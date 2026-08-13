using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/users")]
public class UsersController : ControllerBase
{
    private readonly IUserAdminService _users;
    private readonly ICurrentUserService _currentUser;

    public UsersController(IUserAdminService users, ICurrentUserService currentUser)
    {
        _users = users;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.UserManage, cancellationToken);
        return Ok(await _users.ListAsync(cancellationToken));
    }

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Get(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.UserManage, cancellationToken);
        var user = await _users.GetAsync(id, cancellationToken);
        return user is null ? NotFound() : Ok(user);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] UpsertUserRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.UserManage, cancellationToken);
        try
        {
            var created = await _users.CreateAsync(request, cancellationToken);
            return CreatedAtAction(nameof(Get), new { id = created.Id }, created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpsertUserRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.UserManage, cancellationToken);
        try
        {
            var updated = await _users.UpdateAsync(id, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Deactivate(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.UserManage, cancellationToken);
        var ok = await _users.DeactivateAsync(id, cancellationToken);
        return ok ? Ok(new { success = true }) : NotFound();
    }
}

[ApiController]
[Authorize]
[Route("api/v1/roles")]
public class RolesController : ControllerBase
{
    private readonly IRoleAdminService _roles;
    private readonly ICurrentUserService _currentUser;

    public RolesController(IRoleAdminService roles, ICurrentUserService currentUser)
    {
        _roles = roles;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.RoleManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.UserManage, cancellationToken))
            throw new UnauthorizedAccessException("Missing Role.Manage or User.Manage.");
        return Ok(await _roles.ListAsync(cancellationToken));
    }

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Get(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        var role = await _roles.GetAsync(id, cancellationToken);
        return role is null ? NotFound() : Ok(role);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] UpsertRoleRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        try
        {
            var created = await _roles.CreateAsync(request, cancellationToken);
            return CreatedAtAction(nameof(Get), new { id = created.Id }, created);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpsertRoleRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        try
        {
            var updated = await _roles.UpdateAsync(id, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPut("{id:int}/permissions")]
    public async Task<IActionResult> SetPermissions(int id, [FromBody] SetRolePermissionsRequest request, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        try
        {
            var updated = await _roles.SetPermissionsAsync(id, request, cancellationToken);
            return updated is null ? NotFound() : Ok(updated);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }

    [HttpPost("{id:int}/clone")]
    public async Task<IActionResult> Clone(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        var cloned = await _roles.CloneAsync(id, cancellationToken);
        return cloned is null ? NotFound() : Ok(cloned);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id, CancellationToken cancellationToken)
    {
        await _currentUser.EnsurePermissionAsync(PermissionCodes.RoleManage, cancellationToken);
        try
        {
            var ok = await _roles.DeleteAsync(id, cancellationToken);
            return ok ? Ok(new { success = true }) : NotFound();
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }
}

[ApiController]
[Authorize]
[Route("api/v1/permissions")]
public class PermissionsController : ControllerBase
{
    private readonly IRoleAdminService _roles;
    private readonly ICurrentUserService _currentUser;

    public PermissionsController(IRoleAdminService roles, ICurrentUserService currentUser)
    {
        _roles = roles;
        _currentUser = currentUser;
    }

    [HttpGet]
    public async Task<IActionResult> List(CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.RoleManage, cancellationToken)
            && !await _currentUser.HasPermissionAsync(PermissionCodes.UserManage, cancellationToken))
            throw new UnauthorizedAccessException("Missing Role.Manage or User.Manage.");

        return Ok(await _roles.ListPermissionsAsync(cancellationToken));
    }
}
