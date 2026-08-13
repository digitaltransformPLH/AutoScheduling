using System.Text.Json.Serialization;

namespace WorkforcePlanning.Application.DTOs;

public class PublishScheduleRequest
{
    public string? Action { get; set; }
    public string StoreCode { get; set; } = string.Empty;
    public string WeekStart { get; set; } = string.Empty;
    public string WeekEnd { get; set; } = string.Empty;
    public string PublishId { get; set; } = string.Empty;
    public int PublishVersion { get; set; }
    public string PublishedAt { get; set; } = string.Empty;
    public List<DailyRecordDto> Records { get; set; } = new();
}

public class DailyRecordDto
{
    [JsonPropertyName("Store Code")]
    public string StoreCode { get; set; } = string.Empty;

    [JsonPropertyName("Store Name")]
    public string? StoreName { get; set; }

    [JsonPropertyName("Area Manager")]
    public string? AreaManager { get; set; }

    [JsonPropertyName("Operation Manager")]
    public string? OperationManager { get; set; }

    public string Date { get; set; } = string.Empty;
    public string Day { get; set; } = string.Empty;
    public int Month { get; set; }
    public int Year { get; set; }
    public decimal? ADTC { get; set; }

    [JsonPropertyName("Labor Reg")]
    public decimal? LaborReg { get; set; }

    [JsonPropertyName("Labor Train")]
    public decimal? LaborTrain { get; set; }

    [JsonPropertyName("Labor NSO")]
    public decimal? LaborNSO { get; set; }

    public decimal? TCPH { get; set; }

    [JsonPropertyName("TCPH-NSO")]
    public decimal? TcphNSO { get; set; }

    [JsonPropertyName("Publish ID")]
    public string PublishId { get; set; } = string.Empty;

    [JsonPropertyName("Publish Version")]
    public int PublishVersion { get; set; }

    [JsonPropertyName("Published At")]
    public string PublishedAt { get; set; } = string.Empty;
}

public class PublishScheduleResponse
{
    public bool Success { get; set; }
    public int RowsInserted { get; set; }
    public string PublishId { get; set; } = string.Empty;
    public int PublishVersion { get; set; }
    public string? Message { get; set; }
}

public class DailyMetricsWeekResponse
{
    public string StoreCode { get; set; } = string.Empty;
    public string WeekStart { get; set; } = string.Empty;
    public int? PublishVersion { get; set; }
    public string? PublishId { get; set; }
    public List<DailyRecordDto> Records { get; set; } = new();
}
