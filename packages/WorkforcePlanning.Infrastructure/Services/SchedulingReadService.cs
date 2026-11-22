using System.Data;
using Dapper;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Application.Options;

namespace WorkforcePlanning.Infrastructure.Services;

public class SchedulingReadService : ISchedulingReadService
{
    private readonly string _connectionString;
    private readonly SchedulingOptions _options;

    public SchedulingReadService(IConfiguration configuration, IOptions<SchedulingOptions> options)
    {
        _connectionString = configuration.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("ConnectionStrings:DefaultConnection is required.");
        _options = options.Value;
    }

    private SqlConnection Connect() => new(_connectionString);

    public async Task<SchedulingMetaDto> GetMetaAsync(CancellationToken cancellationToken = default)
    {
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var row = await conn.QuerySingleOrDefaultAsync(
            new CommandDefinition(
                "SELECT DataVersion, BuiltAt FROM sched.vw_meta",
                cancellationToken: cancellationToken));
        return BuildMeta(row);
    }

    private SchedulingMetaDto BuildMeta(dynamic? row)
    {
        var dataVersion = row is null ? 0 : SchedulingValueFormatter.ToInt(row.DataVersion);
        var builtAt = row is null ? null : SchedulingValueFormatter.DateTimeToString(row.BuiltAt);
        return new SchedulingMetaDto
        {
            DataVersion = dataVersion,
            BuiltAt = builtAt,
            Source = "sched",
            BackTest = _options.BackTest,
            AvailabilityWeek = _options.DefaultAvailabilityWeek
        };
    }

    private async Task<SchedulingMetaDto> MetaFromConnAsync(SqlConnection conn, CancellationToken ct) =>
        BuildMeta(await conn.QuerySingleOrDefaultAsync(
            new CommandDefinition("SELECT DataVersion, BuiltAt FROM sched.vw_meta", cancellationToken: ct)));

    public async Task<IReadOnlyList<SchedulingStoreItemDto>> ListStoresAsync(
        bool readyOnly,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default)
    {
        var sql = "SELECT * FROM sched.vw_store_list"
            + (readyOnly ? " WHERE ReadyToSchedule = 1" : "")
            + " ORDER BY ReadyToSchedule DESC, ScheduledWeeks DESC, StoreCode";
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var rows = (await conn.QueryAsync(new CommandDefinition(sql, cancellationToken: cancellationToken))).ToList();
        var list = new List<SchedulingStoreItemDto>();
        foreach (var r in rows)
        {
            var code = (string)r.StoreCode;
            if (!allStores && !allowedStoreCodes.Contains(code)) continue;
            list.Add(MapStoreItem(r));
        }
        return list;
    }

