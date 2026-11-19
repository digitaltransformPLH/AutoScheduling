"""P2 / P3: pre-flight, greedy v0, hard-rule validation (SPEC 6.0, 6.1, 6.4, 9)."""
from datetime import timedelta

import pandas as pd
import pytest

from auto_scheduling.calendar import StoreCalendar
from auto_scheduling.demand.slots import build_slot_demand, daily_demand, week_peak_windows
from auto_scheduling.inputs.forecast import load_store_week_forecast, read_forecast
from auto_scheduling.inputs.loaders import classify_position, load_busy
from auto_scheduling.inputs.shift_codes import load_shift_codes
from auto_scheduling.issues import IssueLog
from auto_scheduling.models import Employee
from auto_scheduling.optimizer.greedy import optimise
from auto_scheduling.optimizer.preflight import build_templates
from auto_scheduling.pipeline import StoreWeekInput, check_fixed_labor_vs_band
from auto_scheduling.validation.rules import validate_roster
from conftest import SHIFT_CODES_PATH, WEEK, make_forecast, make_store


def make_emp(emp_id, position, emp_type="FT", group="Regular", store_id="T001") -> Employee:
    disp, is_mgr, rank, can_act = classify_position(position)
    return Employee(employee_id=emp_id, store_id=store_id, name=f"Emp {emp_id}", position=position, position_display=disp,
                    employment_type=emp_type, labor_group=group, is_manager=is_mgr, manager_rank=rank, can_act_as_manager=can_act,
                    is_fixed=emp_type == "FT" or is_mgr, is_special_pt=emp_type == "PT" and group in ("Training", "NSO"))


def team_a() -> list[Employee]:
    return [make_emp("SM", "Store Manager"), make_emp("ASM", "Assistant Store Manager"), make_emp("SS", "Shift Supervisor"),
            make_emp("FT1", "Crew member"), make_emp("FT2", "Crew member"),
            make_emp("PT1", "Crew member", "PT"), make_emp("PT2", "Crew member", "PT"), make_emp("PT3", "Crew member", "PT"),
            make_emp("PT4", "Crew member", "PT"),
            make_emp("NSO1", "Crew member", "PT", "NSO"), make_emp("TR1", "Crew member", "PT", "Training")]


def make_swi(cfg, employees, busy_rows=(), tc=30.0, store=None, week=WEEK) -> tuple[StoreWeekInput, IssueLog]:
    store = store or make_store()
    issues = IssueLog(store_id=store.store_id, week_start=week)
    cal = StoreCalendar(store)
    hours = range(cal.first_slot, cal.last_slot + 1)
    fc = load_store_week_forecast(read_forecast(make_forecast(store.store_id, week, hours=hours, tc=tc)), cal, week, cfg, issues)
    demand = build_slot_demand(fc, store, cfg)
    daily = daily_demand(demand, store, issues)
    busy_df = pd.DataFrame(list(busy_rows), columns=["employee_id", "weekday", "busy_from", "busy_to"])
    busy = load_busy(busy_df, employees, issues)
    codes = load_shift_codes(SHIFT_CODES_PATH)
    swi = StoreWeekInput(store=store, calendar=cal, week_start=week, employees=employees, busy=busy, shift_codes=codes,
                         demand=demand, daily=daily, peak_windows=week_peak_windows(demand, cfg, store.min_staff_per_slot))
    return swi, issues


def run(cfg, employees, busy_rows=(), tc=30.0, store=None):
    swi, issues = make_swi(cfg, employees, busy_rows, tc, store)
    templates = build_templates(swi.calendar, swi.shift_codes, cfg, issues)
    roster = optimise(swi, templates, cfg, issues)
    validate_roster(roster, swi.shift_codes, cfg, issues)
    return swi, roster, issues


# ------------------------------------------------------------------ pre-flight
def test_preflight_templates_07_22(cfg, issues):
    cal = StoreCalendar(make_store())
    ts = build_templates(cal, load_shift_codes(SHIFT_CODES_PATH), cfg, issues)
    assert ts.get(6 * 60 + 30, 14 * 60 + 30).code == "1177"          # FT open shift
    assert ts.get(14 * 60 + 30, 22 * 60 + 30).code == "1190"         # FT close shift
    assert all(t.hours == 8 for t in ts.fixed) and all(4 <= t.hours <= 8 for t in ts.pt) and all(t.hours == 4 for t in ts.special)
    assert all(cal.inside_window(t.start_min, t.end_min) for t in ts.pt)
    assert "REQUIRED_SHIFT_NO_CODE" not in issues.codes()


