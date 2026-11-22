using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddEmployeeSecondment : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "employee_secondment",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    EmployeeId = table.Column<int>(type: "int", nullable: false),
                    HomePlantCode = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    ReceivingStoreCode = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    StartDate = table.Column<DateOnly>(type: "date", nullable: false),
                    EndDate = table.Column<DateOnly>(type: "date", nullable: false),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    UpdatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    UpdatedBy = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_employee_secondment", x => x.Id);
                    table.ForeignKey(
                        name: "FK_employee_secondment_dim_employee_EmployeeId",
                        column: x => x.EmployeeId,
                        principalTable: "dim_employee",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_employee_secondment_dim_store_ReceivingStoreCode",
                        column: x => x.ReceivingStoreCode,
                        principalTable: "dim_store",
                        principalColumn: "Code",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_employee_secondment_EmployeeId_StartDate_EndDate",
                table: "employee_secondment",
                columns: new[] { "EmployeeId", "StartDate", "EndDate" });

            migrationBuilder.CreateIndex(
                name: "IX_employee_secondment_ReceivingStoreCode",
                table: "employee_secondment",
                column: "ReceivingStoreCode");

            migrationBuilder.CreateIndex(
                name: "IX_employee_secondment_Status",
                table: "employee_secondment",
                column: "Status");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "employee_secondment");
        }
    }
}
