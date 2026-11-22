namespace WorkforcePlanning.Domain.Entities;

public class EmployeeAvailabilitySlot
{
    public int Id { get; set; }
    public string PlantCode { get; set; } = string.Empty;
    public long EmployeeNumber { get; set; }
    public int? EmployeeId { get; set; }
    public DateOnly WeekStartMonday { get; set; }
    public DateOnly WorkDate { get; set; }
    public TimeOnly? BusyFrom { get; set; }
    public TimeOnly? BusyTo { get; set; }
    public bool IsPaidLeave { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }

    public Employee? Employee { get; set; }
    public Store? Plant { get; set; }
}