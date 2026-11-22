using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/sched")]
public class SchedulingController : ControllerBase
{
    private readonly ISchedulingReadService _read;
    private readonly ISchedulingRunService _runs;
    private readonly ISchedulingFile2ExportService _file2;
    private readonly ICurrentUserService _currentUser;

    public SchedulingController(
        ISchedulingReadService read,
        ISchedulingRunService runs,
        ISchedulingFile2ExportService file2,
        ICurrentUserService currentUser)
    {
        _read = read;
        _runs = runs;
        _file2 = file2;
        _currentUser = currentUser;
    }

    [HttpGet("meta")]
    public async Task<ActionResult<SchedulingMetaDto>> Meta(CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        return Ok(await _read.GetMetaAsync(cancellationToken));
    }

    [HttpGet("stores")]
    public async Task<ActionResult<SchedulingEnvelope<IReadOnlyList<SchedulingStoreItemDto>>>> ListStores(
        [FromQuery(Name = "ready_only")] bool readyOnly = false,
        CancellationToken cancellationToken = default)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        var (allowed, allStores) = await GetStoreScopeAsync(cancellationToken);
        var data = await _read.ListStoresAsync(readyOnly, allowed, allStores, cancellationToken);
        return Ok(await EnvelopeAsync(data, cancellationToken));
    }

    [HttpGet("forecast-weeks")]
    public async Task<ActionResult<SchedulingEnvelope<IReadOnlyList<ForecastWeekDto>>>> ForecastWeeks(
        CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        var data = await _read.ListForecastWeeksAsync(cancellationToken);
        return Ok(await EnvelopeAsync(data, cancellationToken));
    }

    [HttpGet("schedules")]
    public async Task<ActionResult<SchedulingEnvelope<IReadOnlyList<ScheduleWeekDto>>>> Schedules(
        [FromQuery] string? store,
        CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        var (allowed, allStores) = await GetStoreScopeAsync(cancellationToken);
        var data = await _read.ListSchedulesAsync(store, allowed, allStores, cancellationToken);
        return Ok(await EnvelopeAsync(data, cancellationToken));
    }

    [HttpGet("schedules/{store}/{week}/overview")]
    public async Task<ActionResult<SchedulingEnvelope<OverviewDto>>> Overview(
        string store,
        string week,
        CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        await EnsureStoreAsync(store, cancellationToken);
        try
        {
            var wk = ParseWeek(week);
            var data = await _read.GetOverviewAsync(store, wk, cancellationToken);
            return Ok(await EnvelopeAsync(data, cancellationToken));
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new { detail = ex.Message });
        }
    }

    [HttpGet("schedules/{store}/{week}/roster")]
    public async Task<ActionResult<SchedulingEnvelope<IReadOnlyList<RosterDayDto>>>> Roster(
        string store,
        string week,
        CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        await EnsureStoreAsync(store, cancellationToken);
        try
        {
            var wk = ParseWeek(week);
            var data = await _read.GetRosterAsync(store, wk, cancellationToken);
            return Ok(await EnvelopeAsync(data, cancellationToken));
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new { detail = ex.Message });
        }
    }

    [HttpGet("schedules/{store}/{week}/file2")]
    public async Task<IActionResult> File2(string store, string week, CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        await EnsureStoreAsync(store, cancellationToken);
        try
        {
            var wk = ParseWeek(week);
            var file = await _file2.ExportAsync(store, wk, cancellationToken);
            return File(
                file.Content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                file.FileName);
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new { detail = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { detail = ex.Message });
        }
    }

    [HttpGet("runs")]
    public async Task<ActionResult<SchedulingEnvelope<IReadOnlyList<SchedulingRunDto>>>> ListRuns(
        [FromQuery] string? store,
        [FromQuery] int limit = 30,
        CancellationToken cancellationToken = default)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        var (allowed, allStores) = await GetStoreScopeAsync(cancellationToken);
        var data = await _read.ListRunsAsync(store, limit, allowed, allStores, cancellationToken);
        return Ok(await EnvelopeAsync(data, cancellationToken));
    }

    [HttpGet("runs/{runId:int}")]
    public async Task<ActionResult<SchedulingEnvelope<SchedulingRunDto>>> GetRun(int runId, CancellationToken cancellationToken)
    {
        await EnsureScheduleViewAsync(cancellationToken);
        var run = await _read.GetRunAsync(runId, cancellationToken);
        if (run is null)
            return NotFound(new { detail = $"run {runId} not found" });
        if (!await _currentUser.CanAccessStoreAsync(run.StoreCode, cancellationToken))
            return NotFound(new { detail = $"run {runId} not found" });
        return Ok(await EnvelopeAsync(run, cancellationToken));
    }

    [HttpPost("runs")]
    public async Task<ActionResult<SchedulingEnvelope<SchedulingRunDto>>> StartRun(
        [FromBody] StartSchedulingRunRequest request,
        CancellationToken cancellationToken)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.PublishSchedule, cancellationToken))
            throw new UnauthorizedAccessException("Missing Action.Publish.Schedule.");
        await EnsureStoreAsync(request.StoreCode, cancellationToken);
        try
        {
            var run = await _runs.StartRunAsync(request, _currentUser.Email, cancellationToken);
            var envelope = await EnvelopeAsync(run, cancellationToken);
            return Accepted(envelope);
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { detail = ex.Message });
        }
    }

    private async Task<SchedulingEnvelope<T>> EnvelopeAsync<T>(T data, CancellationToken cancellationToken) =>
        new() { Data = data, Meta = await _read.GetMetaAsync(cancellationToken) };

    private async Task EnsureScheduleViewAsync(CancellationToken cancellationToken)
    {
        var overview = await _currentUser.HasPermissionAsync(PermissionCodes.PlanningOverviewView, cancellationToken);
        var analysis = await _currentUser.HasPermissionAsync(PermissionCodes.PlanningAnalysisView, cancellationToken);
        if (!overview && !analysis)
            throw new UnauthorizedAccessException("Missing Action.Planning.Overview.View or Action.Planning.Analysis.View.");
    }

    private async Task EnsureStoreAsync(string storeCode, CancellationToken cancellationToken)
    {
        if (!await _currentUser.CanAccessStoreAsync(storeCode, cancellationToken))
            throw new UnauthorizedAccessException($"No access to store {storeCode}.");
    }

    private async Task<(HashSet<string> Allowed, bool AllStores)> GetStoreScopeAsync(CancellationToken cancellationToken)
    {
        var me = await _currentUser.GetMeAsync(cancellationToken);
        if (me is null)
            throw new UnauthorizedAccessException("Not authenticated.");
        if (me.AllStores)
            return (new HashSet<string>(StringComparer.OrdinalIgnoreCase), true);
        var set = me.Stores.Select(s => s.Code).ToHashSet(StringComparer.OrdinalIgnoreCase);
        return (set, false);
    }

    private static DateOnly ParseWeek(string week)
    {
        if (!DateOnly.TryParseExact(week, "yyyy-MM-dd", out var d))
            throw new BadHttpRequestException("week must be YYYY-MM-DD");
        if (d.DayOfWeek != DayOfWeek.Monday)
            throw new BadHttpRequestException("week must be a Monday");
        return d;
    }
}