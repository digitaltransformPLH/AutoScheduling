-- 007_dim_store_detail_schema.sql: shift columns + relax Region check for PLH import
USE WorkforcePlanning;
GO

IF OBJECT_ID(N'dbo.dim_store_detail', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_store_detail (
        StoreCode NVARCHAR(10) NOT NULL CONSTRAINT PK_dim_store_detail PRIMARY KEY,
        StoreName NVARCHAR(200) NOT NULL,
        Concept NVARCHAR(50) NULL,
        City NVARCHAR(100) NULL,
        AreaManager NVARCHAR(200) NOT NULL CONSTRAINT DF_dim_store_detail_AreaManager DEFAULT(N''),
        OperationManager NVARCHAR(200) NOT NULL CONSTRAINT DF_dim_store_detail_OperationManager DEFAULT(N''),
        Region NVARCHAR(1) NOT NULL CONSTRAINT DF_dim_store_detail_Region DEFAULT(N''),
        OpenTime NVARCHAR(50) NULL,
        CloseTime NVARCHAR(50) NULL,
        OpenShift NVARCHAR(50) NULL,
        CloseShift NVARCHAR(50) NULL,
        SM NVARCHAR(200) NULL,
        CONSTRAINT CK_dim_store_detail_Region CHECK (Region IN (N'', N'H', N'T', N'W'))
    );
    CREATE INDEX IX_dim_store_detail_AreaManager ON dbo.dim_store_detail(AreaManager);
    CREATE INDEX IX_dim_store_detail_OperationManager ON dbo.dim_store_detail(OperationManager);
    CREATE INDEX IX_dim_store_detail_Region ON dbo.dim_store_detail(Region);
END
ELSE
BEGIN
    IF COL_LENGTH('dbo.dim_store_detail', N'OpenTime') IS NULL ALTER TABLE dbo.dim_store_detail ADD OpenTime NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.dim_store_detail', N'CloseTime') IS NULL ALTER TABLE dbo.dim_store_detail ADD CloseTime NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.dim_store_detail', N'OpenShift') IS NULL ALTER TABLE dbo.dim_store_detail ADD OpenShift NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.dim_store_detail', N'CloseShift') IS NULL ALTER TABLE dbo.dim_store_detail ADD CloseShift NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.dim_store_detail', N'SM') IS NULL ALTER TABLE dbo.dim_store_detail ADD SM NVARCHAR(200) NULL;

    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_dim_store_detail_Region' AND parent_object_id = OBJECT_ID(N'dbo.dim_store_detail'))
        ALTER TABLE dbo.dim_store_detail DROP CONSTRAINT CK_dim_store_detail_Region;

    ALTER TABLE dbo.dim_store_detail ADD CONSTRAINT CK_dim_store_detail_Region
        CHECK (Region IN (N'', N'H', N'T', N'W'));
END
GO

PRINT 'dim_store_detail schema ready.';
GO