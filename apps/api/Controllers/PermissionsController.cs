using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

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
