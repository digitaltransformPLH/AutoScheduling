using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/employees")]
public class EmployeesController : ControllerBase
{
    private readonly IEmployeeAdminService _employees;
    private readonly ICurrentUserService _currentUser;

    public EmployeesController(IEmployeeAdminService employees, ICurrentUserService currentUser)
    {
        _employees = employees;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        [FromQuery] string? search = null,
        [FromQuery] string? plantCode = null,
        CancellationToken cancellationToken = default)
    {
        await EnsureCanViewAsync(cancellationToken);
        var scope = await ResolvePlantAccessScopeAsync(plantCode, cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var result = await _employees.ListPagedAsync(
            page, pageSize, search, plantCode, scope.AllowedPlantCodes, cancellationToken);
        return Ok(result);
    }

    [HttpGet("lookups")]
    public async Task<IActionResult> Lookups(CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        return Ok(_employees.GetLookups());
    }

    [HttpGet("export")]
    public async Task<IActionResult> ExportExcel(
        [FromQuery] string? plantCode,
        CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        var scope = await ResolvePlantAccessScopeAsync(plantCode, cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var bytes = await _employees.ExportExcelAsync(plantCode, scope.AllowedPlantCodes, cancellationToken);
        var suffix = string.IsNullOrWhiteSpace(plantCode) ? "all" : plantCode.Trim();
        var fileName = $"Employee_Master_{suffix}_{DateTime.UtcNow:yyyyMMdd}.xlsx";
        return File(bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
    }

    [HttpPost("import")]
    [RequestSizeLimit(20 * 1024 * 1024)]
    public async Task<IActionResult> ImportExcel(IFormFile? file, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        if (file is null || file.Length == 0)
            return BadRequest(new { success = false, message = "Chọn file Excel (.xlsx)." });

        var ext = Path.GetExtension(file.FileName);
        if (!string.Equals(ext, ".xlsx", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(ext, ".xlsm", StringComparison.OrdinalIgnoreCase))
            return BadRequest(new { success = false, message = "Chỉ hỗ trợ file .xlsx." });

        var me = await _currentUser.GetMeAsync(cancellationToken);
        IReadOnlyCollection<string>? accessible = null;
        if (me is { AllStores: false })
            accessible = me.Stores.Select(s => s.Code).ToList();

        await using var stream = file.OpenReadStream();
        var result = await _employees.ImportExcelAsync(stream, accessible, cancellationToken);
        return Ok(result);
    }

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Get(int id, CancellationToken cancellationToken)
    {
        await EnsureCanViewAsync(cancellationToken);
        var employee = await _employees.GetAsync(id, cancellationToken);
        if (employee is null) return NotFound();

        if (!await CanAccessEmployeePlantAsync(employee.PlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");

        return Ok(employee);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] UpsertEmployeeRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);
        if (!await _currentUser.CanAccessStoreAsync(request.PlantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException($"No access to store {request.PlantCode}.");

        try
        {
            var created = await _employees.CreateAsync(request, cancellationToken);
            return CreatedAtAction(nameof(Get), new { id = created.Id }, created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpsertEmployeeRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        var existing = await _employees.GetAsync(id, cancellationToken);
        if (existing is null) return NotFound();

        if (!await CanAccessEmployeePlantAsync(existing.PlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");
        if (!await _currentUser.CanAccessStoreAsync(request.PlantCode.Trim(), cancellationToken))
            throw new UnauthorizedAccessException($"No access to store {request.PlantCode}.");

        try
        {
            var updated = await _employees.UpdateAsync(id, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        var existing = await _employees.GetAsync(id, cancellationToken);
        if (existing is null) return NotFound();
        if (!await CanAccessEmployeePlantAsync(existing.PlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");

        var deleted = await _employees.DeleteAsync(id, cancellationToken);
        return deleted ? NoContent() : NotFound();
    }

    private async Task EnsureCanViewAsync(CancellationToken cancellationToken)
    {
        var canView = await _currentUser.HasPermissionAsync(PermissionCodes.EmployeeView, cancellationToken);
        var canManage = await _currentUser.HasPermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);
        if (!canView && !canManage)
            throw new UnauthorizedAccessException("Missing Employee.View or Employee.Manage.");
    }

    private async Task<bool> CanAccessEmployeePlantAsync(string plantCode, CancellationToken cancellationToken) =>
        await _currentUser.CanAccessStoreAsync(plantCode, cancellationToken);

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
                return PlantAccessScope.Restricted([]);
        }

        return PlantAccessScope.Restricted(codes);
    }

    /// <summary>
    /// AllowedPlantCodes: null = all plants; empty = none; non-empty = limit to those codes.
    /// </summary>
    private sealed class PlantAccessScope
    {
        public bool Denied { get; private init; }
        public IReadOnlyCollection<string>? AllowedPlantCodes { get; private init; }

        public static PlantAccessScope Unrestricted { get; } = new() { AllowedPlantCodes = null };

        public static PlantAccessScope Restricted(IReadOnlyCollection<string> codes) =>
            new() { AllowedPlantCodes = codes };
    }
}