"""P4: output tables and File 2 (SPEC 7.1, 7.2)."""
from datetime import timedelta

import pandas as pd
from openpyxl import load_workbook

from auto_scheduling.inputs.shift_codes import load_shift_codes
from auto_scheduling.output.attendance import (HEADERS, attendance_file_name, attendance_store_code, build_attendance_rows,
                                               write_attendance_file)
from auto_scheduling.output.tables import build_daily_kpi, build_schedule, build_slot_coverage, roster_grid, sorted_employees
from auto_scheduling.optimizer.greedy import optimise
from auto_scheduling.optimizer.preflight import build_templates
from auto_scheduling.validation.kpi import compute_kpi
from auto_scheduling.validation.rules import validate_roster
from conftest import SHIFT_CODES_PATH, WEEK, make_store
from test_optimizer import make_emp, make_swi, team_a


def _run(cfg, busy=()):
    swi, issues = make_swi(cfg, team_a(), busy)
    templates = build_templates(swi.calendar, swi.shift_codes, cfg, issues)
    r = optimise(swi, templates, cfg, issues)
    validate_roster(r, swi.shift_codes, cfg, issues)
    return swi, r, issues


def test_store_code_and_file_name():
    assert attendance_store_code("2001") == "PL2001"
    assert attendance_store_code("1023") == "PL1023"
    assert attendance_store_code("PL-12345") == "PL2345"
    assert attendance_store_code("ABC") == "ABC"
    store = make_store(store_id="2189", short_name="HCM - 457A Tran Hung Dao")
    assert attendance_file_name(store, WEEK) == "2189_HCM_457A_Tran_Hung_Dao_Upload_Phan_Cong_20261109-20261115.xlsx"


def test_schedule_and_file2_rows(cfg):
    swi, r, issues = _run(cfg, busy=[("FT1", "Wed", "AL", "AL")])
    sched = build_schedule(r, swi.shift_codes, cfg)
    assert sched["shift_code"].notna().all()
    al = sched[sched["is_paid_leave"]]
    assert len(al) == 1 and al.iloc[0]["employee_id"] == "FT1" and (al.iloc[0]["start"], al.iloc[0]["end"]) == ("07:00", "15:00")
    rows, errors = build_attendance_rows(sched, swi.employees, swi.store, WEEK, swi.shift_codes, cfg)
    assert not errors
    assert len(rows) == len(swi.employees) * 7
    ids = [row[1] for row in rows[::7]]
    assert ids == [e.employee_id for e in sorted_employees(swi.employees)]
    assert ids[0] == "SM" and ids[-2:] == ["TR1", "NSO1"]                        # Regular -> Training -> NSO
    wed = WEEK + timedelta(days=2)
    al_row = next(row for row in rows if row[1] == "FT1" and row[4] == wed.strftime("%d.%m.%Y"))
    assert al_row[6] == 1180 and al_row[7].hour == 7 and al_row[8].hour == 15
    off_rows = [row for row in rows if row[6] == "OFF"]
    assert off_rows and all(row[7] is None and row[8] is None for row in off_rows)
    assert all(row[3] == 2003 and row[0] == "PL001" for row in rows)       # 'T001' -> digits '001' -> PL001


def test_file2_blocked_without_code(cfg, tmp_path):
    swi, r, issues = _run(cfg)
    sched = build_schedule(r, swi.shift_codes, cfg)
    sched.loc[sched.index[0], ["start", "end"]] = ["07:15", "15:15"]               # not on the grid -> no code
    path, errors = write_attendance_file(sched, swi.employees, swi.store, WEEK, swi.shift_codes, cfg, tmp_path)
    assert path is None and len(errors) == 1 and "07:15-15:15" in errors[0]
    path, errors = write_attendance_file(sched, swi.employees, swi.store, WEEK + timedelta(days=1), swi.shift_codes, cfg, tmp_path)
    assert path is None and "not a Monday" in errors[0]


def test_file2_xlsx_layout(cfg, tmp_path):
    swi, r, issues = _run(cfg)
    sched = build_schedule(r, swi.shift_codes, cfg)
    path, errors = write_attendance_file(sched, swi.employees, swi.store, WEEK, swi.shift_codes, cfg, tmp_path)
    assert path is not None and path.exists() and not errors
    ws = load_workbook(path)["Sheet1"]
    assert [c.value for c in ws[1]] == HEADERS
    assert ws.max_row == len(swi.employees) * 7 + 1
    assert ws.column_dimensions["G"].width == 62
    first = ws[2]
    assert first[3].value == 2003 and first[4].value == WEEK.strftime("%d.%m.%Y")
    shift_cells = [row for row in ws.iter_rows(min_row=2) if row[6].value != "OFF"]
    assert shift_cells and shift_cells[0][7].number_format == "HH:mm"


def test_tables_and_kpi(cfg):
    swi, r, issues = _run(cfg)
    sched = build_schedule(r, swi.shift_codes, cfg)
    cov = build_slot_coverage(swi, r, cfg)
    assert set(["store_id", "date", "slot", "forecast_tc", "is_peak", "labor_hours", "required_staff", "scheduled_staff",
                "scheduled_manager", "staff_gap", "manager_gap", "overstaff", "status"]) <= set(cov.columns)
    assert len(cov) == 7 * 15
    daily = build_daily_kpi(swi, r, cov)
    assert len(daily) == 7 and (daily["status"] == "OPEN").all()
    assert daily["tcph"].notna().all()
    kpi = compute_kpi(cov, sched, daily, swi.store, issues)
    assert kpi.planning_status in ("HEALTHY", "ATTENTION", "CRITICAL")
    assert 0 < kpi.coverage_pct <= 100 and kpi.manager_coverage_pct == 100
    grid = roster_grid(r, cfg)
    assert len(grid) == len(swi.employees) and grid.columns[5].startswith("Mon")
