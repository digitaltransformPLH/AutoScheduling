-- Cookie auth + RBAC schema (mirrors EF migration AddCookieAuthRbac)
USE WorkforcePlanning;
GO

IF OBJECT_ID(N'dbo.UserStoreRoles', N'U') IS NOT NULL
    DROP TABLE dbo.UserStoreRoles;
GO

DELETE FROM dbo.Users;
GO

IF COL_LENGTH('dbo.Users', 'WindowsUserName') IS NOT NULL
    EXEC sp_rename N'dbo.Users.WindowsUserName', N'Email', N'COLUMN';
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Users_WindowsUserName' AND object_id = OBJECT_ID(N'dbo.Users'))
    EXEC sp_rename N'dbo.Users.IX_Users_WindowsUserName', N'IX_Users_Email', N'INDEX';
GO

IF COL_LENGTH('dbo.Users', 'AllStores') IS NULL
    ALTER TABLE dbo.Users ADD AllStores bit NOT NULL CONSTRAINT DF_Users_AllStores DEFAULT(0);
IF COL_LENGTH('dbo.Users', 'PasswordHash') IS NULL
    ALTER TABLE dbo.Users ADD PasswordHash nvarchar(500) NOT NULL CONSTRAINT DF_Users_PasswordHash DEFAULT(N'');
IF COL_LENGTH('dbo.Users', 'RoleId') IS NULL
    ALTER TABLE dbo.Users ADD RoleId int NOT NULL CONSTRAINT DF_Users_RoleId DEFAULT(0);
GO

IF OBJECT_ID(N'dbo.Permissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Permissions (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Permissions PRIMARY KEY,
        Code NVARCHAR(100) NOT NULL,
        Name NVARCHAR(200) NOT NULL
    );
    CREATE UNIQUE INDEX IX_Permissions_Code ON dbo.Permissions(Code);
END
GO

IF OBJECT_ID(N'dbo.Roles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Roles (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Roles PRIMARY KEY,
        Name NVARCHAR(100) NOT NULL,
        Description NVARCHAR(500) NULL,
        IsSystem BIT NOT NULL
    );
    CREATE UNIQUE INDEX IX_Roles_Name ON dbo.Roles(Name);
END
GO

IF OBJECT_ID(N'dbo.RolePermissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RolePermissions (
        RoleId INT NOT NULL,
        PermissionId INT NOT NULL,
        CONSTRAINT PK_RolePermissions PRIMARY KEY (RoleId, PermissionId),
        CONSTRAINT FK_RolePermissions_Roles FOREIGN KEY (RoleId) REFERENCES dbo.Roles(Id) ON DELETE CASCADE,
        CONSTRAINT FK_RolePermissions_Permissions FOREIGN KEY (PermissionId) REFERENCES dbo.Permissions(Id) ON DELETE CASCADE
    );
END
GO

IF OBJECT_ID(N'dbo.UserStores', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserStores (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserStores PRIMARY KEY,
        UserId INT NOT NULL,
        StoreId INT NOT NULL,
        CONSTRAINT FK_UserStores_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
        CONSTRAINT FK_UserStores_Stores FOREIGN KEY (StoreId) REFERENCES dbo.Stores(Id) ON DELETE CASCADE
    );
    CREATE UNIQUE INDEX IX_UserStores_UserId_StoreId ON dbo.UserStores(UserId, StoreId);
END
GO

SET IDENTITY_INSERT dbo.Permissions ON;
IF NOT EXISTS (SELECT 1 FROM dbo.Permissions WHERE Id=1)
INSERT INTO dbo.Permissions (Id, Code, Name) VALUES
 (1, N'Action.Published.View', N'Xem dữ liệu đã publish'),
 (2, N'Action.Publish.Schedule', N'Publish schedule'),
 (3, N'Action.User.Manage', N'Quản lý người dùng'),
 (4, N'Action.Role.Manage', N'Quản lý phân quyền'),
 (5, N'Action.Store.View', N'Xem danh sách cửa hàng');
SET IDENTITY_INSERT dbo.Permissions OFF;
GO

SET IDENTITY_INSERT dbo.Roles ON;
IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE Id=1)
INSERT INTO dbo.Roles (Id, Name, Description, IsSystem) VALUES
 (1, N'Administrator', N'Toàn quyền hệ thống', 1),
 (2, N'Manager', N'Publish và xem dữ liệu', 1),
 (3, N'Staff', N'Xem dữ liệu đã publish', 1),
 (4, N'Viewer', N'Chỉ xem dữ liệu đã publish', 1);
SET IDENTITY_INSERT dbo.Roles OFF;
GO

MERGE dbo.RolePermissions AS t
USING (VALUES
 (1,1),(1,2),(1,3),(1,4),(1,5),
 (2,1),(2,2),(2,5),
 (3,1),(3,5),
 (4,1)
) AS s(RoleId, PermissionId)
ON t.RoleId=s.RoleId AND t.PermissionId=s.PermissionId
WHEN NOT MATCHED THEN INSERT (RoleId, PermissionId) VALUES (s.RoleId, s.PermissionId);
GO

IF OBJECT_ID(N'dbo.FK_Users_Roles_RoleId', N'F') IS NULL
    ALTER TABLE dbo.Users WITH CHECK ADD CONSTRAINT FK_Users_Roles_RoleId FOREIGN KEY (RoleId) REFERENCES dbo.Roles(Id) ON DELETE CASCADE;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_Users_RoleId' AND object_id=OBJECT_ID(N'dbo.Users'))
    CREATE INDEX IX_Users_RoleId ON dbo.Users(RoleId);
GO

-- Admin user is created by app seed (Auth:AdminEmail / Auth:AdminPassword) on startup.