    public async Task<IReadOnlyList<ForecastWeekDto>> ListForecastWeeksAsync(CancellationToken cancellationToken = default)
    {
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var rows = await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_forecast_weeks ORDER BY WeekStart DESC",
            cancellationToken: cancellationToken));
        return rows.Select(MapForecastWeek).ToList();
    }

    public async Task<IReadOnlyList<ScheduleWeekDto>> ListSchedulesAsync(
        string? storeCode,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default)
    {
        var sql = "SELECT * FROM sched.vw_schedule_week"
            + (string.IsNullOrWhiteSpace(storeCode) ? "" : " WHERE StoreCode = @s")
            + " ORDER BY WeekStart DESC, StoreCode";
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var rows = await conn.QueryAsync(new CommandDefinition(sql, new { s = storeCode }, cancellationToken: cancellationToken));
        var list = new List<ScheduleWeekDto>();
        foreach (var r in rows)
        {
            var code = (string)r.StoreCode;
            if (!allStores && !allowedStoreCodes.Contains(code)) continue;
            list.Add(MapScheduleWeek(r));
        }
        return list;
    }

    public async Task<ScheduleWeekDto?> GetScheduleWeekAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default)
    {
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var row = await conn.QuerySingleOrDefaultAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_week WHERE StoreCode = @s AND WeekStart = @w",
            new { s = storeCode, w = weekStart.ToDateTime(TimeOnly.MinValue) },
            cancellationToken: cancellationToken));
        return row is null ? null : MapScheduleWeek(row);
    }

    public async Task<OverviewDto> GetOverviewAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default)
    {
        var week = await GetScheduleWeekAsync(storeCode, weekStart, cancellationToken)
            ?? throw new KeyNotFoundException($"chưa có lịch cho store {storeCode} tuần {weekStart:yyyy-MM-dd}");

        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var p = new { s = storeCode, w = weekStart.ToDateTime(TimeOnly.MinValue) };

        var days = (await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_daily WHERE StoreCode = @s AND WeekStart = @w ORDER BY WorkDate",
            p, cancellationToken: cancellationToken))).Select(MapDaySummary).ToList();

        var hourly = (await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_hourly WHERE StoreCode = @s AND WeekStart = @w ORDER BY WorkDate, Slot",
            p, cancellationToken: cancellationToken))).Select(MapHourCoverage).ToList();

        var roster = (await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_roster WHERE StoreCode = @s AND WeekStart = @w ORDER BY SortOrder, WorkDate",
            p, cancellationToken: cancellationToken))).Select(MapRosterDay).ToList();

        var issues = (await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_issues WHERE StoreCode = @s AND WeekStart = @w ORDER BY Id",
            p, cancellationToken: cancellationToken))).Select(MapIssue).ToList();

        return new OverviewDto { Week = week, Days = days, Hourly = hourly, Roster = roster, Issues = issues };
    }

    public async Task<IReadOnlyList<RosterDayDto>> GetRosterAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default)
    {
        if (await GetScheduleWeekAsync(storeCode, weekStart, cancellationToken) is null)
            throw new KeyNotFoundException($"chưa có lịch cho store {storeCode} tuần {weekStart:yyyy-MM-dd}");

        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var rows = await conn.QueryAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_schedule_roster WHERE StoreCode = @s AND WeekStart = @w ORDER BY SortOrder, WorkDate",
            new { s = storeCode, w = weekStart.ToDateTime(TimeOnly.MinValue) },
            cancellationToken: cancellationToken));
        return rows.Select(MapRosterDay).ToList();
    }

    public async Task<IReadOnlyList<SchedulingRunDto>> ListRunsAsync(
        string? storeCode,
        int limit,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        var sql = $"SELECT TOP ({limit}) * FROM sched.vw_engine_runs"
            + (string.IsNullOrWhiteSpace(storeCode) ? "" : " WHERE StoreCode = @s")
            + " ORDER BY RunId DESC";
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var rows = await conn.QueryAsync(new CommandDefinition(sql, new { s = storeCode }, cancellationToken: cancellationToken));
        var list = new List<SchedulingRunDto>();
        foreach (var r in rows)
        {
            var code = (string)r.StoreCode;
            if (!allStores && !allowedStoreCodes.Contains(code)) continue;
            list.Add(MapRun(r));
        }
        return list;
    }

    public async Task<SchedulingRunDto?> GetRunAsync(int runId, CancellationToken cancellationToken = default)
    {
        await using var conn = Connect();
        await conn.OpenAsync(cancellationToken);
        var row = await conn.QuerySingleOrDefaultAsync(new CommandDefinition(
            "SELECT * FROM sched.vw_engine_runs WHERE RunId = @r",
            new { r = runId },
            cancellationToken: cancellationToken));
        return row is null ? null : MapRun(row);
    }

    private static SchedulingStoreItemDto MapStoreItem(dynamic r) => new()
    {
        StoreCode = r.StoreCode,
        StoreName = r.StoreName ?? "",
        OpeningTime = SchedulingValueFormatter.TimeToString(r.OpeningTime),
        ClosingTime = SchedulingValueFormatter.TimeToString(r.ClosingTime),
        TcphTarget = SchedulingValueFormatter.ToDouble(r.TcphTarget),
        EmployeeCount = SchedulingValueFormatter.ToInt(r.EmployeeCount),
        HasForecast = SchedulingValueFormatter.ToBool(r.HasForecast),
        ReadyToSchedule = SchedulingValueFormatter.ToBool(r.ReadyToSchedule),
        ScheduledWeeks = SchedulingValueFormatter.ToInt(r.ScheduledWeeks)
    };

    private static ForecastWeekDto MapForecastWeek(dynamic r) => new()
    {
        WeekStart = SchedulingValueFormatter.DateToString(r.WeekStart) ?? "",
        StoreCount = SchedulingValueFormatter.ToInt(r.StoreCount),
        CreatedAt = SchedulingValueFormatter.DateTimeToString(r.CreatedAt),
        MethodVersion = r.MethodVersion as string
    };

    private static ScheduleWeekDto MapScheduleWeek(dynamic r) => new()
    {
        StoreCode = r.StoreCode,
        WeekStart = SchedulingValueFormatter.DateToString(r.WeekStart) ?? "",
        WeekEnd = SchedulingValueFormatter.DateToString(r.WeekEnd) ?? "",
        StoreName = r.StoreName,
        OpeningTime = SchedulingValueFormatter.TimeToString(r.OpeningTime),
        ClosingTime = SchedulingValueFormatter.TimeToString(r.ClosingTime),
        Status = r.Status ?? "",
        Assessment = r.Assessment,
        TcphTarget = SchedulingValueFormatter.ToDouble(r.TcphTarget),
        WeeklyTcph = SchedulingValueFormatter.ToDouble(r.WeeklyTcph),
        TcphInTarget = r.TcphInTarget is null ? null : SchedulingValueFormatter.ToBool(r.TcphInTarget),
        ForecastTc = SchedulingValueFormatter.ToDouble(r.ForecastTc),
        LaborHours = SchedulingValueFormatter.ToDouble(r.LaborHours),
        NsoHours = SchedulingValueFormatter.ToDouble(r.NsoHours),
        StaffCoveragePct = SchedulingValueFormatter.ToDouble(r.StaffCoveragePct),
        ManagerCoveragePct = SchedulingValueFormatter.ToDouble(r.ManagerCoveragePct),
        EmployeeCount = SchedulingValueFormatter.ToInt(r.EmployeeCount),
        ErrorCount = SchedulingValueFormatter.ToInt(r.ErrorCount),
        WarningCount = SchedulingValueFormatter.ToInt(r.WarningCount),
        AvailabilityWeek = SchedulingValueFormatter.DateToString(r.AvailabilityWeek),
        RunId = r.RunId is null ? null : SchedulingValueFormatter.ToInt(r.RunId),
        Note = r.Note,
        CreatedAt = SchedulingValueFormatter.DateTimeToString(r.CreatedAt) ?? "",
        CreatedBy = r.CreatedBy ?? "",
        RunStatus = r.RunStatus,
        RunFinishedAt = SchedulingValueFormatter.DateTimeToString(r.RunFinishedAt)
    };

    private static DaySummaryDto MapDaySummary(dynamic r) => new()
    {
        WorkDate = SchedulingValueFormatter.DateToString(r.WorkDate) ?? "",
        Weekday = r.Weekday ?? "",
        DayStatus = r.DayStatus ?? "",
        ForecastTc = SchedulingValueFormatter.ToDouble(r.ForecastTc),
        RegularHours = SchedulingValueFormatter.ToDouble(r.RegularHours),
        TrainingHours = SchedulingValueFormatter.ToDouble(r.TrainingHours),
        NsoHours = SchedulingValueFormatter.ToDouble(r.NsoHours),
        Tcph = SchedulingValueFormatter.ToDouble(r.Tcph),
        TcphInclNso = SchedulingValueFormatter.ToDouble(r.TcphInclNso),
        TcphInTarget = r.TcphInTarget is null ? null : SchedulingValueFormatter.ToBool(r.TcphInTarget),
        TargetHoursMin = SchedulingValueFormatter.ToDouble(r.TargetHoursMin),
        TargetHoursMax = SchedulingValueFormatter.ToDouble(r.TargetHoursMax),
        NeededStaffHours = r.NeededStaffHours is null ? null : SchedulingValueFormatter.ToInt(r.NeededStaffHours),
        ScheduledStaffHours = r.ScheduledStaffHours is null ? null : SchedulingValueFormatter.ToInt(r.ScheduledStaffHours),
        MissingStaffHours = r.MissingStaffHours is null ? null : SchedulingValueFormatter.ToInt(r.MissingStaffHours),
        HoursWithoutManager = r.HoursWithoutManager is null ? null : SchedulingValueFormatter.ToInt(r.HoursWithoutManager),
        Openers = r.Openers is null ? null : SchedulingValueFormatter.ToInt(r.Openers),
        Closers = r.Closers is null ? null : SchedulingValueFormatter.ToInt(r.Closers)
    };

    private static HourCoverageDto MapHourCoverage(dynamic r) => new()
    {
        WorkDate = SchedulingValueFormatter.DateToString(r.WorkDate) ?? "",
        Weekday = r.Weekday ?? "",
        Slot = SchedulingValueFormatter.ToInt(r.Slot),
        TimeSlot = r.TimeSlot ?? "",
        ForecastTc = SchedulingValueFormatter.ToDouble(r.ForecastTc) ?? 0,
        IsPeakHour = SchedulingValueFormatter.ToBool(r.IsPeakHour),
        NeededStaff = SchedulingValueFormatter.ToInt(r.NeededStaff),
        ScheduledStaff = SchedulingValueFormatter.ToInt(r.ScheduledStaff),
        ManagersOnDuty = SchedulingValueFormatter.ToInt(r.ManagersOnDuty),
        MissingStaff = SchedulingValueFormatter.ToInt(r.MissingStaff),
        Status = r.Status ?? ""
    };

    private static RosterDayDto MapRosterDay(dynamic r) => new()
    {
        WorkDate = SchedulingValueFormatter.DateToString(r.WorkDate) ?? "",
        Weekday = r.Weekday ?? "",
        EmployeeId = r.EmployeeId ?? "",
        EmployeeName = r.EmployeeName ?? "",
        Position = r.Position ?? "",
        EmploymentType = r.EmploymentType ?? "",
        LaborGroup = r.LaborGroup ?? "",
        HomeStore = r.HomeStore,
        DayType = r.DayType ?? "",
        StartTime = SchedulingValueFormatter.TimeToString(r.StartTime),
        EndTime = SchedulingValueFormatter.TimeToString(r.EndTime),
        Hours = SchedulingValueFormatter.ToDouble(r.Hours) ?? 0,
        ShiftCode = r.ShiftCode,
        ShiftRole = r.ShiftRole,
        Note = r.Note,
        SortOrder = SchedulingValueFormatter.ToInt(r.SortOrder)
    };

    private static ScheduleIssueDto MapIssue(dynamic r) => new()
    {
        Severity = r.Severity ?? "",
        WorkDate = SchedulingValueFormatter.DateToString(r.WorkDate),
        EmployeeId = r.EmployeeId,
        EmployeeName = r.EmployeeName,
        Message = r.Message ?? "",
        IssueCode = r.IssueCode
    };

    public static SchedulingRunDto MapRun(dynamic r) => new()
    {
        RunId = SchedulingValueFormatter.ToInt(r.RunId),
        StoreCode = r.StoreCode,
        WeekStart = SchedulingValueFormatter.DateToString(r.WeekStart) ?? "",
        AvailabilityWeek = SchedulingValueFormatter.DateToString(r.AvailabilityWeek),
        Status = r.Status ?? "",
        Assessment = r.Assessment,
        Message = r.Message,
        RequestedBy = r.RequestedBy ?? "",
        RequestedAt = SchedulingValueFormatter.DateTimeToString(r.RequestedAt) ?? "",
        StartedAt = SchedulingValueFormatter.DateTimeToString(r.StartedAt),
        FinishedAt = SchedulingValueFormatter.DateTimeToString(r.FinishedAt)
    };
}