"""Write a store-week suggested roster into schema `sched` (db/sql/0001_sched_core.sql).

One store-week = one set of rows: writing again replaces the previous roster of that store-week
(DELETE sched.ScheduleWeeks -> children cascade, then INSERT) in one transaction, and bumps
sched.meta_build so the web UI refreshes. Values shown to users are Vietnamese.
"""
from __future__ import annotations

import getpass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text

from ..db import ado_to_odbc, describe_connection  # noqa: F401  (re-exported for older callers)
from ..output.tables import sorted_employees
from ..timeutil import DAY_MINUTES, monday_of, parse_hhmm

WEEKDAY_VI = ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật")
STATUS_VI = {"DRAFT": "Nháp", "BLOCKED": "Không xếp được"}
ASSESSMENT_VI = {"HEALTHY": "Tốt", "ATTENTION": "Cần chú ý", "CRITICAL": "Rủi ro cao"}
SEVERITY_VI = {"CRITICAL": "Lỗi", "WARNING": "Cảnh báo", "SUGGESTION": "Gợi ý"}
COVERAGE_VI = {"OK": "Đủ người", "OVERSTAFF": "Dư người", "STAFF_GAP": "Thiếu người", "MANAGER_GAP": "Thiếu quản lý"}
SHIFT_ROLE_VI = {"OPEN": "Mở cửa", "CLOSE": "Đóng cửa", "MOD_FILL": "Quản lý giữa ca", "PAIR": "Kèm quản lý", "FLOOR": "Bù đủ 2 người"}
DAYTYPE_WORK, DAYTYPE_OFF, DAYTYPE_AL, DAYTYPE_NONE = "Làm", "OFF", "Nghỉ phép", "Không xếp ca"
DAYTYPE_AWAY, DAYTYPE_HOME = "Đi hỗ trợ", "Ở store gốc"
# issues that describe system data, not the roster: kept in validation_issues.csv only
from ..validation.kpi import SYSTEM_DATA_CODES as HIDDEN_CODES  # noqa: E402

WEEK_COLS = ["StoreCode", "WeekStart", "WeekEnd", "StoreName", "OpeningTime", "ClosingTime", "Status", "Assessment", "TcphTarget",
             "WeeklyTcph", "TcphInTarget", "ForecastTc", "LaborHours", "NsoHours", "StaffCoveragePct", "ManagerCoveragePct",
             "EmployeeCount", "ErrorCount", "WarningCount", "AvailabilityWeek", "RunId", "Note", "CreatedAt", "CreatedBy"]
ROSTER_COLS = ["StoreCode", "WeekStart", "WorkDate", "Weekday", "EmployeeId", "EmployeeName", "Position", "EmploymentType",
               "LaborGroup", "HomeStore", "DayType", "StartTime", "EndTime", "Hours", "ShiftCode", "ShiftRole", "Note", "SortOrder"]
DAILY_COLS = ["StoreCode", "WeekStart", "WorkDate", "Weekday", "DayStatus", "ForecastTc", "RegularHours", "TrainingHours", "NsoHours",
              "Tcph", "TcphInclNso", "TcphInTarget", "TargetHoursMin", "TargetHoursMax", "NeededStaffHours", "ScheduledStaffHours",
              "MissingStaffHours", "HoursWithoutManager", "Openers", "Closers"]
HOURLY_COLS = ["StoreCode", "WeekStart", "WorkDate", "Weekday", "Slot", "TimeSlot", "ForecastTc", "IsPeakHour", "NeededStaff",
               "ScheduledStaff", "ManagersOnDuty", "MissingStaff", "Status"]
ISSUE_COLS = ["StoreCode", "WeekStart", "Severity", "WorkDate", "EmployeeId", "EmployeeName", "Message", "IssueCode"]

TABLE_COLS = {"ScheduleWeeks": WEEK_COLS, "ScheduleRoster": ROSTER_COLS, "ScheduleDailySummary": DAILY_COLS,
              "ScheduleHourlyCoverage": HOURLY_COLS, "ScheduleIssues": ISSUE_COLS}


# ----------------------------------------------------------------------------- value helpers
def _dec(v, places: int = 1):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return Decimal(str(round(f, places)))


