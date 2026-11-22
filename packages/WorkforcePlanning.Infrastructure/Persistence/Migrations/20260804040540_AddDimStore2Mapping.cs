using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddDimStore2Mapping : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "dim_store_detail",
                columns: table => new
                {
                    StoreCode = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    StoreName = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    Concept = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    City = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    AreaManager = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    OperationManager = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    Region = table.Column<string>(type: "nvarchar(1)", maxLength: 1, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_dim_store_detail", x => x.StoreCode);
                });

            migrationBuilder.CreateIndex(
                name: "IX_dim_store_detail_AreaManager",
                table: "dim_store_detail",
                column: "AreaManager");

            migrationBuilder.CreateIndex(
                name: "IX_dim_store_detail_OperationManager",
                table: "dim_store_detail",
                column: "OperationManager");

            migrationBuilder.CreateIndex(
                name: "IX_dim_store_detail_Region",
                table: "dim_store_detail",
                column: "Region");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "dim_store_detail");
        }
    }
}
