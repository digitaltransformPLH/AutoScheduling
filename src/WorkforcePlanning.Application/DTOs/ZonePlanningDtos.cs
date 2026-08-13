using System.Text.Json.Serialization;

namespace WorkforcePlanning.Application.DTOs;

public class ZonePlanningMetricsDto
{
    [JsonPropertyName("published")]
    public int Published { get; set; }

    [JsonPropertyName("adtc")]
    public decimal Adtc { get; set; }

    [JsonPropertyName("laborReg")]
    public decimal LaborReg { get; set; }

    [JsonPropertyName("laborTrain")]
    public decimal LaborTrain { get; set; }

    [JsonPropertyName("laborNso")]
    public decimal LaborNso { get; set; }

    [JsonPropertyName("tcph")]
    public decimal? Tcph { get; set; }

    [JsonPropertyName("tcphNso")]
    public decimal? TcphNso { get; set; }
}

public class ZonePlanningAmDto
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("weekly")]
    public ZonePlanningMetricsDto Weekly { get; set; } = new();

    [JsonPropertyName("monthly")]
    public ZonePlanningMetricsDto Monthly { get; set; } = new();
}

public class ZonePlanningGroupDto
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("weekly")]
    public ZonePlanningMetricsDto Weekly { get; set; } = new();

    [JsonPropertyName("monthly")]
    public ZonePlanningMetricsDto Monthly { get; set; } = new();

    [JsonPropertyName("ams")]
    public List<ZonePlanningAmDto> Ams { get; set; } = new();
}

public class ZonePlanningPeriodsDto
{
    [JsonPropertyName("weekly")]
    public string? Weekly { get; set; }

    [JsonPropertyName("monthly")]
    public string? Monthly { get; set; }
}

public class ZonePlanningSummaryDto
{
    [JsonPropertyName("week")]
    public int Week { get; set; }

    [JsonPropertyName("month")]
    public int Month { get; set; }

    [JsonPropertyName("year")]
    public int Year { get; set; }

    [JsonPropertyName("accessibleStores")]
    public int AccessibleStores { get; set; }

    [JsonPropertyName("weeklyPublished")]
    public int WeeklyPublished { get; set; }

    [JsonPropertyName("monthlyPublished")]
    public int MonthlyPublished { get; set; }

    [JsonPropertyName("rowCount")]
    public int RowCount { get; set; }
}

public class ZonePlanningViewDto
{
    [JsonPropertyName("totalWeekly")]
    public ZonePlanningMetricsDto TotalWeekly { get; set; } = new();

    [JsonPropertyName("totalMonthly")]
    public ZonePlanningMetricsDto TotalMonthly { get; set; } = new();

    [JsonPropertyName("groups")]
    public List<ZonePlanningGroupDto> Groups { get; set; } = new();
}

public class ZonePlanningResponseDto
{
    [JsonPropertyName("periods")]
    public ZonePlanningPeriodsDto Periods { get; set; } = new();

    [JsonPropertyName("view")]
    public ZonePlanningViewDto View { get; set; } = new();

    [JsonPropertyName("summary")]
    public ZonePlanningSummaryDto Summary { get; set; } = new();
}

