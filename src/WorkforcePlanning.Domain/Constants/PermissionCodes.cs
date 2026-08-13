namespace WorkforcePlanning.Domain.Constants;

public static class PermissionCodes
{
    // Published data
    public const string PublishedView = "Action.Published.View";
    public const string PublishSchedule = "Action.Publish.Schedule";

    // Planning workflow (tabs)
    public const string PlanningInputView = "Action.Planning.Input.View";
    public const string PlanningOverviewView = "Action.Planning.Overview.View";
    public const string PlanningAnalysisView = "Action.Planning.Analysis.View";

    // Reporting/workspaces
    public const string DashboardView = "Action.Dashboard.View";
    public const string ZonePlanningView = "Action.ZonePlanning.View";

    // Admin (menu-level permissions)
    public const string AmOmManage = "Action.AmOm.Manage";

    public const string UserManage = "Action.User.Manage";
    public const string RoleManage = "Action.Role.Manage";
    public const string StoreView = "Action.Store.View";
    public const string StoreManage = "Action.Store.Manage";

    public static readonly string[] All =
    [
        PublishedView,
        PublishSchedule,
        PlanningInputView,
        PlanningOverviewView,
        PlanningAnalysisView,
        DashboardView,
        ZonePlanningView,
        AmOmManage,
        UserManage,
        RoleManage,
        StoreView,
        StoreManage
    ];
}
