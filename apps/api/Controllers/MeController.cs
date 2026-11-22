using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.Interfaces;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1")]
public class MeController : ControllerBase
{
    private readonly ICurrentUserService _currentUser;

    public MeController(ICurrentUserService currentUser)
    {
        _currentUser = currentUser;
    }

    [HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken cancellationToken)
    {
        var me = await _currentUser.GetMeAsync(cancellationToken);
        if (me is null)
            return Unauthorized(new { success = false, message = "Not authenticated." });
        return Ok(me);
    }
}
