-- 006_store_org_management.sql
-- Schema: Person, AmOmAssignment, extended Stores + Store.Manage permission
USE WorkforcePlanning;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Permissions WHERE Code = N'Action.Store.Manage')
    INSERT INTO dbo.Permissions (Id, Code, Name) VALUES (6, N'Action.Store.Manage', N'Quản lý cửa hàng');

IF NOT EXISTS (SELECT 1 FROM dbo.RolePermissions WHERE RoleId = 1 AND PermissionId = 6)
    INSERT INTO dbo.RolePermissions (RoleId, PermissionId) VALUES (1, 6);
GO

IF OBJECT_ID(N'dbo.Persons', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Persons (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Persons PRIMARY KEY,
        FullName NVARCHAR(200) NOT NULL,
        Email NVARCHAR(256) NULL,
        Phone NVARCHAR(50) NULL,
        Role NVARCHAR(10) NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_Persons_IsActive DEFAULT(1)
    );
    CREATE INDEX IX_Persons_Role ON dbo.Persons(Role);
    CREATE INDEX IX_Persons_FullName ON dbo.Persons(FullName);
END
GO

IF OBJECT_ID(N'dbo.AmOmAssignments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.AmOmAssignments (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_AmOmAssignments PRIMARY KEY,
        AreaManagerId INT NOT NULL,
        OperationManagerId INT NOT NULL,
        EffectiveFrom DATE NOT NULL,
        EffectiveTo DATE NULL,
        CONSTRAINT FK_AmOmAssignments_AM FOREIGN KEY (AreaManagerId) REFERENCES dbo.Persons(Id),
        CONSTRAINT FK_AmOmAssignments_OM FOREIGN KEY (OperationManagerId) REFERENCES dbo.Persons(Id)
    );
    CREATE INDEX IX_AmOmAssignments_AM_EffectiveTo ON dbo.AmOmAssignments(AreaManagerId, EffectiveTo);
    CREATE INDEX IX_AmOmAssignments_OM ON dbo.AmOmAssignments(OperationManagerId);
END
GO

IF COL_LENGTH('dbo.Stores', 'City') IS NULL ALTER TABLE dbo.Stores ADD City NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.Stores', 'Concept') IS NULL ALTER TABLE dbo.Stores ADD Concept NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.Stores', 'OpenDate') IS NULL ALTER TABLE dbo.Stores ADD OpenDate DATE NULL;
IF COL_LENGTH('dbo.Stores', 'Email') IS NULL ALTER TABLE dbo.Stores ADD Email NVARCHAR(256) NULL;
IF COL_LENGTH('dbo.Stores', 'AreaManagerId') IS NULL ALTER TABLE dbo.Stores ADD AreaManagerId INT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Stores_Persons_AreaManagerId')
    ALTER TABLE dbo.Stores ADD CONSTRAINT FK_Stores_Persons_AreaManagerId
        FOREIGN KEY (AreaManagerId) REFERENCES dbo.Persons(Id) ON DELETE SET NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Stores_AreaManagerId' AND object_id = OBJECT_ID(N'dbo.Stores'))
    CREATE INDEX IX_Stores_AreaManagerId ON dbo.Stores(AreaManagerId);
GO

PRINT 'Store org schema ready. Run 006_store_org_seed.sql to import data.';
GO
