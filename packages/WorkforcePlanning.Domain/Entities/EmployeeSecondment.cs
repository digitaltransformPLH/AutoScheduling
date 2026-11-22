namespace WorkforcePlanning.Domain.Entities;

public class EmployeeSecondment
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public string HomePlantCode { get; set; } = string.Empty;
    public string ReceivingStoreCode { get; set; } = string.Empty;
    public DateOnly StartDate { get; set; }
    public DateOnly EndDate { get; set; }
    public string Status { get; set; } = SecondmentStatuses.Active;
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public string UpdatedBy { get; set; } = string.Empty;

    public Employee? Employee { get; set; }
    public Store? ReceivingStore { get; set; }
}

public static class SecondmentStatuses
{
    public const string Active = "Active";
    public const string Cancelled = "Cancelled";
}