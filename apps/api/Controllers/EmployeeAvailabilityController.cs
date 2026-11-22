using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/employee-availability")]
public class EmployeeAvailabilityController : ControllerBase
{
    private readonly IEmployeeAvailabilityService _service;
    private readonly ICurrentUserService _currentUser;

    public EmployeeAvailabilityController(
        IEmployeeAvailabilityService service,
        ICurrentUserService currentUser)
    {
        _service = service;
        _currentUser = currentUser;
    }

    [HttpGet("employee-picks")]
    public async Task<IActionResult> ListEmployeePicks(
        [FromQuery] string plantCode,
        [FromQuery] string weekDate,
        [FromQuery] string? search = null,
        CancellationToken cancellationToken = default)
    {
        await EnsureCanViewAsync(cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });

        if (!await _currentUser.CanAccessStoreAsync(plantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var items = await _service.ListEmployeePicksAsync(plantCode, anchor, search, cancellationToken);
        return Ok(items);
    }

    [HttpGet]
    public async Task<IActionResult> GetWeek(
        [FromQuery] string plantCode,
        [FromQuery] string weekDate,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        [FromQuery] string? search = null,
        CancellationToken cancellationToken = default)
    {
        await EnsureCanViewAsync(cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });

        var scope = await ResolvePlantAccessScopeAsync(plantCode, cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested plant.");

        if (!await _currentUser.CanAccessStoreAsync(plantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var result = await _service.GetWeekAsync(
            plantCode,
            anchor,
            page,
            pageSize,
            search,
            scope.AllowedPlantCodes,
            cancellationToken);
        return Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> Create(
        [FromQuery] string weekDate,
        [FromBody] UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeAvailabilityManage, cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });
        if (!await _currentUser.CanAccessStoreAsync(request.PlantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException("No access to the requested plant.");

        try
        {
            var created = await _service.CreateAsync(anchor, request, cancellationToken);
            return Ok(created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(
        int id,
        [FromQuery] string weekDate,
        [FromBody] UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeAvailabilityManage, cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });
        if (!await _currentUser.CanAccessStoreAsync(request.PlantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException("No access to the requested plant.");

        try
        {
            var updated = await _service.UpdateAsync(id, anchor, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id, CancellationToken cancellationToken = default)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeAvailabilityManage, cancellationToken);
        var deleted = await _service.DeleteAsync(id, cancellationToken);
        return deleted ? NoContent() : NotFound();
    }

    [HttpGet("export")]
    public async Task<IActionResult> ExportExcel(
        [FromQuery] string plantCode,
        [FromQuery] string weekDate,
        CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });

        var scope = await ResolvePlantAccessScopeAsync(plantCode, cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested plant.");
        if (!await _currentUser.CanAccessStoreAsync(plantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var bytes = await _service.ExportExcelAsync(plantCode, anchor, scope.AllowedPlantCodes, cancellationToken);
        var fileName = $"Availability_{plantCode.Trim()}_{anchor:yyyyMMdd}.xlsx";
        return File(bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
    }

    [HttpPost("import")]
    [RequestSizeLimit(20 * 1024 * 1024)]
    public async Task<IActionResult> ImportExcel(
        [FromQuery] string weekDate,
        IFormFile? file,
        CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeAvailabilityManage, cancellationToken);
        if (!DateOnly.TryParse(weekDate, out var anchor))
            return BadRequest(new { success = false, message = "weekDate không hợp lệ (yyyy-MM-dd)." });

        if (file is null || file.Length == 0)
            return BadRequest(new { success = false, message = "Chọn file Excel (.xlsx)." });

        var me = await _currentUser.GetMeAsync(cancellationToken);
        IReadOnlyCollection<string>? accessible = null;
        if (me is { AllStores: false })
            accessible = me.Stores.Select(s => s.Code).ToList();

        await using var stream = file.OpenReadStream();
        var result = await _service.ImportExcelAsync(stream, anchor, accessible, cancellationToken);
        return Ok(result);
    }

    private async Task EnsureCanViewAsync(CancellationToken cancellationToken)
    {
        var canView = await _currentUser.HasPermissionAsync(PermissionCodes.EmployeeAvailabilityView, cancellationToken);
        var canManage = await _currentUser.HasPermissionAsync(PermissionCodes.EmployeeAvailabilityManage, cancellationToken);
        if (!canView && !canManage)
            throw new UnauthorizedAccessException("Missing EmployeeAvailability.View or Manage.");
    }

    private async Task<PlantAccessScope> ResolvePlantAccessScopeAsync(
        string? plantCodeFilter,
        CancellationToken cancellationToken)
    {
        var me = await _currentUser.GetMeAsync(cancellationToken);
        if (me is null)
            return PlantAccessScope.Restricted([]);

        if (me.AllStores)
            return PlantAccessScope.Unrestricted;

        var codes = me.Stores.Select(s => s.Code).ToList();
        if (!string.IsNullOrWhiteSpace(plantCodeFilter))
        {
            var code = plantCodeFilter.Trim();
            if (!codes.Contains(code, StringComparer.OrdinalIgnoreCase))
                return PlantAccessScope.DeniedScope;
        }

        return PlantAccessScope.Restricted(codes);
    }

    private sealed class PlantAccessScope
    {
        public bool Denied { get; private init; }
        public IReadOnlyCollection<string>? AllowedPlantCodes { get; private init; }

        public static PlantAccessScope Unrestricted { get; } = new();

        public static PlantAccessScope DeniedScope { get; } = new() { Denied = true, AllowedPlantCodes = [] };

        public static PlantAccessScope Restricted(IReadOnlyCollection<string> codes) =>
            new() { AllowedPlantCodes = codes };
    }
}