using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;

namespace WorkforcePlanning.Infrastructure.Persistence;

public class WorkforcePlanningDbContext : DbContext
{
    public WorkforcePlanningDbContext(DbContextOptions<WorkforcePlanningDbContext> options)
        : base(options)
    {
    }

    public DbSet<Store> Stores => Set<Store>();
    public DbSet<User> Users => Set<User>();
    public DbSet<UserStore> UserStores => Set<UserStore>();
    public DbSet<Role> Roles => Set<Role>();
    public DbSet<Permission> Permissions => Set<Permission>();
    public DbSet<RolePermission> RolePermissions => Set<RolePermission>();
    public DbSet<DailyPlanningMetric> DailyPlanningMetrics => Set<DailyPlanningMetric>();
    public DbSet<DimStoreDetail> DimStoreDetails => Set<DimStoreDetail>();
    public DbSet<Person> Persons => Set<Person>();
    public DbSet<AmOmAssignment> AmOmAssignments => Set<AmOmAssignment>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Store>(e =>
        {
            e.ToTable("Stores");
            e.HasKey(x => x.Id);
            e.Property(x => x.Code).HasMaxLength(10).IsRequired();
            e.Property(x => x.Name).HasMaxLength(200).IsRequired();
            e.Property(x => x.City).HasMaxLength(100);
            e.Property(x => x.Concept).HasMaxLength(50);
            e.Property(x => x.Email).HasMaxLength(256);
            e.HasIndex(x => x.Code).IsUnique();
            e.HasIndex(x => x.AreaManagerId);
            e.HasOne(x => x.AreaManager)
                .WithMany(p => p.ManagedStores)
                .HasForeignKey(x => x.AreaManagerId)
                .OnDelete(DeleteBehavior.SetNull);
        });

        modelBuilder.Entity<Person>(e =>
        {
            e.ToTable("Persons");
            e.HasKey(x => x.Id);
            e.Property(x => x.FullName).HasMaxLength(200).IsRequired();
            e.Property(x => x.Email).HasMaxLength(256);
            e.Property(x => x.Phone).HasMaxLength(50);
            e.Property(x => x.Role).HasMaxLength(10).IsRequired();
            e.HasIndex(x => x.Role);
            e.HasIndex(x => x.FullName);
        });

