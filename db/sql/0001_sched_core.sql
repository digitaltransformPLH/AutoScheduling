-- Schema `sched`: owned by the auto-scheduling platform (Alembic). The ASP.NET app owns dbo.*.
-- Output tables keep one roster per store-week: re-running the engine deletes the week (children cascade) and inserts again.

IF SCHEMA_ID(N'sched') IS NULL EXEC(N'CREATE SCHEMA sched');
GO

-- data_version for the UI: bumped every time the engine writes a store-week or the ETL loads inputs
CREATE TABLE sched.meta_build (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_meta_build PRIMARY KEY,
    Component NVARCHAR(50) NOT NULL,                 -- schedule / inputs
    DataVersion INT NOT NULL,
    BuiltAt DATETIME2(0) NOT NULL,
    BuiltBy NVARCHAR(256) NOT NULL,
    Detail NVARCHAR(1000) NULL                        -- e.g. "2184 2026-11-09"
);
GO

-- one row per engine run requested from the UI / CLI
CREATE TABLE sched.engine_run (
    RunId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_engine_run PRIMARY KEY,
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,
    AvailabilityWeek DATE NULL,                       -- week whose busy data was used (back-test)
    Status NVARCHAR(20) NOT NULL,                     -- queued / running / done / failed
    Assessment NVARCHAR(20) NULL,
    Message NVARCHAR(2000) NULL,
    RequestedBy NVARCHAR(256) NOT NULL,
    RequestedAt DATETIME2(0) NOT NULL,
    StartedAt DATETIME2(0) NULL,
    FinishedAt DATETIME2(0) NULL
);
CREATE INDEX IX_engine_run_Store_Week ON sched.engine_run (StoreCode, WeekStart, RunId DESC);
GO

CREATE TABLE sched.ScheduleWeeks (
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,                          -- thứ 2
    WeekEnd DATE NOT NULL,                            -- chủ nhật
    StoreName NVARCHAR(200) NULL,
    OpeningTime NVARCHAR(5) NULL,
    ClosingTime NVARCHAR(5) NULL,
    Status NVARCHAR(20) NOT NULL,                     -- Nháp / Không xếp được
    Assessment NVARCHAR(20) NULL,                     -- Tốt / Cần chú ý / Rủi ro cao
    TcphTarget DECIMAL(9,2) NULL,
    WeeklyTcph DECIMAL(9,2) NULL,
    TcphInTarget BIT NULL,
    ForecastTc DECIMAL(12,1) NULL,
    LaborHours DECIMAL(9,1) NULL,
    NsoHours DECIMAL(9,1) NULL,
    StaffCoveragePct DECIMAL(5,1) NULL,
    ManagerCoveragePct DECIMAL(5,1) NULL,
    EmployeeCount INT NOT NULL,
    ErrorCount INT NOT NULL,
    WarningCount INT NOT NULL,
    AvailabilityWeek DATE NULL,
    RunId INT NULL,
    Note NVARCHAR(500) NULL,
    CreatedAt DATETIME2(0) NOT NULL,                  -- giờ Việt Nam
    CreatedBy NVARCHAR(256) NOT NULL,
    CONSTRAINT PK_ScheduleWeeks PRIMARY KEY (StoreCode, WeekStart)
);
GO

CREATE TABLE sched.ScheduleRoster (
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,
    WorkDate DATE NOT NULL,
    Weekday NVARCHAR(10) NOT NULL,                    -- Thứ 2 .. Chủ nhật
    EmployeeId NVARCHAR(20) NOT NULL,                 -- mã nhân viên (EmployeeNumber)
    EmployeeName NVARCHAR(200) NOT NULL,
    Position NVARCHAR(50) NOT NULL,
    EmploymentType NVARCHAR(2) NOT NULL,
    LaborGroup NVARCHAR(10) NOT NULL,
    HomeStore NVARCHAR(10) NULL,                      -- khác StoreCode khi nhân viên được mượn từ store khác
    DayType NVARCHAR(20) NOT NULL,                    -- Làm / OFF / Nghỉ phép / Không xếp ca / Đi hỗ trợ / Ở store gốc
    StartTime TIME(0) NULL,
    EndTime TIME(0) NULL,
    Hours DECIMAL(4,1) NOT NULL,
    ShiftCode NVARCHAR(10) NULL,
    ShiftRole NVARCHAR(100) NULL,                     -- Mở cửa / Đóng cửa / Quản lý giữa ca ...
    Note NVARCHAR(200) NULL,                          -- vd. "Hỗ trợ store 2023"
    SortOrder INT NOT NULL,
    CONSTRAINT PK_ScheduleRoster PRIMARY KEY (StoreCode, WorkDate, EmployeeId),
    CONSTRAINT FK_ScheduleRoster_ScheduleWeeks FOREIGN KEY (StoreCode, WeekStart)
        REFERENCES sched.ScheduleWeeks (StoreCode, WeekStart) ON DELETE CASCADE
);
CREATE INDEX IX_ScheduleRoster_Week ON sched.ScheduleRoster (StoreCode, WeekStart, SortOrder, WorkDate);
GO