def _int(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    return int(round(float(v)))


def _bool(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    return bool(v)


def _time(minutes: int) -> time:
    m = int(minutes) % DAY_MINUTES
    return time(m // 60, m % 60)


def _hhmm(minutes: int) -> str:
    return "24:00" if minutes >= DAY_MINUTES else f"{minutes // 60:02d}:{minutes % 60:02d}"


def _weekday(d: date) -> str:
    return WEEKDAY_VI[d.weekday()]


def shift_role(tags: set[str]) -> str | None:
    roles = [SHIFT_ROLE_VI[t] for t in ("OPEN", "CLOSE", "MOD_FILL", "PAIR", "FLOOR") if t in tags]
    return ", ".join(roles) or None


# ----------------------------------------------------------------------------- payload
def build_payload(res, cfg, created_by: str | None = None, now: datetime | None = None, run_id: int | None = None) -> dict[str, list[dict]]:
    """RunResult -> rows (dicts keyed by column) per table. Pure: no DB access."""
    from ..issues import CRITICAL, WARNING
    from ..planning_window import server_today

    tz = ZoneInfo(cfg.timezone)
    now = (now or datetime.now(tz)).astimezone(tz)
    sid, week = res.store_id, res.week_start
    swi = res.swi
    store = swi.store if swi is not None else None
    emps = {e.employee_id: e for e in swi.employees} if swi is not None else {}
    issues = [i for i in res.issues if i.code not in HIDDEN_CODES]
    blocked = res.roster is None
    k = res.kpi
    daily = res.daily_kpi
    aw = swi.availability_week if swi is not None else None

    notes = []
    if week <= monday_of(server_today(cfg, now)):
        notes.append("Chạy thử cho tuần đã qua (back-test)")
    if aw and aw != week:
        notes.append(f"dùng lịch bận tuần {aw:%d/%m/%Y}")

    forecast_tc = labor = nso = None
    if daily is not None and len(daily):
        open_days = daily[daily["status"] == "OPEN"]
        forecast_tc = open_days["adtc"].sum()
        labor = open_days["labor_reg"].sum() + open_days["labor_train"].sum()
        nso = open_days["labor_nso"].sum()

    week_row = dict(zip(WEEK_COLS, (
        sid, week, week + timedelta(days=6), store.short_name if store else None,
        None if store is None or store.is_24h else _hhmm(store.opening_min),
        None if store is None or store.is_24h else _hhmm(store.closing_min),
        STATUS_VI["BLOCKED" if blocked else "DRAFT"], ASSESSMENT_VI.get(k.planning_status) if k else ASSESSMENT_VI["CRITICAL"],
        _dec(store.tcph_target, 2) if store else None, _dec(k.weekly_tcph, 2) if k else None, _bool(k.tcph_in_band) if k else None,
        _dec(forecast_tc), _dec(labor), _dec(nso), _dec(k.coverage_pct) if k else None, _dec(k.manager_coverage_pct) if k else None,
        len(emps), sum(i.severity == CRITICAL for i in issues), sum(i.severity == WARNING for i in issues),
        aw, run_id, "; ".join(notes) or None, now.replace(tzinfo=None, microsecond=0), created_by or getpass.getuser(),
    ), strict=True))

    roster_rows: list[dict] = []
    opens: dict[date, int] = {}
    closes: dict[date, int] = {}
    if not blocked:
        r = res.roster
        codes = swi.shift_codes
        al_s, al_e = parse_hhmm(cfg.al_shift_start), parse_hhmm(cfg.al_shift_end)
        aw_s, aw_e = parse_hhmm(cfg.away_shift_start), parse_hhmm(cfg.away_shift_end)
        for order, emp in enumerate(sorted_employees(list(r.emps.values())), start=1):
            eid = emp.employee_id
            for d in r.dates:
                sh = r.shift_of(eid, d)
                note = None
                if sh is not None:
                    row = (DAYTYPE_WORK, _time(sh.start_min), _time(sh.end_min), _dec(sh.hours), codes.lookup(sh.start_min, sh.end_min),
                           shift_role(sh.tags))
                    opens[d] = opens.get(d, 0) + ("OPEN" in sh.tags)
                    closes[d] = closes.get(d, 0) + ("CLOSE" in sh.tags)
                    if emp.is_borrowed:
                        note = f"Mượn từ store {emp.home_store}"
                elif d in r.al.get(eid, ()):
                    row = (DAYTYPE_AL, _time(al_s), _time(al_e), _dec(cfg.al_paid_hours), codes.lookup(al_s, al_e), None)
                elif d in r.away.get(eid, {}):
                    row = (DAYTYPE_AWAY, _time(aw_s), _time(aw_e), _dec(cfg.ft_shift_hours), codes.lookup(aw_s, aw_e), None)
                    note = f"Hỗ trợ store {r.away[eid][d]}"
                elif d in r.not_here.get(eid, ()):
                    row = (DAYTYPE_HOME, None, None, Decimal("0"), None, None)
                    note = f"Nhân viên store {emp.home_store}"
                elif d not in r.open_dates or d in r.off.get(eid, ()):
                    row = (DAYTYPE_OFF, None, None, Decimal("0"), None, None)
                else:
                    row = (DAYTYPE_NONE, None, None, Decimal("0"), None, None)
                day_type, st, en, hrs, code, role = row
                roster_rows.append(dict(zip(ROSTER_COLS, (
                    sid, week, d, _weekday(d), eid, emp.name, emp.position_display, emp.employment_type, emp.labor_group,
                    emp.home_store, day_type, st, en, hrs, code, role, note, order), strict=True)))

    daily_rows: list[dict] = []
    if daily is not None:
        for x in daily.to_dict("records"):
            g = x.get
            d = g("date")
            daily_rows.append(dict(zip(DAILY_COLS, (
                sid, week, d, _weekday(d), "Mở cửa" if g("status") == "OPEN" else "Đóng cửa", _dec(g("adtc")),
                _dec(g("labor_reg")), _dec(g("labor_train")), _dec(g("labor_nso")), _dec(g("tcph"), 2), _dec(g("tcph_nso"), 2),
                _bool(g("tcph_in_band")), _dec(g("band_min_hours")), _dec(g("band_max_hours")), _int(g("required_hours")),
                _int(g("scheduled_hours")), _int(g("staff_gap_hours")), _int(g("manager_gap_slots")), opens.get(d, 0), closes.get(d, 0)), strict=True)))

    hourly_rows: list[dict] = []
    if res.coverage is not None:
        for c in res.coverage.itertuples(index=False):
            h = int(c.slot)
            hourly_rows.append(dict(zip(HOURLY_COLS, (
                sid, week, c.date, _weekday(c.date), h, f"{h:02d}:00-{(h + 1) % 24:02d}:00", _dec(c.forecast_tc), bool(c.is_peak),
                int(c.required_staff), int(c.scheduled_staff), int(c.scheduled_manager), int(c.staff_gap),
                COVERAGE_VI.get(str(c.status), str(c.status))), strict=True)))

    issue_rows: list[dict] = []
    for i in issues:
        if i.severity not in (CRITICAL, WARNING):
            continue                                   # INFO stays in validation_issues.csv
        name = emps[i.employee_id].name if i.employee_id in emps else None
        issue_rows.append(dict(zip(ISSUE_COLS, (sid, week, SEVERITY_VI[i.severity], i.date, i.employee_id, name, i.message[:1000], i.code), strict=True)))
    for rec in (k.recommendations if k else []):
        issue_rows.append(dict(zip(ISSUE_COLS, (sid, week, SEVERITY_VI["SUGGESTION"], rec.get("date"), None, None,
                                                str(rec["text"])[:1000], rec.get("type")), strict=True)))
    order = {"Lỗi": 0, "Cảnh báo": 1, "Gợi ý": 2}
    issue_rows.sort(key=lambda r: (order[r["Severity"]], r["WorkDate"] or date.min, r["IssueCode"] or ""))

    return {"ScheduleWeeks": [week_row], "ScheduleRoster": roster_rows, "ScheduleDailySummary": daily_rows,
            "ScheduleHourlyCoverage": hourly_rows, "ScheduleIssues": issue_rows}


# ----------------------------------------------------------------------------- write
def write_payload(engine: Engine, payload: dict, schema: str = "sched", built_by: str | None = None) -> bool:
    """Replace the store-week in one transaction + bump sched.meta_build. Returns True when an older roster was replaced."""
    wk = payload["ScheduleWeeks"][0]
    with engine.begin() as conn:
        replaced = conn.execute(text(f"DELETE FROM {schema}.ScheduleWeeks WHERE StoreCode = :s AND WeekStart = :w"),
                                {"s": wk["StoreCode"], "w": wk["WeekStart"]}).rowcount > 0
        for table, cols in TABLE_COLS.items():
            rows = payload[table]
            if rows:
                conn.execute(text(f"INSERT INTO {schema}.{table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"), rows)
        v = int(conn.execute(text(f"SELECT ISNULL(MAX(DataVersion), 0) + 1 FROM {schema}.meta_build")).scalar())
        conn.execute(text(f"INSERT INTO {schema}.meta_build (Component, DataVersion, BuiltAt, BuiltBy, Detail) VALUES "
                          f"('schedule', :v, :t, :u, :d)"),
                     {"v": v, "t": wk["CreatedAt"], "u": built_by or wk["CreatedBy"], "d": f"{wk['StoreCode']} {wk['WeekStart']}"})
    return replaced


def write_run(res, cfg, engine: Engine | None = None, created_by: str | None = None, run_id: int | None = None) -> tuple[bool, dict[str, int]]:
    from ..db import get_engine

    payload = build_payload(res, cfg, created_by, run_id=run_id)
    replaced = write_payload(engine or get_engine(), payload)
    return replaced, {t: len(payload[t]) for t in TABLE_COLS}
