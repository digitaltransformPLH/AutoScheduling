using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/stores")]
public class StoresController : ControllerBase
{
    private readonly IStoreQueryService _stores;
    private readonly ICurrentUserService _currentUser;

    public StoresController(IStoreQueryService stores, ICurrentUserService currentUser)
    {
        _stores = stores;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(
        [FromQuery] int? page,
        [FromQuery] int? pageSize,
        [FromQuery] string? search,
        CancellationToken cancellationToken)
    {
        var canManage = await CanManageStoresAsync(cancellationToken);
        var canView = await _currentUser.HasPermissionAsync(PermissionCodes.StoreView, cancellationToken);
        if (!canManage && !canView)
            throw new UnauthorizedAccessException("Missing Store.View or Store.Manage.");

        if (canManage && page.HasValue && pageSize.HasValue)
            return Ok(await _stores.ListPagedAsync(page.Value, pageSize.Value, search, cancellationToken));

        if (canManage)
            return Ok(await _stores.ListActiveAsync(cancellationToken));

        var me = await _currentUser.GetMeAsync(cancellationToken);
        if (me is null) return Unauthorized();
        if (me.AllStores)
            return Ok(await _stores.ListActiveAsync(cancellationToken));

        return Ok(me.Stores.Select(s => new StoreDto
        {
            Id = s.Id,
            Code = s.Code,
            Name = s.Name,
            IsActive = true
        }).ToList());
    }

    [HttpGet("org/{code}")]
    public async Task<IActionResult> GetOrg(string code, CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.StoreView, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.PublishSchedule, cancellationToken))
            throw new UnauthorizedAccessException("Missing Store.View or Publish.Schedule.");

        if (!await _currentUser.CanAccessStoreAsync(code, cancellationToken))
            throw new UnauthorizedAccessException($"No access to store {code}.");

        var org = await _stores.GetOrgByCodeAsync(code, cancellationToken);
        return org is null ? NotFound() : Ok(org);
    }

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Get(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreManage, cancellationToken);
        var store = await _stores.GetAsync(id, cancellationToken);
        return store is null ? NotFound() : Ok(store);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] UpsertStoreRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreManage, cancellationToken);
        try
        {
            var created = await _stores.CreateAsync(request, cancellationToken);
            return CreatedAtAction(nameof(Get), new { id = created.Id }, created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpsertStoreRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreManage, cancellationToken);
        try
        {
            var updated = await _stores.UpdateAsync(id, request, cancellationToken);
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
        await _currentUser.EnsurePermissionAsync(PermissionCodes.StoreManage, cancellationToken);
        var deleted = await _stores.DeleteAsync(id, cancellationToken);
        return deleted ? NoContent() : NotFound();
    }

    private async Task<bool> CanManageStoresAsync(CancellationToken cancellationToken) =>
        await _currentUser.HasPermissionAsync(PermissionCodes.StoreManage, cancellationToken)
        || await _currentUser.HasPermissionAsync(PermissionCodes.UserManage, cancellationToken);
}

[ApiController]
[Authorize]
[Route("api/v1/persons")]
public class PersonsController : ControllerBase
{
    private readonly IPersonQueryService _persons;
    private readonly ICurrentUserService _currentUser;

    public PersonsController(IPersonQueryService persons, ICurrentUserService currentUser)
    {
        _persons = persons;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List([FromQuery] string? role, CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.StoreManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.StoreView, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.UserManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.AmOmManage, cancellationToken))
            throw new UnauthorizedAccessException("Missing permission.");

        return Ok(await _persons.ListAsync(role, cancellationToken));
    }
}

[ApiController]
[Authorize]
[Route("api/v1/am-om-assignments")]
public class AmOmAssignmentsController : ControllerBase
{
    private readonly IAmOmAssignmentService _assignments;
    private readonly ICurrentUserService _currentUser;

    public AmOmAssignmentsController(IAmOmAssignmentService assignments, ICurrentUserService currentUser)
    {
        _assignments = assignments;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.AmOmManage, cancellationToken);
        return Ok(await _assignments.ListCurrentAsync(cancellationToken));
    }

    [HttpGet("by-am/{areaManagerId:int}/om")]
    public async Task<IActionResult> GetOmByAm(int areaManagerId, CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.AmOmManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.StoreManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.PublishSchedule, cancellationToken))
            throw new UnauthorizedAccessException("Missing permission.");

        var om = await _assignments.GetOmByAmIdAsync(areaManagerId, cancellationToken);
        return om is null ? NotFound() : Ok(om);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateAmOmAssignmentRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.AmOmManage, cancellationToken);
        try
        {
            var created = await _assignments.CreateAsync(request, cancellationToken);
            return created is null ? BadRequest(new { success = false, message = "Không tạo được mapping." }) : Ok(created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{areaManagerId:int}")]
    public async Task<IActionResult> Update(int areaManagerId, [FromBody] UpsertAmOmAssignmentRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.AmOmManage, cancellationToken);
        try
        {
            var updated = await _assignments.UpdateCurrentAsync(areaManagerId, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }
}
