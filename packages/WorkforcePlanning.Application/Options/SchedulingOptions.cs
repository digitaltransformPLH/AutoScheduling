namespace WorkforcePlanning.Application.Options;

public class SchedulingOptions
{
    public const string SectionName = "Scheduling";

    public bool BackTest { get; set; }
    public string? DefaultAvailabilityWeek { get; set; }
    public string? EngineBaseUrl { get; set; }
    public string PythonExecutable { get; set; } = "python";
}