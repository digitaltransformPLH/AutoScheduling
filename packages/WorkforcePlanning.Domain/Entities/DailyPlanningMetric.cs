namespace WorkforcePlanning.Domain.Entities;

public class DailyPlanningMetric
{
    public long Id { get; set; }
    public string StoreCode { get; set; } = string.Empty;
    public string? StoreName { get; set; }
    public string? AreaManager { get; set; }
    public string? OperationManager { get; set; }
    public DateOnly Date { get; set; }
    public string Day { get; set; } = string.Empty;
    public int Month { get; set; }
    public int Year { get; set; }
    public decimal? ADTC { get; set; }
    public decimal? LaborReg { get; set; }
    public decimal? LaborTrain { get; set; }
    public decimal? LaborNSO { get; set; }
    public decimal? TCPH { get; set; }
    public decimal? TcphNSO { get; set; }
    public string PublishId { get; set; } = string.Empty;
    public int PublishVersion { get; set; }
    public DateTimeOffset PublishedAt { get; set; }
    public string PublishedBy { get; set; } = string.Empty;
}