def test_preflight_missing_open_code_is_critical(cfg, issues):
    cal = StoreCalendar(make_store())
    raw = pd.read_csv(SHIFT_CODES_PATH, dtype=str)
    raw = raw[~((raw["start"].str.strip().isin(["06:30", "6:30"])) & (raw["end"].str.strip().isin(["14:30"])))]
    build_templates(cal, load_shift_codes(raw), cfg, issues)
    assert "REQUIRED_SHIFT_NO_CODE" in issues.codes("CRITICAL")


# ------------------------------------------------------------------ greedy + hard rules
def test_greedy_hard_rules_hold(cfg):
    busy = [("PT1", "Sun", "00:00", "24:00"), ("FT1", "Wed", "AL", "AL"), ("PT2", "Mon", "07:00", "12:00")]
    swi, r, issues = run(cfg, team_a(), busy)
    assert not issues.has_critical(), [i.message for i in issues if i.severity == "CRITICAL"]
    store, cal = swi.store, swi.calendar
    for d in r.open_dates:
        st = r.day_state(d)
        assert st.openers >= 2 and st.closers >= 2
        assert all(st.scheduled_manager(h) >= 1 for h in cal.operating_hours)
        assert all(st.staff[h] >= 2 for h in cal.operating_hours)
    # fixed employees: 6 working days + 1 OFF, <= 48 paid hours; AL -> 5 worked + AL, never on the OFF
    for e in r.emps.values():
        if e.is_fixed:
            assert r.weekly_hours(e.employee_id) <= 48
            worked = r.days_worked(e.employee_id)
            assert worked + len(r.al.get(e.employee_id, ())) == 6
    assert r.days_worked("FT1") == 5 and r.weekly_hours("FT1") == 48
    assert r.shift_of("FT1", WEEK + timedelta(days=2)) is None
    assert r.shift_of("PT1", WEEK + timedelta(days=6)) is None                 # busy all Sunday
    mon = r.shift_of("PT2", WEEK)
    assert mon is None or mon.start_min >= 12 * 60                              # busy Mon 07-12
    assert all(swi.shift_codes.has(s.start_min, s.end_min) for s in r.all_shifts())
    for s in r.all_shifts():
        emp = r.emps[s.employee_id]
        if emp.is_special_pt:
            assert s.hours == 4
    assert r.weekly_hours("NSO1") <= 20


def test_band_first_weekly_tcph_in_band(cfg):
    swi, r, issues = run(cfg, team_a(), tc=30.0)
    daily = swi.daily.set_index("date")
    in_band = 0
    for d in r.open_dates:
        st = r.day_state(d)
        tcph = daily.loc[d, "adtc"] / (st.hours_reg + st.hours_train)
        in_band += swi.store.tcph_target - 1e-9 <= tcph <= swi.store.tcph_ceiling + 1e-9
    assert in_band >= 5
    # any remaining gap is explained
    for d in r.open_dates:
        st = r.day_state(d)
        gaps = [h for h in swi.calendar.operating_hours if st.staff[h] < swi.demand[swi.demand["date"] == d].set_index("hour").loc[h, "required_staff"]]
        if gaps:
            assert any(i.date == d and i.code in ("COVERAGE_SACRIFICED_FOR_TCPH_BAND", "STAFF_GAP_NO_AVAILABLE_STAFF", "STAFF_GAP_NOT_WORTH_FILLING")
                       for i in issues)


def test_coverage_sacrificed_when_fixed_labor_fills_band(cfg):
    # 5 fixed x 8h = 40h/day; demand needs ~4/slot (60h) but band max = 450/8 = 56h -> PT added only up to the band
    swi, r, issues = run(cfg, team_a(), tc=30.0)
    hours = {d: r.day_state(d).hours_reg + r.day_state(d).hours_train for d in r.open_dates}
    assert all(h <= swi.daily.set_index("date").loc[d, "band_max_hours"] + 1e-6 for d, h in hours.items())


