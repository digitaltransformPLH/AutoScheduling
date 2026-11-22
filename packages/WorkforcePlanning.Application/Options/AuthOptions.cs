namespace WorkforcePlanning.Application.Options;

public class AuthOptions
{
    public const string SectionName = "Auth";

    /// <summary>Admin seed email (created on startup if missing).</summary>
    public string AdminEmail { get; set; } = "admin@phuclong.com";

    public string AdminPassword { get; set; } = "Admin@123";

    public string AdminDisplayName { get; set; } = "Administrator";

    /// <summary>Cookie session lifetime in hours.</summary>
    public int SessionHours { get; set; } = 10;

    /// <summary>Default password for AM/OM users created from org seed.</summary>
    public string OrgUserDefaultPassword { get; set; } = "PLH@2026";
}
