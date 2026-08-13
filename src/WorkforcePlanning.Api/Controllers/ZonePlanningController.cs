using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1")]
public class ZonePlanningController : ControllerBase
{
    private readonly IZonePlanningService _zonePlanningService;
    private readonly ICurrentUserService _currentUser;

    public ZonePlanningController(IZonePlanningService zonePlanningService, ICurrentUserService currentUser)
    {
        _zonePlanningService = zonePlanningService;
        _currentUser = currentUser;
    }

    [HttpGet("zone-planning")]
    public async Task<ActionResult<ZonePlanningResponseDto>> Get(
        [FromQuery] int year,
        [FromQuery] int month,
        [FromQuery] string weekStart,
        CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.ZonePlanningView, cancellationToken))
            return Forbid();

        if (!DateOnly.TryParseExact(weekStart, "yyyy-MM-dd", out var weekStartMonday))
            return BadRequest(new { success = false, message = "weekStart must be YYYY-MM-DD." });

        if (weekStartMonday.DayOfWeek != DayOfWeek.Monday)
            return BadRequest(new { success = false, message = "weekStart must be a Monday." });

        var resp = await _zonePlanningService.GetZonePlanningAsync(year, month, weekStartMonday, cancellationToken);
        return Ok(resp);
    }
}

