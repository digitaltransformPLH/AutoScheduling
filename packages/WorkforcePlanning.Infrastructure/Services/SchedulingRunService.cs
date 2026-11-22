using System.Diagnostics;
using Dapper;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Application.Options;

namespace WorkforcePlanning.Infrastructure.Services;

public class SchedulingRunService : ISchedulingRunService
{
    private static readonly SemaphoreSlim GlobalEngineLock = new(1, 1);

    private readonly string _connectionString;
    private readonly SchedulingOptions _options;
    private readonly ISchedulingReadService _read;
    private readonly ILogger<SchedulingRunService> _logger;

    public SchedulingRunService(
        IConfiguration configuration,
        IOptions<SchedulingOptions> options,
        ISchedulingReadService read,
        ILogger<SchedulingRunService> logger)
    {
        _connectionString = configuration.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("ConnectionStrings:DefaultConnection is required.");
        _options = options.Value;
        _read = read;
        _logger = logger;
    }

    public async Task<SchedulingRunDto> StartRunAsync(
        StartSchedulingRunRequest request,
        string requestedByEmail,
        CancellationToken cancellationToken = default)
    {
        var store = request.StoreCode.Trim();
        var week = ParseWeekMonday(request.WeekStart);
        var awRaw = string.IsNullOrWhiteSpace(request.AvailabilityWeek)
            ? _options.DefaultAvailabilityWeek
            : request.AvailabilityWeek;
        DateOnly? availabilityWeek = string.IsNullOrWhiteSpace(awRaw) ? null : ParseWeekMonday(awRaw);

        await using var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync(cancellationToken);

        var busy = await conn.QuerySingleOrDefaultAsync<int?>(new CommandDefinition(
            """
            SELECT TOP 1 RunId FROM sched.vw_engine_runs
            WHERE StoreCode = @s AND WeekStart = @w AND Status IN ('queued','running')
            """,
            new { s = store, w = week.ToDateTime(TimeOnly.MinValue) },
            cancellationToken: cancellationToken));

        if (busy.HasValue)
            throw new InvalidOperationException($"store {store} tuần {week:yyyy-MM-dd} đang được xếp lịch (run {busy.Value})");

        var now = DateTime.Now;
        var runId = await conn.QuerySingleAsync<int>(new CommandDefinition(
            """
            INSERT INTO sched.engine_run (StoreCode, WeekStart, AvailabilityWeek, Status, RequestedBy, RequestedAt)
            OUTPUT INSERTED.RunId
            VALUES (@s, @w, @a, 'queued', @u, @t)
            """,
            new
            {
                s = store,
                w = week.ToDateTime(TimeOnly.MinValue),
                a = availabilityWeek?.ToDateTime(TimeOnly.MinValue),
                u = requestedByEmail,
                t = now
            },
            cancellationToken: cancellationToken));

        _ = Task.Run(() => ExecutePythonRunAsync(runId, store, week, availabilityWeek, requestedByEmail));

        var run = await _read.GetRunAsync(runId, cancellationToken);
        return run ?? throw new InvalidOperationException($"run {runId} not found after create");
    }

    private async Task ExecutePythonRunAsync(
        int runId,
        string store,
        DateOnly week,
        DateOnly? availabilityWeek,
        string user)
    {
        await GlobalEngineLock.WaitAsync();
        try
        {
            var repoRoot = FindRepoRoot();
            var weekIso = week.ToString("yyyy-MM-dd");
            var storeEsc = store.Replace("'", "\\'");
            var userEsc = user.Replace("'", "\\'");
            var awLine = availabilityWeek.HasValue
                ? $"aw = date.fromisoformat('{availabilityWeek:yyyy-MM-dd}')"
                : "aw = None";
            var script = $"""
                from datetime import date
                from auto_scheduling.db import get_engine
                from auto_scheduling.service import execute_run
                {awLine}
                execute_run({runId}, '{storeEsc}', date.fromisoformat('{weekIso}'), aw, '{userEsc}', None, get_engine())
                """;
            var scriptPath = Path.Combine(Path.GetTempPath(), $"sched-run-{runId}-{Guid.NewGuid():N}.py");
            await File.WriteAllTextAsync(scriptPath, script);

            try
            {
            var psi = new ProcessStartInfo
            {
                FileName = _options.PythonExecutable,
                Arguments = $"\"{scriptPath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = repoRoot
            };
            psi.Environment["SCHED_SQL_CONN"] = _connectionString;
            psi.Environment["PYTHONPATH"] = Path.Combine(repoRoot, "auto_scheduling");
            if (!string.IsNullOrWhiteSpace(_options.DefaultAvailabilityWeek))
                psi.Environment["SCHED_DEFAULT_AVAILABILITY_WEEK"] = _options.DefaultAvailabilityWeek;

            using var proc = Process.Start(psi);
            if (proc is null)
            {
                _logger.LogError("Failed to start Python engine for run {RunId}", runId);
                return;
            }

            var stdout = await proc.StandardOutput.ReadToEndAsync();
            var stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();
            if (proc.ExitCode != 0)
                _logger.LogWarning("Python run {RunId} exit {Code}: {Err} {Out}", runId, proc.ExitCode, stderr, stdout);
            }
            finally
            {
                try { File.Delete(scriptPath); } catch { /* ignore */ }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Python engine run {RunId} failed", runId);
        }
        finally
        {
            GlobalEngineLock.Release();
        }
    }

    private static DateOnly ParseWeekMonday(string week)
    {
        if (!DateOnly.TryParseExact(week, "yyyy-MM-dd", out var d))
            throw new ArgumentException("week must be YYYY-MM-DD");
        if (d.DayOfWeek != DayOfWeek.Monday)
            throw new ArgumentException("week must be a Monday");
        return d;
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "auto_scheduling")))
                return dir.FullName;
            dir = dir.Parent;
        }
        return Directory.GetCurrentDirectory();
    }
}