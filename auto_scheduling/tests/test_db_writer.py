"""DB payload (schema sched) + connection-string handling (no database needed)."""
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from auto_scheduling.db import ado_to_odbc, describe_connection, sqlalchemy_url
from auto_scheduling.optimizer.greedy import optimise
from auto_scheduling.optimizer.preflight import build_templates
from auto_scheduling.output.db_writer import (
    DAILY_COLS,
    HOURLY_COLS,
    ISSUE_COLS,
    ROSTER_COLS,
    TABLE_COLS,
    WEEK_COLS,
    build_payload,
    shift_role,
)
from auto_scheduling.output.tables import build_daily_kpi, build_schedule, build_slot_coverage, roster_grid
from auto_scheduling.pipeline import RunResult
from auto_scheduling.validation.kpi import compute_kpi
from auto_scheduling.validation.rules import validate_roster
from conftest import WEEK
from test_optimizer import make_swi, team_a

NOW = datetime(2026, 11, 13, 10, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))


def _result(cfg, busy=(), employees=None, extra_busy=()):
    swi, issues = make_swi(cfg, employees or team_a(), busy)
    swi.busy = list(swi.busy) + list(extra_busy)
    templates = build_templates(swi.calendar, swi.shift_codes, cfg, issues)
    r = optimise(swi, templates, cfg, issues)
    validate_roster(r, swi.shift_codes, cfg, issues)
    res = RunResult(store_id=swi.store.store_id, week_start=WEEK, issues=issues, swi=swi, templates=templates, roster=r)
    res.schedule = build_schedule(r, swi.shift_codes, cfg)
    res.coverage = build_slot_coverage(swi, r, cfg)
    res.daily_kpi = build_daily_kpi(swi, r, res.coverage)
    res.grid = roster_grid(r, cfg)
    res.kpi = compute_kpi(res.coverage, res.schedule, res.daily_kpi, swi.store, issues)
    return res


def test_ado_to_odbc_and_url():
    cs = ("Data Source=10.0.0.1,1433;Initial Catalog=AutoScheduling;User ID=u1;Password=secret!;Encrypt=True;"
          "Trust Server Certificate=True;Authentication=SqlPassword;")
    odbc = ado_to_odbc(cs, driver="ODBC Driver 18 for SQL Server")
    assert odbc.startswith("Driver={ODBC Driver 18 for SQL Server};Server=10.0.0.1,1433;Database=AutoScheduling;UID=u1;")
    assert "TrustServerCertificate=yes" in odbc and "Encrypt=yes" in odbc
    assert "PWD=***" in describe_connection(odbc) and "secret" not in describe_connection(odbc)
    assert "Trusted_Connection=yes" in ado_to_odbc("Server=.;Database=X;Trusted_Connection=True;", driver="SQL Server")
    assert sqlalchemy_url(cs).startswith("mssql+pyodbc:///?odbc_connect=")
    assert sqlalchemy_url("mssql+pyodbc://x") == "mssql+pyodbc://x"


def test_shift_role_labels():
    assert shift_role({"OPEN", "LOCKED"}) == "Mở cửa"
    assert shift_role({"CLOSE", "LOCKED"}) == "Đóng cửa"
    assert shift_role({"LOCKED"}) is None


