using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1")]
public class EmployeeSecondmentsController : ControllerBase
{
    private readonly IEmployeeSecondmentService _secondments;
    private readonly IEmployeeAdminService _employees;
    private readonly ICurrentUserService _currentUser;

    public EmployeeSecondmentsController(
        IEmployeeSecondmentService secondments,
        IEmployeeAdminService employees,
        ICurrentUserService currentUser)
    {
        _secondments = secondments;
        _employees = employees;
        _currentUser = currentUser;
    }

    [HttpGet("employee-secondments")]
    public async Task<IActionResult> List(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        [FromQuery] string? search = null,
        [FromQuery] string? plantCode = null,
        [FromQuery] string? status = null,
        CancellationToken cancellationToken = default)
    {
        await EnsureCanViewAsync(cancellationToken);
        var scope = await ResolvePlantAccessScopeAsync(plantCode, cancellationToken);
        if (scope.Denied)
            throw new UnauthorizedAccessException("No access to the requested plant.");

        var result = await _secondments.ListPagedAsync(
            page, pageSize, search, plantCode, status, scope.AllowedPlantCodes, cancellationToken);
        return Ok(result);
    }

    [HttpPost("employees/{employeeId:int}/secondments")]
    public async Task<IActionResult> Create(
        int employeeId,
        [FromBody] CreateEmployeeSecondmentRequest request,
        CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        var employee = await _employees.GetAsync(employeeId, cancellationToken);
        if (employee is null) return NotFound();
        if (!await CanAccessEmployeePlantAsync(employee.PlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");

        var updatedBy = string.IsNullOrWhiteSpace(_currentUser.Email) ? "unknown" : _currentUser.Email.Trim();
        var created = await _secondments.CreateAsync(employeeId, request, updatedBy, cancellationToken);
        return CreatedAtAction(nameof(List), new { id = created.Id }, created);
    }

    [HttpPut("employee-secondments/{id:int}")]
    public async Task<IActionResult> Update(
        int id,
        [FromBody] UpdateEmployeeSecondmentRequest request,
        CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        var item = await _secondments.GetAsync(id, cancellationToken);
        if (item is null) return NotFound();
        if (!await CanAccessEmployeePlantAsync(item.HomePlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");

        var updatedBy = string.IsNullOrWhiteSpace(_currentUser.Email) ? "unknown" : _currentUser.Email.Trim();
        var result = await _secondments.UpdateAsync(id, request, updatedBy, cancellationToken);
        return result is null ? NotFound() : Ok(result);
    }

    [HttpPost("employee-secondments/{id:int}/cancel")]
    public async Task<IActionResult> Cancel(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.EmployeeManage, cancellationToken);

        var item = await _secondments.GetAsync(id, cancellationToken);
        if (item is null) return NotFound();
        if (!await CanAccessEmployeePlantAsync(item.HomePlantCode, cancellationToken))
            throw new UnauthorizedAccessException("No access to this employee's plant.");

        var updatedBy = string.IsNullOrWhiteSpace(_currentUser.Email) ? "unknown" : _currentUser.Email.Trim();
        var result = await _secondments.CancelAsync(id, updatedBy, cancellationToken);
        return result is null ? NotFound() : Ok(result);
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

    private sealed class PlantAccessScope
    {
        public bool Denied { get; private init; }
        public IReadOnlyCollection<string>? AllowedPlantCodes { get; private init; }

        public static PlantAccessScope Unrestricted { get; } = new() { AllowedPlantCodes = null };

        public static PlantAccessScope Restricted(IReadOnlyCollection<string> codes) =>
            new() { AllowedPlantCodes = codes, Denied = codes.Count == 0 };
    }
}