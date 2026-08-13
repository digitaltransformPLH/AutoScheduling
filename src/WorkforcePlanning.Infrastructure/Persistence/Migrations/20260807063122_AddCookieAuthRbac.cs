using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddCookieAuthRbac : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                IF OBJECT_ID(N'dbo.UserStoreRoles', N'U') IS NOT NULL
                    DROP TABLE dbo.UserStoreRoles;

                DELETE FROM dbo.Users;

                IF COL_LENGTH('dbo.Users', 'WindowsUserName') IS NOT NULL
                BEGIN
                    EXEC sp_rename N'dbo.Users.WindowsUserName', N'Email', N'COLUMN';
                END

                IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Users_WindowsUserName' AND object_id = OBJECT_ID(N'dbo.Users'))
                    EXEC sp_rename N'dbo.Users.IX_Users_WindowsUserName', N'IX_Users_Email', N'INDEX';

                IF COL_LENGTH('dbo.Users', 'AllStores') IS NULL
                    ALTER TABLE dbo.Users ADD AllStores bit NOT NULL CONSTRAINT DF_Users_AllStores DEFAULT(0);

                IF COL_LENGTH('dbo.Users', 'PasswordHash') IS NULL
                    ALTER TABLE dbo.Users ADD PasswordHash nvarchar(500) NOT NULL CONSTRAINT DF_Users_PasswordHash DEFAULT(N'');

                IF COL_LENGTH('dbo.Users', 'RoleId') IS NULL
                    ALTER TABLE dbo.Users ADD RoleId int NOT NULL CONSTRAINT DF_Users_RoleId DEFAULT(0);
                """);

            migrationBuilder.CreateTable(
                name: "Permissions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Code = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    Name = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Permissions", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Roles",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Name = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    Description = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    IsSystem = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Roles", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "UserStores",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    UserId = table.Column<int>(type: "int", nullable: false),
                    StoreId = table.Column<int>(type: "int", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UserStores", x => x.Id);
                    table.ForeignKey(
                        name: "FK_UserStores_Stores_StoreId",
                        column: x => x.StoreId,
                        principalTable: "Stores",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UserStores_Users_UserId",
                        column: x => x.UserId,
                        principalTable: "Users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "RolePermissions",
                columns: table => new
                {
                    RoleId = table.Column<int>(type: "int", nullable: false),
                    PermissionId = table.Column<int>(type: "int", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_RolePermissions", x => new { x.RoleId, x.PermissionId });
                    table.ForeignKey(
                        name: "FK_RolePermissions_Permissions_PermissionId",
                        column: x => x.PermissionId,
                        principalTable: "Permissions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_RolePermissions_Roles_RoleId",
                        column: x => x.RoleId,
                        principalTable: "Roles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                table: "Permissions",
                columns: new[] { "Id", "Code", "Name" },
                values: new object[,]
                {
                    { 1, "Action.Published.View", "Xem dữ liệu đã publish" },
                    { 2, "Action.Publish.Schedule", "Publish schedule" },
                    { 3, "Action.User.Manage", "Quản lý người dùng" },
                    { 4, "Action.Role.Manage", "Quản lý phân quyền" },
                    { 5, "Action.Store.View", "Xem danh sách cửa hàng" }
                });

            migrationBuilder.InsertData(
                table: "Roles",
                columns: new[] { "Id", "Description", "IsSystem", "Name" },
                values: new object[,]
                {
                    { 1, "Toàn quyền hệ thống", true, "Administrator" },
                    { 2, "Publish và xem dữ liệu", true, "Manager" },
                    { 3, "Xem dữ liệu đã publish", true, "Staff" },
                    { 4, "Chỉ xem dữ liệu đã publish", true, "Viewer" }
                });

            migrationBuilder.InsertData(
                table: "RolePermissions",
                columns: new[] { "PermissionId", "RoleId" },
                values: new object[,]
                {
                    { 1, 1 },
                    { 2, 1 },
                    { 3, 1 },
                    { 4, 1 },
                    { 5, 1 },
                    { 1, 2 },
                    { 2, 2 },
                    { 5, 2 },
                    { 1, 3 },
                    { 5, 3 },
                    { 1, 4 }
                });

            migrationBuilder.Sql("""
                IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Users_RoleId' AND object_id = OBJECT_ID(N'dbo.Users'))
                    CREATE INDEX IX_Users_RoleId ON dbo.Users(RoleId);

                IF OBJECT_ID(N'dbo.FK_Users_Roles_RoleId', N'F') IS NULL
                    ALTER TABLE dbo.Users WITH CHECK
                    ADD CONSTRAINT FK_Users_Roles_RoleId FOREIGN KEY (RoleId) REFERENCES dbo.Roles(Id) ON DELETE CASCADE;
                """);

            migrationBuilder.CreateIndex(
                name: "IX_Permissions_Code",
                table: "Permissions",
                column: "Code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_RolePermissions_PermissionId",
                table: "RolePermissions",
                column: "PermissionId");

            migrationBuilder.CreateIndex(
                name: "IX_Roles_Name",
                table: "Roles",
                column: "Name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_UserStores_StoreId",
                table: "UserStores",
                column: "StoreId");

            migrationBuilder.CreateIndex(
                name: "IX_UserStores_UserId_StoreId",
                table: "UserStores",
                columns: new[] { "UserId", "StoreId" },
                unique: true);

            // IDENTITY insert for seeded Roles/Permissions requires reseeding
            migrationBuilder.Sql("""
                DBCC CHECKIDENT ('dbo.Permissions', RESEED, 5);
                DBCC CHECKIDENT ('dbo.Roles', RESEED, 4);
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                IF OBJECT_ID(N'dbo.FK_Users_Roles_RoleId', N'F') IS NOT NULL
                    ALTER TABLE dbo.Users DROP CONSTRAINT FK_Users_Roles_RoleId;
                """);

            migrationBuilder.DropTable(name: "RolePermissions");
            migrationBuilder.DropTable(name: "UserStores");
            migrationBuilder.DropTable(name: "Permissions");
            migrationBuilder.DropTable(name: "Roles");

            migrationBuilder.Sql("""
                IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Users_RoleId' AND object_id = OBJECT_ID(N'dbo.Users'))
                    DROP INDEX IX_Users_RoleId ON dbo.Users;
                IF COL_LENGTH('dbo.Users', 'AllStores') IS NOT NULL
                    ALTER TABLE dbo.Users DROP CONSTRAINT DF_Users_AllStores;
                IF COL_LENGTH('dbo.Users', 'AllStores') IS NOT NULL
                    ALTER TABLE dbo.Users DROP COLUMN AllStores;
                IF COL_LENGTH('dbo.Users', 'PasswordHash') IS NOT NULL
                    ALTER TABLE dbo.Users DROP CONSTRAINT DF_Users_PasswordHash;
                IF COL_LENGTH('dbo.Users', 'PasswordHash') IS NOT NULL
                    ALTER TABLE dbo.Users DROP COLUMN PasswordHash;
                IF COL_LENGTH('dbo.Users', 'RoleId') IS NOT NULL
                    ALTER TABLE dbo.Users DROP CONSTRAINT DF_Users_RoleId;
                IF COL_LENGTH('dbo.Users', 'RoleId') IS NOT NULL
                    ALTER TABLE dbo.Users DROP COLUMN RoleId;
                IF COL_LENGTH('dbo.Users', 'Email') IS NOT NULL
                    EXEC sp_rename N'dbo.Users.Email', N'WindowsUserName', N'COLUMN';
                """);
        }
    }
}
