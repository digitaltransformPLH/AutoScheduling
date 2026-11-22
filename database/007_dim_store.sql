-- 007_dim_store.sql: CloseDate + rename dbo.Stores -> dbo.dim_store
USE WorkforcePlanning;
GO

DECLARE @table sysname;
IF OBJECT_ID(N'dbo.dim_store', N'U') IS NOT NULL
    SET @table = N'dim_store';
ELSE IF OBJECT_ID(N'dbo.Stores', N'U') IS NOT NULL
    SET @table = N'Stores';
ELSE
BEGIN
    RAISERROR(N'Neither dbo.Stores nor dbo.dim_store exists.', 16, 1);
    RETURN;
END

IF COL_LENGTH(@table, N'CloseDate') IS NULL
BEGIN
  DECLARE @sql nvarchar(500) = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' ADD CloseDate DATE NULL;';
  EXEC sp_executesql @sql;
END
GO

IF OBJECT_ID(N'dbo.Stores', N'U') IS NOT NULL AND OBJECT_ID(N'dbo.dim_store', N'U') IS NULL
BEGIN
    EXEC sp_rename N'dbo.Stores', N'dim_store', N'OBJECT';

    IF OBJECT_ID(N'dbo.PK_Stores', N'PK') IS NOT NULL
        EXEC sp_rename N'dbo.PK_Stores', N'PK_dim_store', N'OBJECT';

    IF OBJECT_ID(N'dbo.DF_Stores_IsActive', N'D') IS NOT NULL
        EXEC sp_rename N'dbo.DF_Stores_IsActive', N'DF_dim_store_IsActive', N'OBJECT';

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Stores_Code' AND object_id = OBJECT_ID(N'dbo.dim_store'))
        EXEC sp_rename N'dbo.dim_store.IX_Stores_Code', N'IX_dim_store_Code', N'INDEX';

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Stores_AreaManagerId' AND object_id = OBJECT_ID(N'dbo.dim_store'))
        EXEC sp_rename N'dbo.dim_store.IX_Stores_AreaManagerId', N'IX_dim_store_AreaManagerId', N'INDEX';

    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Stores_Persons_AreaManagerId')
        EXEC sp_rename N'dbo.FK_Stores_Persons_AreaManagerId', N'FK_dim_store_Persons_AreaManagerId', N'OBJECT';

    -- Legacy FK from UserStoreRoles (if present)
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_UserStoreRoles_Stores_StoreId')
        EXEC sp_rename N'dbo.FK_UserStoreRoles_Stores_StoreId', N'FK_UserStoreRoles_dim_store_StoreId', N'OBJECT';

    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_UserStores_Stores_StoreId')
        EXEC sp_rename N'dbo.FK_UserStores_Stores_StoreId', N'FK_UserStores_dim_store_StoreId', N'OBJECT';
END
GO

PRINT 'dim_store schema ready. Run 007_dim_store_seed.sql after 007_dim_store_detail_schema.sql.';
GO