namespace WorkforcePlanning.Application.DTOs;

public class EmployeeAvailabilitySlotListItemDto
{
    public int Id { get; set; }
    public string PlantCode { get; set; } = string.Empty;
    public string? PlantName { get; set; }
    public long EmployeeNumber { get; set; }
    public int? EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public string WeekStartMonday { get; set; } = string.Empty;
    public string WorkDate { get; set; } = string.Empty;
    public string WeekdayLabel { get; set; } = string.Empty;
    public string? BusyFrom { get; set; }
    public string? BusyTo { get; set; }
    public bool IsPaidLeave { get; set; }
}

public class EmployeeAvailabilityWeekResponse
{
    public string WeekStartMonday { get; set; } = string.Empty;
    public string WeekEndSunday { get; set; } = string.Empty;
    public string? PlantCode { get; set; }
    public List<EmployeeAvailabilitySlotListItemDto> Items { get; set; } = new();
    public int Total { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
    public int TotalPages { get; set; }
}

public class UpsertEmployeeAvailabilitySlotRequest
{
    public string PlantCode { get; set; } = string.Empty;
    public long EmployeeNumber { get; set; }
    public string WorkDate { get; set; } = string.Empty;
    public string? BusyFrom { get; set; }
    public string? BusyTo { get; set; }
    public bool IsPaidLeave { get; set; }
}

public class EmployeeAvailabilityImportResultDto
{
    public int Created { get; set; }
    public int Failed { get; set; }
    public List<EmployeeImportRowErrorDto> Errors { get; set; } = new();
    public string WeekStartMonday { get; set; } = string.Empty;
    public string WeekEndSunday { get; set; } = string.Empty;
}

/// <summary>Nhân viên được chọn khi thêm lịch bận (thuộc store hoặc mượn vào còn hạn trong tuần).</summary>
public class EmployeeAvailabilityEmployeePickDto
{
    public long EmployeeNumber { get; set; }
    public string FullName { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
  /// <summary>store | borrowed</summary>
    public string Source { get; set; } = string.Empty;
    public string? HomePlantCode { get; set; }
    public string? SecondmentStart { get; set; }
    public string? SecondmentEnd { get; set; }
}