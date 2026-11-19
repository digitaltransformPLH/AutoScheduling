-- Login + permissions reuse the ASP.NET app's accounts (dbo.Users / Roles / Permissions / UserStores, read-only here)
-- [DECISION 19-Nov-2026, Thanh]: the platform checks the password itself and issues its own session; users / roles are still
-- managed in the .NET app. Input editing moves to the platform (the .NET edit screens are retired).

CREATE VIEW sched.vw_auth_user AS
SELECT u.Id AS UserId, LOWER(u.Email) AS Email, u.DisplayName, u.IsActive, u.AllStores, u.PasswordHash, r.Name AS RoleName
FROM dbo.Users u
JOIN dbo.Roles r ON r.Id = u.RoleId;
GO

CREATE VIEW sched.vw_auth_user_permission AS
SELECT u.Id AS UserId, p.Code AS PermissionCode
FROM dbo.Users u
JOIN dbo.RolePermissions rp ON rp.RoleId = u.RoleId
JOIN dbo.Permissions p ON p.Id = rp.PermissionId;
GO

-- UserStores.StoreId -> dim_store.Id
CREATE VIEW sched.vw_auth_user_store AS
SELECT us.UserId, s.Code AS StoreCode
FROM dbo.UserStores us
JOIN dbo.dim_store s ON s.Id = us.StoreId;
GO

-- only active employees count towards "ready to schedule"
CREATE OR ALTER VIEW sched.vw_store_list AS
SELECT
    s.store_id                AS StoreCode,
    s.short_name              AS StoreName,
    s.opening_time            AS OpeningTime,
    s.closing_time            AS ClosingTime,
    s.tcph_target             AS TcphTarget,
    (SELECT COUNT(*) FROM dbo.dim_employee e WHERE e.PlantCode = s.store_id AND e.Status = N'Active') AS EmployeeCount,
    CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.forecast_tc_hourly f WHERE f.store_id = s.store_id) THEN 1 ELSE 0 END AS BIT) AS HasForecast,
    CAST(CASE WHEN s.tcph_target IS NOT NULL AND s.opening_time IS NOT NULL
              AND EXISTS (SELECT 1 FROM dbo.dim_employee e WHERE e.PlantCode = s.store_id AND e.Status = N'Active') THEN 1 ELSE 0 END AS BIT) AS ReadyToSchedule,
    (SELECT COUNT(*) FROM sched.ScheduleWeeks w WHERE w.StoreCode = s.store_id) AS ScheduledWeeks
FROM sched.vw_engine_store s
WHERE s.is_active = 1;
GO

-- input views used by the edit screens: + last change
CREATE OR ALTER VIEW sched.vw_input_employees AS
SELECT e.PlantCode AS StoreCode, CAST(e.EmployeeNumber AS NVARCHAR(20)) AS EmployeeId, e.FullName AS EmployeeName, e.Position,
       e.EmploymentType, e.LaborGroup, e.Status, CAST(e.UpdatedAt AT TIME ZONE 'SE Asia Standard Time' AS DATETIME2(0)) AS UpdatedAt
FROM dbo.dim_employee e;
GO

CREATE OR ALTER VIEW sched.vw_input_secondment AS
SELECT s.Id, CAST(e.EmployeeNumber AS NVARCHAR(20)) AS EmployeeId, e.FullName AS EmployeeName, e.Position, s.HomePlantCode AS HomeStore,
       s.ReceivingStoreCode AS ReceivingStore, s.StartDate, s.EndDate, s.Status, s.UpdatedBy,
       CAST(s.UpdatedAt AT TIME ZONE 'SE Asia Standard Time' AS DATETIME2(0)) AS UpdatedAt
FROM dbo.employee_secondment s
JOIN dbo.dim_employee e ON e.Id = s.EmployeeId;
GO

CREATE OR ALTER VIEW sched.vw_input_store_config AS
SELECT s.store_id AS StoreCode, s.short_name AS StoreName, s.opening_time AS OpeningTime, s.closing_time AS ClosingTime, s.is_24h AS Is24h,
       s.tcph_target AS TcphTarget, s.tcph_ceiling_mult AS TcphCeilingMult, s.open_staff AS OpenStaff, s.close_staff AS CloseStaff,
       s.min_staff_per_slot AS MinStaffPerSlot, o.updated_by AS UpdatedBy,
       CAST(o.updated_at AT TIME ZONE 'SE Asia Standard Time' AS DATETIME2(0)) AS UpdatedAt
FROM sched.vw_engine_store s
LEFT JOIN dbo.ops_store_config o ON o.store_id = s.store_db_id
WHERE s.is_active = 1;
GO
