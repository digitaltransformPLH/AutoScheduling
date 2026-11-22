using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace WorkforcePlanning.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class RenameStoresToDimStoreAndShiftColumns : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Stores_Persons_AreaManagerId",
                table: "Stores");

            migrationBuilder.DropForeignKey(
                name: "FK_UserStores_Stores_StoreId",
                table: "UserStores");

            migrationBuilder.DropPrimaryKey(
                name: "PK_Stores",
                table: "Stores");

            migrationBuilder.RenameTable(
                name: "Stores",
                newName: "dim_store");

            migrationBuilder.RenameIndex(
                name: "IX_Stores_Code",
                table: "dim_store",
                newName: "IX_dim_store_Code");

            migrationBuilder.RenameIndex(
                name: "IX_Stores_AreaManagerId",
                table: "dim_store",
                newName: "IX_dim_store_AreaManagerId");

            migrationBuilder.AddColumn<string>(
                name: "CloseShift",
                table: "dim_store_detail",
                type: "nvarchar(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "CloseTime",
                table: "dim_store_detail",
                type: "nvarchar(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "OpenShift",
                table: "dim_store_detail",
                type: "nvarchar(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "OpenTime",
                table: "dim_store_detail",
                type: "nvarchar(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "SM",
                table: "dim_store_detail",
                type: "nvarchar(200)",
                maxLength: 200,
                nullable: true);

            migrationBuilder.AddColumn<DateOnly>(
                name: "CloseDate",
                table: "dim_store",
                type: "date",
                nullable: true);

            migrationBuilder.AddPrimaryKey(
                name: "PK_dim_store",
                table: "dim_store",
                column: "Id");

            migrationBuilder.UpdateData(
                table: "dim_store",
                keyColumn: "Id",
                keyValue: 1,
                column: "CloseDate",
                value: null);

            migrationBuilder.UpdateData(
                table: "dim_store",
                keyColumn: "Id",
                keyValue: 2,
                column: "CloseDate",
                value: null);

            migrationBuilder.AddForeignKey(
                name: "FK_dim_store_Persons_AreaManagerId",
                table: "dim_store",
                column: "AreaManagerId",
                principalTable: "Persons",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);

            migrationBuilder.AddForeignKey(
                name: "FK_UserStores_dim_store_StoreId",
                table: "UserStores",
                column: "StoreId",
                principalTable: "dim_store",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_dim_store_Persons_AreaManagerId",
                table: "dim_store");

            migrationBuilder.DropForeignKey(
                name: "FK_UserStores_dim_store_StoreId",
                table: "UserStores");

            migrationBuilder.DropPrimaryKey(
                name: "PK_dim_store",
                table: "dim_store");

            migrationBuilder.DropColumn(
                name: "CloseShift",
                table: "dim_store_detail");

            migrationBuilder.DropColumn(
                name: "CloseTime",
                table: "dim_store_detail");

            migrationBuilder.DropColumn(
                name: "OpenShift",
                table: "dim_store_detail");

            migrationBuilder.DropColumn(
                name: "OpenTime",
                table: "dim_store_detail");

            migrationBuilder.DropColumn(
                name: "SM",
                table: "dim_store_detail");

            migrationBuilder.DropColumn(
                name: "CloseDate",
                table: "dim_store");

            migrationBuilder.RenameTable(
                name: "dim_store",
                newName: "Stores");

            migrationBuilder.RenameIndex(
                name: "IX_dim_store_Code",
                table: "Stores",
                newName: "IX_Stores_Code");

            migrationBuilder.RenameIndex(
                name: "IX_dim_store_AreaManagerId",
                table: "Stores",
                newName: "IX_Stores_AreaManagerId");

            migrationBuilder.AddPrimaryKey(
                name: "PK_Stores",
                table: "Stores",
                column: "Id");

            migrationBuilder.AddForeignKey(
                name: "FK_Stores_Persons_AreaManagerId",
                table: "Stores",
                column: "AreaManagerId",
                principalTable: "Persons",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);

            migrationBuilder.AddForeignKey(
                name: "FK_UserStores_Stores_StoreId",
                table: "UserStores",
                column: "StoreId",
                principalTable: "Stores",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
