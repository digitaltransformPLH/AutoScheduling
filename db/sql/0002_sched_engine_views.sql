-- Engine input views: map the dbo tables owned by the ASP.NET app (EF) to the engine input contract
-- (SPEC Section 2). The engine only reads these views, never dbo directly, so a change in the .NET
-- schema is absorbed here.

-- store hours (dim_store_detail) + OPS targets (ops_store_config.store_id = dim_store.Id)
CREATE VIEW sched.vw_engine_store AS
SELECT
    s.Code                    AS store_id,
    s.Id                      AS store_db_id,
    s.Name                    AS short_name,
    s.IsActive                AS is_active,
    d.OpenTime                AS opening_time,
    d.CloseTime               AS closing_time,
    CAST(CASE WHEN d.OpenTime = N'00:00' AND d.CloseTime IN (N'24:00', N'23:59', N'00:00') THEN 1 ELSE 0 END AS BIT) AS is_24h,
    CAST(0 AS BIT)            AS closed_sat,
    CAST(0 AS BIT)            AS closed_sun,
    o.tcph_target,
    o.tcph_ceiling_mult,
    o.open_staff,
    o.close_staff,
    o.min_staff_per_slot
FROM dbo.dim_store s
LEFT JOIN dbo.dim_store_detail d ON d.StoreCode = s.Code
LEFT JOIN dbo.ops_store_config o ON o.store_id = s.Id;
GO

CREATE VIEW sched.vw_engine_employee AS
SELECT
    CAST(e.EmployeeNumber AS NVARCHAR(20)) AS employee_id,
    e.Id                      AS employee_db_id,
    e.PlantCode               AS store_id,
    e.FullName                AS name,
    e.Position                AS position,
    e.EmploymentType          AS employment_type,
    e.LaborGroup              AS labor_group,
    e.Status                  AS status
FROM dbo.dim_employee e;
GO

-- one row per employee x day; busy_from/busy_to NULL = free all day
CREATE VIEW sched.vw_engine_busy AS
SELECT
    a.PlantCode               AS store_id,
    CAST(a.EmployeeNumber AS NVARCHAR(20)) AS employee_id,
    a.WeekStartMonday         AS week_start,
    a.WorkDate                AS work_date,
    CONVERT(CHAR(5), a.BusyFrom, 108) AS busy_from,
    CONVERT(CHAR(5), a.BusyTo, 108)   AS busy_to,
    a.IsPaidLeave             AS is_paid_leave
FROM dbo.employee_availability_slot a;
GO

-- employee lent from home store to receiving store for [start_date, end_date]
CREATE VIEW sched.vw_engine_secondment AS
SELECT
    s.Id                      AS secondment_id,
    CAST(e.EmployeeNumber AS NVARCHAR(20)) AS employee_id,
    s.HomePlantCode           AS home_store,
    s.ReceivingStoreCode      AS receiving_store,
    s.StartDate               AS start_date,
    s.EndDate                 AS end_date,
    s.Status                  AS status,
    e.FullName                AS name,
    e.Position                AS position,
    e.EmploymentType          AS employment_type,
    e.LaborGroup              AS labor_group,
    e.Status                  AS employee_status
FROM dbo.employee_secondment s
JOIN dbo.dim_employee e ON e.Id = s.EmployeeId;
GO

CREATE VIEW sched.vw_engine_forecast AS
SELECT
    f.plan_run_id, f.iso_week, f.week_start, f.store_id, f.forecast_date, f.hour, f.day_of_week, f.day_type, f.event_key,
    f.store_age_layer, f.tc_dine_in, f.tc_delivery, f.tc_p50, f.tc_p90, f.is_peak, f.forecast_origin, f.forecast_run_id,
    f.bill_cutoff_date, f.method_version, f.created_at
FROM dbo.forecast_tc_hourly f;
GO
