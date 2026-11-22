using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1")]
public class PublishController : ControllerBase
{
    private readonly IPublishService _publishService;

    public PublishController(IPublishService publishService)
    {
        _publishService = publishService;
    }

    [HttpPost("publish")]
    public async Task<IActionResult> Publish(
        [FromBody] PublishScheduleRequest request,
        CancellationToken cancellationToken)
    {
        try
        {
            var result = await _publishService.PublishAsync(request, cancellationToken);
            if (!result.Success)
            {
                var status = result.Message?.StartsWith("Forbidden", StringComparison.OrdinalIgnoreCase) == true
                    ? StatusCodes.Status403Forbidden
                    : StatusCodes.Status400BadRequest;
                return StatusCode(status, result);
            }

            return Ok(result);
        }
        catch (Exception ex)
        {
            // Surface DB/login errors to client for IIS troubleshooting (e.g. App Pool SQL access).
            return StatusCode(StatusCodes.Status500InternalServerError, new PublishScheduleResponse
            {
                Success = false,
                PublishId = request?.PublishId ?? "",
                PublishVersion = request?.PublishVersion ?? 0,
                Message = ex.GetBaseException().Message
            });
        }
    }

    [HttpGet("stores/{storeCode}/daily")]
    public async Task<IActionResult> GetDaily(
        string storeCode,
        [FromQuery] string weekStart,
        CancellationToken cancellationToken)
    {
        if (!DateOnly.TryParseExact(weekStart, "yyyy-MM-dd", out var monday))
            return BadRequest(new { success = false, message = "weekStart must be YYYY-MM-DD." });

        try
        {
            var result = await _publishService.GetLatestWeekAsync(storeCode, monday, cancellationToken);
            return Ok(result);
        }
        catch (UnauthorizedAccessException)
        {
            return Forbid();
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { success = false, message = ex.Message });
        }
    }
}
