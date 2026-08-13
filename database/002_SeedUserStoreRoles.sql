-- After InitialCreate: grant a real Windows user StoreAdmin on all active stores.
-- Replace the @WinUser value before running.

USE WorkforcePlanning;
GO

DECLARE @WinUser NVARCHAR(256) = N'DOMAIN\your.user';  -- e.g. CONTOSO\tienlta
DECLARE @Display NVARCHAR(200) = N'Your Name';
DECLARE @UserId INT;

IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE WindowsUserName = @WinUser)
    INSERT INTO dbo.Users (WindowsUserName, DisplayName, IsActive)
    VALUES (@WinUser, @Display, 1);

SELECT @UserId = Id FROM dbo.Users WHERE WindowsUserName = @WinUser;

INSERT INTO dbo.UserStoreRoles (UserId, StoreId, Role)
SELECT @UserId, s.Id, N'StoreAdmin'
FROM dbo.Stores s
WHERE s.IsActive = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.UserStoreRoles r
      WHERE r.UserId = @UserId AND r.StoreId = s.Id
  );

SELECT u.WindowsUserName, s.Code, r.Role
FROM dbo.UserStoreRoles r
JOIN dbo.Users u ON u.Id = r.UserId
JOIN dbo.Stores s ON s.Id = r.StoreId
WHERE u.WindowsUserName = @WinUser;
GO
