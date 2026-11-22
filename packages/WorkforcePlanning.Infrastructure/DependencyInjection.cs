using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Application.Options;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;
using WorkforcePlanning.Infrastructure.Services;

namespace WorkforcePlanning.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        var connectionString = configuration.GetConnectionString("DefaultConnection")
            ?? "Server=localhost;Database=WorkforcePlanning;Trusted_Connection=True;TrustServerCertificate=True;";

        services.AddDbContext<WorkforcePlanningDbContext>(options =>
            options
                .UseSqlServer(connectionString)
                // When we add new HasData entries for RBAC, older DBs may have pending model changes.
                // For this app scenario, we want the background seeding to still run.
                .ConfigureWarnings(w => w.Ignore(RelationalEventId.PendingModelChangesWarning)));

        services.AddHttpContextAccessor();
        services.AddScoped<ICurrentUserService, CurrentUserService>();
        services.AddScoped<IAuthService, AuthService>();
        services.AddScoped<IPublishService, PublishService>();
        services.AddScoped<IUserAdminService, UserAdminService>();
        services.AddScoped<IRoleAdminService, RoleAdminService>();
        services.AddScoped<StoreOrgServiceHelper>();
        services.AddScoped<IStoreQueryService, StoreQueryService>();
        services.AddScoped<IPersonQueryService, PersonQueryService>();
        services.AddScoped<IAmOmAssignmentService, AmOmAssignmentService>();
        services.AddScoped<IEmployeeAdminService, EmployeeAdminService>();
        services.AddScoped<IEmployeeSecondmentService, EmployeeSecondmentService>();
        services.AddScoped<IEmployeeAvailabilityService, EmployeeAvailabilityService>();
        services.AddScoped<IStoreConfigService, StoreConfigService>();
        services.AddScoped<IZonePlanningService, ZonePlanningService>();
        services.AddScoped<ISchedulingReadService, SchedulingReadService>();
        services.AddScoped<ISchedulingRunService, SchedulingRunService>();
        services.AddScoped<ISchedulingFile2ExportService, SchedulingFile2ExportService>();

        return services;
    }

    /// <summary>
    /// Migrate DB and ensure admin user from Auth options exists.
    /// </summary>
    public static async Task EnsureRbacSeedAsync(IServiceProvider services)
    {
        using var scope = services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<WorkforcePlanningDbContext>();
        await db.Database.MigrateAsync();

        var logger = scope.ServiceProvider.GetService<ILoggerFactory>()?.CreateLogger("StoreOrgSeed");
        await StoreOrgSeedService.EnsureSeedAsync(db, logger);

        var auth = scope.ServiceProvider.GetRequiredService<IOptions<AuthOptions>>().Value;
        var authOptions = scope.ServiceProvider.GetRequiredService<IOptions<AuthOptions>>();
        await OrgUserSeedService.EnsureSeedAsync(db, authOptions, logger, cancellationToken: default);

        // Ensure menu-level permissions exist even if the DB was created before we added them.
        await EnsureMenuLevelPermissionsAsync(db, cancellationToken: default);

        var email = (auth.AdminEmail ?? "admin@phuclong.com").Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(email)) return;

        var adminRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Administrator");
        if (adminRole is null) return;

        var storeManagePerm = await db.Permissions.FirstOrDefaultAsync(p => p.Code == PermissionCodes.StoreManage);
        if (storeManagePerm is not null
            && !await db.RolePermissions.AnyAsync(rp => rp.RoleId == adminRole.Id && rp.PermissionId == storeManagePerm.Id))
        {
            db.RolePermissions.Add(new RolePermission { RoleId = adminRole.Id, PermissionId = storeManagePerm.Id });
            await db.SaveChangesAsync();
        }

        var hasher = new PasswordHasher<User>();
        var user = await db.Users.FirstOrDefaultAsync(u => u.Email == email);
        if (user is null)
        {
            user = new User
            {
                Email = email,
                DisplayName = string.IsNullOrWhiteSpace(auth.AdminDisplayName) ? "Administrator" : auth.AdminDisplayName.Trim(),
                RoleId = adminRole.Id,
                AllStores = true,
                IsActive = true
            };
            user.PasswordHash = hasher.HashPassword(user, string.IsNullOrWhiteSpace(auth.AdminPassword) ? "Admin@123" : auth.AdminPassword);
            db.Users.Add(user);
        }
        else
        {
            user.RoleId = adminRole.Id;
            user.AllStores = true;
            user.IsActive = true;
            if (!string.IsNullOrWhiteSpace(auth.AdminDisplayName))
                user.DisplayName = auth.AdminDisplayName.Trim();
        }

        await db.SaveChangesAsync();
    }

    private static async Task EnsureMenuLevelPermissionsAsync(WorkforcePlanningDbContext db, CancellationToken cancellationToken)
    {
        // Seed only "new" menu-level permissions. Existing permissions are expected to exist already.
        var requiredPermissions = new Dictionary<string, string>
        {
            [PermissionCodes.PlanningInputView] = "Xem tab Nhập dữ liệu & Cấu hình",
            [PermissionCodes.PlanningOverviewView] = "Xem tab Tổng quan",
            [PermissionCodes.PlanningAnalysisView] = "Xem tab Phân tích & Weekly roster",
            [PermissionCodes.DashboardView] = "Xem Dashboard",
            [PermissionCodes.ZonePlanningView] = "Xem Zone Planning",
            [PermissionCodes.AmOmManage] = "Quản lý Mapping AM → OM",
            [PermissionCodes.EmployeeView] = "Xem danh sách nhân viên",
            [PermissionCodes.EmployeeManage] = "Quản lý nhân viên",
            [PermissionCodes.EmployeeAvailabilityView] = "Xem lịch bận nhân viên",
            [PermissionCodes.EmployeeAvailabilityManage] = "Quản lý lịch bận nhân viên",
            [PermissionCodes.StoreConfigView] = "Xem cấu hình OPS cửa hàng",
            [PermissionCodes.StoreConfigManage] = "Quản lý cấu hình OPS cửa hàng",
        };

        foreach (var (code, name) in requiredPermissions)
        {
            if (await db.Permissions.AnyAsync(p => p.Code == code, cancellationToken))
                continue;

            db.Permissions.Add(new Permission { Code = code, Name = name });
        }

        await db.SaveChangesAsync(cancellationToken);

        // Seed default permission sets for system roles.
        // Note: this is only for baseline behavior; admin can change/assign permissions later.
        var adminRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Administrator", cancellationToken);
        var managerRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Manager", cancellationToken);
        var staffRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Staff", cancellationToken);
        var viewerRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Viewer", cancellationToken);
        if (adminRole is null || managerRole is null || staffRole is null || viewerRole is null)
            return;

        var allPerms = PermissionCodes.All;
        await EnsureRolePermissionsAsync(db, adminRole.Id, allPerms, cancellationToken);

        var managerPerms = new[]
        {
            PermissionCodes.PublishedView,
            PermissionCodes.PublishSchedule,
            PermissionCodes.StoreView,
            PermissionCodes.PlanningInputView,
            PermissionCodes.PlanningOverviewView,
            PermissionCodes.PlanningAnalysisView,
            PermissionCodes.EmployeeAvailabilityView,
            PermissionCodes.EmployeeAvailabilityManage,
            PermissionCodes.StoreConfigView,
            PermissionCodes.StoreConfigManage,
        };
        await EnsureRolePermissionsAsync(db, managerRole.Id, managerPerms, cancellationToken);

        var staffPerms = new[]
        {
            PermissionCodes.PublishedView,
            PermissionCodes.StoreView,
        };
        await EnsureRolePermissionsAsync(db, staffRole.Id, staffPerms, cancellationToken);

        var viewerPerms = new[]
        {
            PermissionCodes.PublishedView,
        };
        await EnsureRolePermissionsAsync(db, viewerRole.Id, viewerPerms, cancellationToken);
    }

    private static async Task EnsureRolePermissionsAsync(
        WorkforcePlanningDbContext db,
        int roleId,
        IEnumerable<string> permCodes,
        CancellationToken cancellationToken)
    {
        var permIds = await db.Permissions
            .Where(p => permCodes.Contains(p.Code))
            .Select(p => p.Id)
            .ToListAsync(cancellationToken);

        foreach (var permId in permIds)
        {
            if (await db.RolePermissions.AnyAsync(rp => rp.RoleId == roleId && rp.PermissionId == permId, cancellationToken))
                continue;

            db.RolePermissions.Add(new RolePermission { RoleId = roleId, PermissionId = permId });
        }

        await db.SaveChangesAsync(cancellationToken);
    }
}
