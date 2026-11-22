namespace WorkforcePlanning.Application.DTOs;

public class SchedulingMetaDto
{
    public int DataVersion { get; set; }
    public string? BuiltAt { get; set; }
    public string Source { get; set; } = "sched";
    public bool BackTest { get; set; }
    public string? AvailabilityWeek { get; set; }
}

public class SchedulingEnvelope<T>
{
    public T Data { get; set; } = default!;
    public SchedulingMetaDto Meta { get; set; } = new();
}

public class SchedulingStoreItemDto
{
    public string StoreCode { get; set; } = string.Empty;
    public string StoreName { get; set; } = string.Empty;
    public string? OpeningTime { get; set; }
    public string? ClosingTime { get; set; }
    public double? TcphTarget { get; set; }
    public int EmployeeCount { get; set; }
    public bool HasForecast { get; set; }
    public bool ReadyToSchedule { get; set; }
    public int ScheduledWeeks { get; set; }
}

public class ForecastWeekDto
{
    public string WeekStart { get; set; } = string.Empty;
    public int StoreCount { get; set; }
    public string? CreatedAt { get; set; }
    public string? MethodVersion { get; set; }
}

public class ScheduleWeekDto
{
    public string StoreCode { get; set; } = string.Empty;
    public string WeekStart { get; set; } = string.Empty;
    public string WeekEnd { get; set; } = string.Empty;
    public string? StoreName { get; set; }
    public string? OpeningTime { get; set; }
    public string? ClosingTime { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? Assessment { get; set; }
    public double? TcphTarget { get; set; }
    public double? WeeklyTcph { get; set; }
    public bool? TcphInTarget { get; set; }
    public double? ForecastTc { get; set; }
    public double? LaborHours { get; set; }
    public double? NsoHours { get; set; }
    public double? StaffCoveragePct { get; set; }
    public double? ManagerCoveragePct { get; set; }
    public int EmployeeCount { get; set; }
    public int ErrorCount { get; set; }
    public int WarningCount { get; set; }
    public string? AvailabilityWeek { get; set; }
    public int? RunId { get; set; }
    public string? Note { get; set; }
    public string CreatedAt { get; set; } = string.Empty;
    public string CreatedBy { get; set; } = string.Empty;
    public string? RunStatus { get; set; }
    public string? RunFinishedAt { get; set; }
}

public class DaySummaryDto
{
    public string WorkDate { get; set; } = string.Empty;
    public string Weekday { get; set; } = string.Empty;
    public string DayStatus { get; set; } = string.Empty;
    public double? ForecastTc { get; set; }
    public double? RegularHours { get; set; }
    public double? TrainingHours { get; set; }
    public double? NsoHours { get; set; }
    public double? Tcph { get; set; }
    public double? TcphInclNso { get; set; }
    public bool? TcphInTarget { get; set; }
    public double? TargetHoursMin { get; set; }
    public double? TargetHoursMax { get; set; }
    public int? NeededStaffHours { get; set; }
    public int? ScheduledStaffHours { get; set; }
    public int? MissingStaffHours { get; set; }
    public int? HoursWithoutManager { get; set; }
    public int? Openers { get; set; }
    public int? Closers { get; set; }
}

public class HourCoverageDto
{
    public string WorkDate { get; set; } = string.Empty;
    public string Weekday { get; set; } = string.Empty;
    public int Slot { get; set; }
    public string TimeSlot { get; set; } = string.Empty;
    public double ForecastTc { get; set; }
    public bool IsPeakHour { get; set; }
    public int NeededStaff { get; set; }
    public int ScheduledStaff { get; set; }
    public int ManagersOnDuty { get; set; }
    public int MissingStaff { get; set; }
    public string Status { get; set; } = string.Empty;
}

public class RosterDayDto
{
    public string WorkDate { get; set; } = string.Empty;
    public string Weekday { get; set; } = string.Empty;
    public string EmployeeId { get; set; } = string.Empty;
    public string EmployeeName { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
    public string EmploymentType { get; set; } = string.Empty;
    public string LaborGroup { get; set; } = string.Empty;
    public string? HomeStore { get; set; }
    public string DayType { get; set; } = string.Empty;
    public string? StartTime { get; set; }
    public string? EndTime { get; set; }
    public double Hours { get; set; }
    public string? ShiftCode { get; set; }
    public string? ShiftRole { get; set; }
    public string? Note { get; set; }
    public int SortOrder { get; set; }
}

public class ScheduleIssueDto
{
    public string Severity { get; set; } = string.Empty;
    public string? WorkDate { get; set; }
    public string? EmployeeId { get; set; }
    public string? EmployeeName { get; set; }
    public string Message { get; set; } = string.Empty;
    public string? IssueCode { get; set; }
}

public class OverviewDto
{
    public ScheduleWeekDto Week { get; set; } = new();
    public List<DaySummaryDto> Days { get; set; } = new();
    public List<HourCoverageDto> Hourly { get; set; } = new();
    public List<RosterDayDto> Roster { get; set; } = new();
    public List<ScheduleIssueDto> Issues { get; set; } = new();
}

public class SchedulingRunDto
{
    public int RunId { get; set; }
    public string StoreCode { get; set; } = string.Empty;
    public string WeekStart { get; set; } = string.Empty;
    public string? AvailabilityWeek { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? Assessment { get; set; }
    public string? Message { get; set; }
    public string RequestedBy { get; set; } = string.Empty;
    public string RequestedAt { get; set; } = string.Empty;
    public string? StartedAt { get; set; }
    public string? FinishedAt { get; set; }
}

public class StartSchedulingRunRequest
{
    public string StoreCode { get; set; } = string.Empty;
    public string WeekStart { get; set; } = string.Empty;
    public string? AvailabilityWeek { get; set; }
}

public class File2ExportResult
{
    public byte[] Content { get; set; } = Array.Empty<byte>();
    public string FileName { get; set; } = "upload_phan_cong.xlsx";
}