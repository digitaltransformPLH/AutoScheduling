using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddEmployeeAvailabilitySlot : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "employee_availability_slot",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    PlantCode = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    EmployeeNumber = table.Column<long>(type: "bigint", nullable: false),
                    EmployeeId = table.Column<int>(type: "int", nullable: true),
                    WeekStartMonday = table.Column<DateOnly>(type: "date", nullable: false),
                    WorkDate = table.Column<DateOnly>(type: "date", nullable: false),
                    BusyFrom = table.Column<TimeOnly>(type: "time", nullable: true),
                    BusyTo = table.Column<TimeOnly>(type: "time", nullable: true),
                    IsPaidLeave = table.Column<bool>(type: "bit", nullable: false),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    UpdatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_employee_availability_slot", x => x.Id);
                    table.ForeignKey(
                        name: "FK_employee_availability_slot_dim_employee_EmployeeId",
                        column: x => x.EmployeeId,
                        principalTable: "dim_employee",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_employee_availability_slot_dim_store_PlantCode",
                        column: x => x.PlantCode,
                        principalTable: "dim_store",
                        principalColumn: "Code",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Permissions",
                columns: new[] { "Id", "Code", "Name" },
                values: new object[,]
                {
                    { 15, "Action.EmployeeAvailability.View", "Xem lịch bận nhân viên" },
                    { 16, "Action.EmployeeAvailability.Manage", "Quản lý lịch bận nhân viên" }
                });

            migrationBuilder.InsertData(
                table: "RolePermissions",
                columns: new[] { "PermissionId", "RoleId" },
                values: new object[,]
                {
                    { 15, 1 },
                    { 16, 1 },
                    { 15, 2 },
                    { 16, 2 }
                });

            migrationBuilder.CreateIndex(
                name: "IX_employee_availability_slot_EmployeeId",
                table: "employee_availability_slot",
                column: "EmployeeId");

            migrationBuilder.CreateIndex(
                name: "IX_employee_availability_slot_PlantCode_EmployeeNumber_WorkDate",
                table: "employee_availability_slot",
                columns: new[] { "PlantCode", "EmployeeNumber", "WorkDate" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_employee_availability_slot_PlantCode_WeekStartMonday",
                table: "employee_availability_slot",
                columns: new[] { "PlantCode", "WeekStartMonday" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "employee_availability_slot");

            migrationBuilder.DeleteData(
                table: "RolePermissions",
                keyColumns: new[] { "PermissionId", "RoleId" },
                keyValues: new object[] { 15, 1 });

            migrationBuilder.DeleteData(
                table: "RolePermissions",
                keyColumns: new[] { "PermissionId", "RoleId" },
                keyValues: new object[] { 16, 1 });

            migrationBuilder.DeleteData(
                table: "RolePermissions",
                keyColumns: new[] { "PermissionId", "RoleId" },
                keyValues: new object[] { 15, 2 });

            migrationBuilder.DeleteData(
                table: "RolePermissions",
                keyColumns: new[] { "PermissionId", "RoleId" },
                keyValues: new object[] { 16, 2 });

            migrationBuilder.DeleteData(
                table: "Permissions",
                keyColumn: "Id",
                keyValue: 15);

            migrationBuilder.DeleteData(
                table: "Permissions",
                keyColumn: "Id",
                keyValue: 16);
        }
    }
}
