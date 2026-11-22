namespace WorkforcePlanning.Domain.Constants;

public static class EmployeeCatalog
{
    public static readonly string[] Positions =
    [
        "Store Manager",
        "Shift Supervisor",
        "Crew member",
        "Barista Trainer"
    ];

    public static readonly string[] EmploymentTypes = ["FT", "PT"];

    public static readonly string[] LaborGroups = ["Regular"];

    public static readonly string[] Statuses = ["Active", "Inactive"];
}