CREATE TABLE sched.ScheduleDailySummary (
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,
    WorkDate DATE NOT NULL,
    Weekday NVARCHAR(10) NOT NULL,
    DayStatus NVARCHAR(20) NOT NULL,                  -- Mở cửa / Đóng cửa
    ForecastTc DECIMAL(10,1) NULL,
    RegularHours DECIMAL(6,1) NULL,
    TrainingHours DECIMAL(6,1) NULL,
    NsoHours DECIMAL(6,1) NULL,
    Tcph DECIMAL(9,2) NULL,
    TcphInclNso DECIMAL(9,2) NULL,
    TcphInTarget BIT NULL,
    TargetHoursMin DECIMAL(6,1) NULL,
    TargetHoursMax DECIMAL(6,1) NULL,
    NeededStaffHours INT NULL,
    ScheduledStaffHours INT NULL,
    MissingStaffHours INT NULL,
    HoursWithoutManager INT NULL,
    Openers INT NULL,
    Closers INT NULL,
    CONSTRAINT PK_ScheduleDailySummary PRIMARY KEY (StoreCode, WorkDate),
    CONSTRAINT FK_ScheduleDailySummary_ScheduleWeeks FOREIGN KEY (StoreCode, WeekStart)
        REFERENCES sched.ScheduleWeeks (StoreCode, WeekStart) ON DELETE CASCADE
);
CREATE INDEX IX_ScheduleDailySummary_Week ON sched.ScheduleDailySummary (StoreCode, WeekStart);
GO

CREATE TABLE sched.ScheduleHourlyCoverage (
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,
    WorkDate DATE NOT NULL,
    Weekday NVARCHAR(10) NOT NULL,
    Slot INT NOT NULL,                                -- giờ bắt đầu (7 = 07:00-08:00)
    TimeSlot NVARCHAR(11) NOT NULL,
    ForecastTc DECIMAL(10,1) NOT NULL,
    IsPeakHour BIT NOT NULL,
    NeededStaff INT NOT NULL,
    ScheduledStaff INT NOT NULL,
    ManagersOnDuty INT NOT NULL,
    MissingStaff INT NOT NULL,
    Status NVARCHAR(20) NOT NULL,                     -- Đủ người / Dư người / Thiếu người / Thiếu quản lý
    CONSTRAINT PK_ScheduleHourlyCoverage PRIMARY KEY (StoreCode, WorkDate, Slot),
    CONSTRAINT FK_ScheduleHourlyCoverage_ScheduleWeeks FOREIGN KEY (StoreCode, WeekStart)
        REFERENCES sched.ScheduleWeeks (StoreCode, WeekStart) ON DELETE CASCADE
);
CREATE INDEX IX_ScheduleHourlyCoverage_Week ON sched.ScheduleHourlyCoverage (StoreCode, WeekStart);
GO

CREATE TABLE sched.ScheduleIssues (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ScheduleIssues PRIMARY KEY,
    StoreCode NVARCHAR(10) NOT NULL,
    WeekStart DATE NOT NULL,
    Severity NVARCHAR(20) NOT NULL,                   -- Lỗi / Cảnh báo / Gợi ý
    WorkDate DATE NULL,
    EmployeeId NVARCHAR(20) NULL,
    EmployeeName NVARCHAR(200) NULL,
    Message NVARCHAR(1000) NOT NULL,
    IssueCode NVARCHAR(64) NULL,
    CONSTRAINT FK_ScheduleIssues_ScheduleWeeks FOREIGN KEY (StoreCode, WeekStart)
        REFERENCES sched.ScheduleWeeks (StoreCode, WeekStart) ON DELETE CASCADE
);
CREATE INDEX IX_ScheduleIssues_Week ON sched.ScheduleIssues (StoreCode, WeekStart, Severity);
GO

CREATE VIEW sched.vw_meta AS
SELECT ISNULL(MAX(DataVersion), 0) AS DataVersion, MAX(BuiltAt) AS BuiltAt
FROM sched.meta_build;
GO