def test_payload_shapes(cfg):
    res = _result(cfg, busy=[("FT1", "Wed", "AL", "AL")])
    p = build_payload(res, cfg, created_by="tester", now=NOW, run_id=7)
    assert set(p) == set(TABLE_COLS)
    for table, cols in TABLE_COLS.items():
        assert all(list(r) == cols for r in p[table]), table
    week = p["ScheduleWeeks"][0]
    assert (week["StoreCode"], week["WeekStart"], week["WeekEnd"].isoformat()) == ("T001", WEEK, "2026-11-15")
    assert week["Status"] == "Nháp" and week["Assessment"] in ("Tốt", "Cần chú ý", "Rủi ro cao") and week["RunId"] == 7
    assert "back-test" in week["Note"] and week["CreatedBy"] == "tester" and week["CreatedAt"].tzinfo is None
    assert week["TcphTarget"] == Decimal("8.0") and week["EmployeeCount"] == len(res.swi.employees)

    roster = p["ScheduleRoster"]
    assert len(roster) == len(res.swi.employees) * 7
    assert roster[0]["Weekday"] == "Thứ 2" and roster[6]["Weekday"] == "Chủ nhật"
    al = [r for r in roster if r["DayType"] == "Nghỉ phép"]
    assert len(al) == 1 and al[0]["EmployeeId"] == "FT1" and al[0]["ShiftCode"] == "1180" and al[0]["StartTime"] == time(7, 0)
    work = [r for r in roster if r["DayType"] == "Làm"]
    assert len(work) == sum(1 for _ in res.roster.all_shifts()) and all(r["ShiftCode"] for r in work)
    assert any(r["ShiftRole"] == "Mở cửa" for r in work) and any(r["ShiftRole"] == "Đóng cửa" for r in work)
    off = [r for r in roster if r["DayType"] == "OFF"]
    assert off and all(r["StartTime"] is None and r["Hours"] == 0 for r in off)
    assert roster[0]["EmployeeId"] == "SM" and roster[0]["SortOrder"] == 1
    assert len({(r["WorkDate"], r["EmployeeId"]) for r in roster}) == len(roster)          # PK unique

    hourly = p["ScheduleHourlyCoverage"]
    assert len(hourly) == 7 * 15 and hourly[0]["TimeSlot"] == "07:00-08:00" and hourly[0]["Slot"] == 7
    assert {h["Status"] for h in hourly} <= {"Đủ người", "Dư người", "Thiếu người", "Thiếu quản lý"}
    daily = p["ScheduleDailySummary"]
    assert len(daily) == 7 and daily[0]["DayStatus"] == "Mở cửa" and daily[0]["Openers"] >= 2 and daily[0]["Closers"] >= 2
    sev = [i["Severity"] for i in p["ScheduleIssues"]]
    assert set(sev) <= {"Lỗi", "Cảnh báo", "Gợi ý"} and sev == sorted(sev, key=["Lỗi", "Cảnh báo", "Gợi ý"].index)
    assert len(DAILY_COLS) and len(HOURLY_COLS) and len(ISSUE_COLS) and len(ROSTER_COLS) and len(WEEK_COLS)


def test_payload_secondment_away_day(cfg):
    from auto_scheduling.models import BusyBlock
    res = _result(cfg, extra_busy=[BusyBlock("FT2", 0, None, None, away_to="2023")])   # FT2 at store 2023 on Monday
    roster = {(r["EmployeeId"], r["Weekday"]): r for r in build_payload(res, cfg, created_by="t", now=NOW)["ScheduleRoster"]}
    mon = roster[("FT2", "Thứ 2")]
    assert mon["DayType"] == "Đi hỗ trợ" and mon["Note"] == "Hỗ trợ store 2023"
    # still paid hours, never OFF [DECISION 19-Nov-2026]: 07:00-15:00, 8h, code 1180
    assert (mon["StartTime"].hour, mon["EndTime"].hour, int(mon["Hours"]), mon["ShiftCode"]) == (7, 15, 8, "1180")


def test_payload_blocked_week(cfg):
    from auto_scheduling.issues import IssueLog
    log = IssueLog(store_id="9999", week_start=WEEK)
    log.critical("STORE_NOT_FOUND", "store 9999 not in dim_store")
    res = RunResult(store_id="9999", week_start=WEEK, issues=log)
    p = build_payload(res, cfg, created_by="tester", now=NOW)
    week = p["ScheduleWeeks"][0]
    assert week["Status"] == "Không xếp được" and week["Assessment"] == "Rủi ro cao" and week["ErrorCount"] == 1
    assert not p["ScheduleRoster"] and not p["ScheduleHourlyCoverage"] and len(p["ScheduleIssues"]) == 1