        modelBuilder.Entity<AmOmAssignment>(e =>
        {
            e.ToTable("AmOmAssignments");
            e.HasKey(x => x.Id);
            e.HasIndex(x => new { x.AreaManagerId, x.EffectiveTo });
            e.HasOne(x => x.AreaManager)
                .WithMany(p => p.AreaManagerAssignments)
                .HasForeignKey(x => x.AreaManagerId)
                .OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.OperationManager)
                .WithMany(p => p.OperationManagerAssignments)
                .HasForeignKey(x => x.OperationManagerId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<Role>(e =>
        {
            e.ToTable("Roles");
            e.HasKey(x => x.Id);
            e.Property(x => x.Name).HasMaxLength(100).IsRequired();
            e.Property(x => x.Description).HasMaxLength(500);
            e.HasIndex(x => x.Name).IsUnique();
        });

        modelBuilder.Entity<Permission>(e =>
        {
            e.ToTable("Permissions");
            e.HasKey(x => x.Id);
            e.Property(x => x.Code).HasMaxLength(100).IsRequired();
            e.Property(x => x.Name).HasMaxLength(200).IsRequired();
            e.HasIndex(x => x.Code).IsUnique();
        });

        modelBuilder.Entity<RolePermission>(e =>
        {
            e.ToTable("RolePermissions");
            e.HasKey(x => new { x.RoleId, x.PermissionId });
            e.HasOne(x => x.Role).WithMany(r => r.RolePermissions).HasForeignKey(x => x.RoleId);
            e.HasOne(x => x.Permission).WithMany(p => p.RolePermissions).HasForeignKey(x => x.PermissionId);
        });

        modelBuilder.Entity<User>(e =>
        {
            e.ToTable("Users");
            e.HasKey(x => x.Id);
            e.Property(x => x.Email).HasMaxLength(256).IsRequired();
            e.Property(x => x.DisplayName).HasMaxLength(200).IsRequired();
            e.Property(x => x.PasswordHash).HasMaxLength(500).IsRequired();
            e.HasIndex(x => x.Email).IsUnique();
            e.HasOne(x => x.Role).WithMany(r => r.Users).HasForeignKey(x => x.RoleId);
        });

        modelBuilder.Entity<UserStore>(e =>
        {
            e.ToTable("UserStores");
            e.HasKey(x => x.Id);
            e.HasIndex(x => new { x.UserId, x.StoreId }).IsUnique();
            e.HasOne(x => x.User).WithMany(u => u.UserStores).HasForeignKey(x => x.UserId);
            e.HasOne(x => x.Store).WithMany(s => s.UserStores).HasForeignKey(x => x.StoreId);
        });

        modelBuilder.Entity<DimStoreDetail>(e =>
        {
            e.ToTable("dim_store_detail");
            e.HasKey(x => x.StoreCode);
            e.Property(x => x.StoreCode).HasMaxLength(10).IsRequired();
            e.Property(x => x.StoreName).HasMaxLength(200).IsRequired();
            e.Property(x => x.Concept).HasMaxLength(50);
            e.Property(x => x.City).HasMaxLength(100);
            e.Property(x => x.AreaManager).HasMaxLength(200).IsRequired();
            e.Property(x => x.OperationManager).HasMaxLength(200).IsRequired();
            e.Property(x => x.Region).HasMaxLength(1).IsRequired();
            e.HasIndex(x => x.AreaManager);
            e.HasIndex(x => x.OperationManager);
            e.HasIndex(x => x.Region);
        });

        modelBuilder.Entity<DailyPlanningMetric>(e =>
        {
            e.ToTable("DailyPlanningMetrics");
            e.HasKey(x => x.Id);
            e.Property(x => x.StoreCode).HasMaxLength(10).IsRequired();
            e.Property(x => x.StoreName).HasMaxLength(200);
            e.Property(x => x.AreaManager).HasMaxLength(200);
            e.Property(x => x.OperationManager).HasMaxLength(200);
            e.Property(x => x.Day).HasMaxLength(20).IsRequired();
            e.Property(x => x.ADTC).HasPrecision(18, 4);
            e.Property(x => x.LaborReg).HasPrecision(18, 2);
            e.Property(x => x.LaborTrain).HasPrecision(18, 2);
            e.Property(x => x.LaborNSO).HasPrecision(18, 2);
            e.Property(x => x.TCPH).HasPrecision(18, 4);
            e.Property(x => x.TcphNSO).HasPrecision(18, 4);
            e.Property(x => x.PublishId).HasMaxLength(64).IsRequired();
            e.Property(x => x.PublishedBy).HasMaxLength(256).IsRequired();
            e.HasIndex(x => new { x.StoreCode, x.Date, x.PublishVersion }).IsUnique();
            e.HasIndex(x => new { x.StoreCode, x.Date });
            e.HasIndex(x => x.PublishId);
        });

        SeedRbac(modelBuilder);

        modelBuilder.Entity<Store>().HasData(
            new Store { Id = 1, Code = "2026", Name = "HCM-CH Đường số 7 P.Bình Trị Đông", IsActive = true },
            new Store { Id = 2, Code = "0001", Name = "Sample Store 0001", IsActive = true }
        );
    }

    private static void SeedRbac(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Permission>().HasData(
            new Permission { Id = 1, Code = PermissionCodes.PublishedView, Name = "Xem dữ liệu đã publish" },
            new Permission { Id = 2, Code = PermissionCodes.PublishSchedule, Name = "Publish schedule" },
            new Permission { Id = 3, Code = PermissionCodes.UserManage, Name = "Quản lý người dùng" },
            new Permission { Id = 4, Code = PermissionCodes.RoleManage, Name = "Quản lý phân quyền" },
            new Permission { Id = 5, Code = PermissionCodes.StoreView, Name = "Xem danh sách cửa hàng" },
            new Permission { Id = 6, Code = PermissionCodes.StoreManage, Name = "Quản lý cửa hàng" },

            new Permission { Id = 7, Code = PermissionCodes.PlanningInputView, Name = "Xem tab Nhập dữ liệu & Cấu hình" },
            new Permission { Id = 8, Code = PermissionCodes.PlanningOverviewView, Name = "Xem tab Tổng quan" },
            new Permission { Id = 9, Code = PermissionCodes.PlanningAnalysisView, Name = "Xem tab Phân tích & Weekly roster" },
            new Permission { Id = 10, Code = PermissionCodes.DashboardView, Name = "Xem Dashboard" },
            new Permission { Id = 11, Code = PermissionCodes.ZonePlanningView, Name = "Xem Zone Planning" },
            new Permission { Id = 12, Code = PermissionCodes.AmOmManage, Name = "Quản lý Mapping AM → OM" }
        );

        modelBuilder.Entity<Role>().HasData(
            new Role { Id = 1, Name = "Administrator", Description = "Toàn quyền hệ thống", IsSystem = true },
            new Role { Id = 2, Name = "Manager", Description = "Publish và xem dữ liệu", IsSystem = true },
            new Role { Id = 3, Name = "Staff", Description = "Xem dữ liệu đã publish", IsSystem = true },
            new Role { Id = 4, Name = "Viewer", Description = "Chỉ xem dữ liệu đã publish", IsSystem = true }
        );

        // Administrator: all permissions
        var adminPerms = new[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
        // Manager: planning workflow + publish + published + store view
        // (does NOT include Dashboard/ZonePlanning by default)
        var managerPerms = new[] { 1, 2, 5, 7, 8, 9 };
        // Staff: published + store view (no planning workflow, no dashboard/zone)
        var staffPerms = new[] { 1, 5 };
        // Viewer: published only
        var viewerPerms = new[] { 1 };

        var rolePerms = new List<RolePermission>();
        void Add(int roleId, IEnumerable<int> permIds)
        {
            foreach (var p in permIds)
                rolePerms.Add(new RolePermission { RoleId = roleId, PermissionId = p });
        }
        Add(1, adminPerms);
        Add(2, managerPerms);
        Add(3, staffPerms);
        Add(4, viewerPerms);
        modelBuilder.Entity<RolePermission>().HasData(rolePerms);
    }
}
