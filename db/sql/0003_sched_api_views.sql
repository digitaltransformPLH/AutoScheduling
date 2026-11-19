-- Read views for the API (one view per endpoint family; the API adds only WHERE / ORDER BY on these).

-- store picker: active stores with flags telling what data is ready
CREATE VIEW sched.vw_store_list AS
SELECT
    s.store_id                AS StoreCode,
    s.short_name              AS StoreName,
    s.opening_time            AS OpeningTime,
    s.closing_time            AS ClosingTime,
    s.tcph_target             AS TcphTarget,
    (SELECT COUNT(*) FROM dbo.dim_employee e WHERE e.PlantCode = s.store_id) AS EmployeeCount,
    CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.forecast_tc_hourly f WHERE f.store_id = s.store_id) THEN 1 ELSE 0 END AS BIT) AS HasForecast,
    CAST(CASE WHEN s.tcph_target IS NOT NULL AND s.opening_time IS NOT NULL
              AND EXISTS (SELECT 1 FROM dbo.dim_employee e WHERE e.PlantCode = s.store_id) THEN 1 ELSE 0 END AS BIT) AS ReadyToSchedule,
    (SELECT COUNT(*) FROM sched.ScheduleWeeks w WHERE w.StoreCode = s.store_id) AS ScheduledWeeks
FROM sched.vw_engine_store s
WHERE s.is_active = 1;
GO

CREATE VIEW sched.vw_forecast_weeks AS
SELECT week_start AS WeekStart, COUNT(DISTINCT store_id) AS StoreCount, MAX(created_at) AS CreatedAt, MAX(method_version) AS MethodVersion
FROM dbo.forecast_tc_hourly
GROUP BY week_start;
GO

CREATE VIEW sched.vw_schedule_week AS
SELECT w.*, r.Status AS RunStatus, r.FinishedAt AS RunFinishedAt
FROM sched.ScheduleWeeks w
LEFT JOIN sched.engine_run r ON r.RunId = w.RunId;
GO

CREATE VIEW sched.vw_schedule_roster AS SELECT * FROM sched.ScheduleRoster;
GO
CREATE VIEW sched.vw_schedule_daily AS SELECT * FROM sched.ScheduleDailySummary;
GO
CREATE VIEW sched.vw_schedule_hourly AS SELECT * FROM sched.ScheduleHourlyCoverage;
GO
CREATE VIEW sched.vw_schedule_issues AS SELECT * FROM sched.ScheduleIssues;
GO

CREATE VIEW sched.vw_engine_runs AS
SELECT RunId, StoreCode, WeekStart, AvailabilityWeek, Status, Assessment, Message, RequestedBy, RequestedAt, StartedAt, FinishedAt
FROM sched.engine_run;
GO

-- input pages (read-only in this platform; the ASP.NET app edits them)
CREATE VIEW sched.vw_input_employees AS
SELECT e.store_id AS StoreCode, e.employee_id AS EmployeeId, e.name AS EmployeeName, e.position AS Position,
       e.employment_type AS EmploymentType, e.labor_group AS LaborGroup, e.status AS Status
FROM sched.vw_engine_employee e;
GO

CREATE VIEW sched.vw_input_availability AS
SELECT b.store_id AS StoreCode, b.employee_id AS EmployeeId, e.name AS EmployeeName, b.week_start AS WeekStart,
       b.work_date AS WorkDate, b.busy_from AS BusyFrom, b.busy_to AS BusyTo, b.is_paid_leave AS IsPaidLeave
FROM sched.vw_engine_busy b
LEFT JOIN sched.vw_engine_employee e ON e.employee_id = b.employee_id;
GO

CREATE VIEW sched.vw_input_secondment AS
SELECT secondment_id AS Id, employee_id AS EmployeeId, name AS EmployeeName, position AS Position, home_store AS HomeStore,
       receiving_store AS ReceivingStore, start_date AS StartDate, end_date AS EndDate, status AS Status
FROM sched.vw_engine_secondment;
GO

CREATE VIEW sched.vw_input_store_config AS
SELECT store_id AS StoreCode, short_name AS StoreName, opening_time AS OpeningTime, closing_time AS ClosingTime, is_24h AS Is24h,
       tcph_target AS TcphTarget, tcph_ceiling_mult AS TcphCeilingMult, open_staff AS OpenStaff, close_staff AS CloseStaff,
       min_staff_per_slot AS MinStaffPerSlot
FROM sched.vw_engine_store
WHERE is_active = 1;
GO
