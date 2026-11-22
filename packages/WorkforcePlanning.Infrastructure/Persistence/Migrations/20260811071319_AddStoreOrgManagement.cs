using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddStoreOrgManagement : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "AreaManagerId",
                table: "Stores",
                type: "int",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "City",
                table: "Stores",
                type: "nvarchar(100)",
                maxLength: 100,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Concept",
                table: "Stores",
                type: "nvarchar(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Email",
                table: "Stores",
                type: "nvarchar(256)",
                maxLength: 256,
                nullable: true);

            migrationBuilder.AddColumn<DateOnly>(
                name: "OpenDate",
                table: "Stores",
                type: "date",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "Persons",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    FullName = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    Email = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: true),
                    Phone = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    Role = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    IsActive = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Persons", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "AmOmAssignments",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AreaManagerId = table.Column<int>(type: "int", nullable: false),
                    OperationManagerId = table.Column<int>(type: "int", nullable: false),
                    EffectiveFrom = table.Column<DateOnly>(type: "date", nullable: false),
                    EffectiveTo = table.Column<DateOnly>(type: "date", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AmOmAssignments", x => x.Id);
                    table.ForeignKey(
                        name: "FK_AmOmAssignments_Persons_AreaManagerId",
                        column: x => x.AreaManagerId,
                        principalTable: "Persons",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_AmOmAssignments_Persons_OperationManagerId",
                        column: x => x.OperationManagerId,
                        principalTable: "Persons",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Permissions",
                columns: new[] { "Id", "Code", "Name" },
                values: new object[] { 6, "Action.Store.Manage", "Quản lý cửa hàng" });

            migrationBuilder.UpdateData(
                table: "Stores",
                keyColumn: "Id",
                keyValue: 1,
                columns: new[] { "AreaManagerId", "City", "Concept", "Email", "OpenDate" },
                values: new object[] { null, null, null, null, null });

            migrationBuilder.UpdateData(
                table: "Stores",
                keyColumn: "Id",
                keyValue: 2,
                columns: new[] { "AreaManagerId", "City", "Concept", "Email", "OpenDate" },
                values: new object[] { null, null, null, null, null });

            migrationBuilder.InsertData(
                table: "RolePermissions",
                columns: new[] { "PermissionId", "RoleId" },
                values: new object[] { 6, 1 });

            migrationBuilder.CreateIndex(
                name: "IX_Stores_AreaManagerId",
                table: "Stores",
                column: "AreaManagerId");

            migrationBuilder.CreateIndex(
                name: "IX_AmOmAssignments_AreaManagerId_EffectiveTo",
                table: "AmOmAssignments",
                columns: new[] { "AreaManagerId", "EffectiveTo" });

            migrationBuilder.CreateIndex(
                name: "IX_AmOmAssignments_OperationManagerId",
                table: "AmOmAssignments",
                column: "OperationManagerId");

            migrationBuilder.CreateIndex(
                name: "IX_Persons_FullName",
                table: "Persons",
                column: "FullName");

            migrationBuilder.CreateIndex(
                name: "IX_Persons_Role",
                table: "Persons",
                column: "Role");

            migrationBuilder.AddForeignKey(
                name: "FK_Stores_Persons_AreaManagerId",
                table: "Stores",
                column: "AreaManagerId",
                principalTable: "Persons",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Stores_Persons_AreaManagerId",
                table: "Stores");

            migrationBuilder.DropTable(
                name: "AmOmAssignments");

            migrationBuilder.DropTable(
                name: "Persons");

            migrationBuilder.DropIndex(
                name: "IX_Stores_AreaManagerId",
                table: "Stores");

            migrationBuilder.DeleteData(
                table: "RolePermissions",
                keyColumns: new[] { "PermissionId", "RoleId" },
                keyValues: new object[] { 6, 1 });

            migrationBuilder.DeleteData(
                table: "Permissions",
                keyColumn: "Id",
                keyValue: 6);

            migrationBuilder.DropColumn(
                name: "AreaManagerId",
                table: "Stores");

            migrationBuilder.DropColumn(
                name: "City",
                table: "Stores");

            migrationBuilder.DropColumn(
                name: "Concept",
                table: "Stores");

            migrationBuilder.DropColumn(
                name: "Email",
                table: "Stores");

            migrationBuilder.DropColumn(
                name: "OpenDate",
                table: "Stores");
        }
    }
}
