-- WorkforcePlanning phase-1 schema (mirrors EF migration InitialCreate)
-- Run against SQL Server if not using `dotnet ef database update`.

IF DB_ID(N'WorkforcePlanning') IS NULL
    CREATE DATABASE WorkforcePlanning;
GO

USE WorkforcePlanning;
GO

IF OBJECT_ID(N'dbo.Stores', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Stores (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Stores PRIMARY KEY,
        Code NVARCHAR(10) NOT NULL,
        Name NVARCHAR(200) NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_Stores_IsActive DEFAULT(1)
    );
    CREATE UNIQUE INDEX IX_Stores_Code ON dbo.Stores(Code);
END
GO

IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Users PRIMARY KEY,
        WindowsUserName NVARCHAR(256) NOT NULL,
        DisplayName NVARCHAR(200) NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_Users_IsActive DEFAULT(1)
    );
    CREATE UNIQUE INDEX IX_Users_WindowsUserName ON dbo.Users(WindowsUserName);
END
GO

IF OBJECT_ID(N'dbo.UserStoreRoles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserStoreRoles (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserStoreRoles PRIMARY KEY,
        UserId INT NOT NULL,
        StoreId INT NOT NULL,
        Role NVARCHAR(32) NOT NULL,
        CONSTRAINT FK_UserStoreRoles_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
        CONSTRAINT FK_UserStoreRoles_Stores FOREIGN KEY (StoreId) REFERENCES dbo.Stores(Id)
    );
    CREATE UNIQUE INDEX IX_UserStoreRoles_UserId_StoreId ON dbo.UserStoreRoles(UserId, StoreId);
END
GO

IF OBJECT_ID(N'dbo.DailyPlanningMetrics', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DailyPlanningMetrics (
        Id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DailyPlanningMetrics PRIMARY KEY,
        StoreCode NVARCHAR(10) NOT NULL,
        StoreName NVARCHAR(200) NULL,
        AreaManager NVARCHAR(200) NULL,
        OperationManager NVARCHAR(200) NULL,
        [Date] DATE NOT NULL,
        [Day] NVARCHAR(20) NOT NULL,
        [Month] INT NOT NULL,
        [Year] INT NOT NULL,
        ADTC DECIMAL(18,4) NULL,
        LaborReg DECIMAL(18,2) NULL,
        LaborTrain DECIMAL(18,2) NULL,
        LaborNSO DECIMAL(18,2) NULL,
        TCPH DECIMAL(18,4) NULL,
        TcphNSO DECIMAL(18,4) NULL,
        PublishId NVARCHAR(64) NOT NULL,
        PublishVersion INT NOT NULL,
        PublishedAt DATETIMEOFFSET NOT NULL,
        PublishedBy NVARCHAR(256) NOT NULL
    );
    CREATE UNIQUE INDEX IX_DailyPlanningMetrics_StoreCode_Date_PublishVersion
        ON dbo.DailyPlanningMetrics(StoreCode, [Date], PublishVersion);
    CREATE INDEX IX_DailyPlanningMetrics_StoreCode_Date
        ON dbo.DailyPlanningMetrics(StoreCode, [Date]);
    CREATE INDEX IX_DailyPlanningMetrics_PublishId
        ON dbo.DailyPlanningMetrics(PublishId);
END
GO

-- Seed sample stores (idempotent)
IF NOT EXISTS (SELECT 1 FROM dbo.Stores WHERE Code = N'2026')
    INSERT INTO dbo.Stores (Code, Name, IsActive)
    VALUES (N'2026', N'HCM-CH Đường số 7 P.Bình Trị Đông', 1);

IF NOT EXISTS (SELECT 1 FROM dbo.Stores WHERE Code = N'0001')
    INSERT INTO dbo.Stores (Code, Name, IsActive)
    VALUES (N'0001', N'Sample Store 0001', 1);
GO

-- Seed current planner (REPLACE DOMAIN\user before UAT)
DECLARE @WinUser NVARCHAR(256) = N'DOMAIN\uat.planner';
DECLARE @UserId INT;

IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE WindowsUserName = @WinUser)
    INSERT INTO dbo.Users (WindowsUserName, DisplayName, IsActive)
    VALUES (@WinUser, N'UAT Planner', 1);

SELECT @UserId = Id FROM dbo.Users WHERE WindowsUserName = @WinUser;

INSERT INTO dbo.UserStoreRoles (UserId, StoreId, Role)
SELECT @UserId, s.Id, N'StoreAdmin'
FROM dbo.Stores s
WHERE s.IsActive = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.UserStoreRoles r
      WHERE r.UserId = @UserId AND r.StoreId = s.Id
  );
GO
