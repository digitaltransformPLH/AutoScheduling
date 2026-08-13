-- Grant IIS App Pool access to WorkforcePlanning (Trusted_Connection / Windows auth to SQL).
-- Replace the login name with your real App Pool name from IIS Manager.
-- Examples:
--   IIS APPPOOL\WorkforcePlanning
--   IIS APPPOOL\DefaultAppPool

USE [master];
GO

DECLARE @PoolLogin SYSNAME = N'IIS APPPOOL\WorkforcePlanningPool';  -- <-- đổi đúng tên App Pool

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = @PoolLogin)
    EXEC(N'CREATE LOGIN ' + QUOTENAME(@PoolLogin) + N' FROM WINDOWS');

USE [WorkforcePlanningPool];
GO

DECLARE @PoolLogin SYSNAME = N'IIS APPPOOL\WorkforcePlanningPool';  -- <-- cùng tên ở trên
DECLARE @sql NVARCHAR(MAX);

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @PoolLogin)
BEGIN
    SET @sql = N'CREATE USER ' + QUOTENAME(@PoolLogin) + N' FOR LOGIN ' + QUOTENAME(@PoolLogin);
    EXEC(@sql);
END

SET @sql = N'ALTER ROLE db_datareader ADD MEMBER ' + QUOTENAME(@PoolLogin);
EXEC(@sql);
SET @sql = N'ALTER ROLE db_datawriter ADD MEMBER ' + QUOTENAME(@PoolLogin);
EXEC(@sql);
SET @sql = N'ALTER ROLE db_ddladmin ADD MEMBER ' + QUOTENAME(@PoolLogin); -- for Migrate at startup
EXEC(@sql);

SELECT dp.name AS DbUser, r.name AS RoleName
FROM sys.database_role_members rm
JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
JOIN sys.database_principals dp ON dp.principal_id = rm.member_principal_id
WHERE dp.name = @PoolLogin;
GO