def test_fixed_labor_exceeds_band_warning(cfg):
    # tcph_target so high that fixed labor alone breaks the band
    store = make_store(tcph=20.0)
    emps = [make_emp("SM", "Store Manager"), make_emp("ASM", "Assistant Store Manager"), make_emp("SS", "Shift Supervisor"),
            make_emp("FT1", "Crew member"), make_emp("PT1", "Crew member", "PT"), make_emp("PT2", "Crew member", "PT")]
    swi, issues = make_swi(cfg, emps, tc=20.0, store=store)
    check_fixed_labor_vs_band(swi.daily, swi.employees, swi.busy, store, cfg, issues)
    assert "FIXED_LABOR_EXCEEDS_TCPH_BAND" in issues.codes("WARNING")


def test_h15_multiple_forced_off_is_critical(cfg):
    busy = [("FT1", wd, "07:00", "23:00") for wd in ("Mon", "Tue", "Wed")]
    swi, r, issues = run(cfg, team_a(), busy)
    h15 = issues.by_code("FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS")
    assert h15 and h15[0].employee_id == "FT1" and h15[0].severity == "CRITICAL"
    assert all(r.shift_of("FT1", WEEK + timedelta(days=i)) is None for i in range(3))


def test_single_forced_off_becomes_the_weekly_off(cfg):
    busy = [("FT2", "Fri", "07:00", "23:00")]
    swi, r, issues = run(cfg, team_a(), busy)
    assert "FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS" not in issues.codes()
    assert r.shift_of("FT2", WEEK + timedelta(days=4)) is None and r.days_worked("FT2") == 6


def test_manager_gap_fill_for_06_22_store(cfg):
    # 06:30-22:30 store: window 06:00-23:00 = 17h; open 06:00-14:00 + close 15:00-23:00 leave slot 14 without MOD
    store = make_store(opening=6 * 60 + 30, closing=22 * 60 + 30, tcph=8.0)
    # 3 manager shifts/day x 7 days = 21 > 3 managers x 6 days: a 4th manager-group employee is needed
    emps = team_a() + [make_emp("SS2", "Shift Supervisor")]
    swi, r, issues = run(cfg, emps, tc=30.0, store=store)
    for d in r.open_dates:
        st = r.day_state(d)
        assert st.scheduled_manager(14) >= 1, d
    fills = [s for s in r.all_shifts() if "MOD_FILL" in s.tags]
    assert fills and all(s.is_manager for s in fills)
    assert "INVALID_MANAGER_COVERAGE" not in issues.codes("CRITICAL")


def test_no_unstaffed_half_hour_at_handover_06_30_22_30(cfg):
    # Window 06:00-23:00: morning shifts must not all end at 14:30 while the close shift starts 15:00
    # (06:30-14:30 and 07:00-15:00 score the same under 60-min slots; tie-break picks the full-hour one).
    store = make_store(opening=6 * 60 + 30, closing=22 * 60 + 30, tcph=8.0)
    emps = team_a() + [make_emp("SS2", "Shift Supervisor")]
    swi, r, issues = run(cfg, emps, tc=30.0, store=store)
    for d in r.open_dates:
        on_floor = [s for s in r.shifts_on(d) if s.start_min <= 14 * 60 + 30 and s.end_min >= 15 * 60]
        assert on_floor, f"nobody on the floor 14:30-15:00 on {d}"


def test_training_manager_pairs_regular_manager(cfg):
    emps = team_a() + [make_emp("TM", "Shift Supervisor", "FT", "Training")]
    swi, r, issues = run(cfg, emps)
    assert "TRAINING_MANAGER_REGULAR_PAIR_REQUIRED" not in issues.codes()
    for d in r.open_dates:
        tm = r.shift_of("TM", d)
        if tm is not None:
            assert any(s.is_manager and s.labor_group != "Training" and (s.start_min, s.end_min) == (tm.start_min, tm.end_min)
                       for s in r.shifts_on(d))


def test_validation_catches_injected_violations(cfg):
    swi, r, issues = run(cfg, team_a())
    before = len(issues)
    d = r.open_dates[0]
    # remove every closer -> H09 / H10
    for s in list(r.shifts_on(d)):
        if "CLOSE" in s.tags:
            r.remove(s.employee_id, d)
    log = IssueLog()
    validate_roster(r, swi.shift_codes, cfg, log)
    codes = set(log.codes("CRITICAL"))
    assert {"INSUFFICIENT_CLOSERS", "MANAGER_CLOSE_GAP"} <= codes
    assert len(issues) == before
