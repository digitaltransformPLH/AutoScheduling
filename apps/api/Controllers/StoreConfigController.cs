using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/store-configs")]
public class StoreConfigController : ControllerBase
{
    private readonly IStoreConfigService _storeConfigs;
    private readonly ICurrentUserService _currentUser;

    public StoreConfigController(IStoreConfigService storeConfigs, ICurrentUserService currentUser)
    {
        _storeConfigs = storeConfigs;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        [FromQuery] string? search = null,
        CancellationToken cancellationToken = default)
    {
        await EnsureCanViewAsync(cancellationToken);
        var codes = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (codes.Denied)
            return Ok(EmptyPage(page, pageSize));

        var result = await _storeConfigs.ListPagedAsync(
            page, pageSize, search, codes.AllowedStoreCodes, cancellationToken);
        return Ok(result);
    }

    [HttpGet("{storeId:int}")]
    public async Task<IActionResult> GetByStoreId(int storeId, CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        var codes = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (codes.Denied)
            return NotFound();

        var detail = await _storeConfigs.GetByStoreIdAsync(storeId, codes.AllowedStoreCodes, cancellationToken);
        return detail is null ? NotFound() : Ok(detail);
    }

    [HttpGet("by-code/{code}")]
    public async Task<IActionResult> GetByStoreCode(string code, CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        var scope = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (scope.Denied)
            return NotFound();

        var detail = await _storeConfigs.GetByStoreCodeAsync(code, scope.AllowedStoreCodes, cancellationToken);
        return detail is null ? NotFound() : Ok(detail);
    }

    [HttpPut("{storeId:int}")]
    public async Task<IActionResult> Upsert(
        int storeId,
        [FromBody] UpsertStoreConfigRequest request,
        CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreConfigManage, cancellationToken);
        var scope = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested store.");

        try
        {
            var detail = await _storeConfigs.UpsertAsync(
                storeId,
                request,
                _currentUser.Email,
                scope.AllowedStoreCodes,
                cancellationToken);
            return detail is null ? NotFound() : Ok(detail);
        }
        catch (FluentValidation.ValidationException ex)
        {
            return BadRequest(new { success = false, message = ex.Errors.FirstOrDefault()?.ErrorMessage ?? "Dữ liệu không hợp lệ." });
        }
    }

    [HttpGet("export")]
    public async Task<IActionResult> ExportExcel(CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        var scope = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to any store.");

        var bytes = await _storeConfigs.ExportExcelAsync(scope.AllowedStoreCodes, cancellationToken);
        var fileName = $"Store_Config_{DateTime.UtcNow:yyyyMMdd}.xlsx";
        return File(bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
    }

    [HttpPost("import")]
    [RequestSizeLimit(20 * 1024 * 1024)]
    public async Task<IActionResult> ImportExcel(IFormFile? file, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreConfigManage, cancellationToken);

        if (file is null || file.Length == 0)
            return BadRequest(new { success = false, message = "Chọn file Excel (.xlsx)." });

        var ext = Path.GetExtension(file.FileName);
        if (!string.Equals(ext, ".xlsx", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(ext, ".xlsm", StringComparison.OrdinalIgnoreCase))
            return BadRequest(new { success = false, message = "Chỉ hỗ trợ file .xlsx." });

        var scope = await ResolveAccessibleStoreCodesAsync(cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to any store.");

        await using var stream = file.OpenReadStream();
        var result = await _storeConfigs.ImportExcelAsync(
            stream,
            _currentUser.Email,
            scope.AllowedStoreCodes,
            cancellationToken);
        return Ok(result);
    }

    private async Task EnsureCanViewAsync(CancellationToken cancellationToken)
    {
        var canView = await _currentUser.HasPermissionAsync(PermissionCodes.StoreConfigView, cancellationToken);
        var canManage = await _currentUser.HasPermissionAsync(PermissionCodes.StoreConfigManage, cancellationToken);
        if (!canView && !canManage)
            throw new UnauthorizedAccessException("Missing StoreConfig.View or StoreConfig.Manage.");
    }

    private async Task<StoreAccessScope> ResolveAccessibleStoreCodesAsync(CancellationToken cancellationToken)
    {
        var me = await _currentUser.GetMeAsync(cancellationToken);
        if (me is null)
            return StoreAccessScope.DeniedScope;

        if (me.AllStores)
            return StoreAccessScope.Unrestricted;

        var codes = me.Stores.Select(s => s.Code).ToList();
        return codes.Count == 0
            ? StoreAccessScope.DeniedScope
            : StoreAccessScope.Restricted(codes);
    }

    private static PagedResult<StoreConfigListItemDto> EmptyPage(int page, int pageSize) =>
        new() { Items = [], Total = 0, Page = page, PageSize = pageSize };

    private sealed class StoreAccessScope
    {
        public bool Denied { get; private init; }
        public IReadOnlyCollection<string>? AllowedStoreCodes { get; private init; }

        public static StoreAccessScope Unrestricted { get; } = new() { AllowedStoreCodes = null };

        public static StoreAccessScope DeniedScope { get; } = new() { Denied = true, AllowedStoreCodes = [] };

        public static StoreAccessScope Restricted(IReadOnlyCollection<string> codes) =>
            new() { AllowedStoreCodes = codes };
    }
}