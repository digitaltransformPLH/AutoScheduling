"""P0: input contracts + validation (SPEC Section 2) and shift codes (7.3)."""
import pandas as pd
import pytest

from auto_scheduling.config import Config
from auto_scheduling.inputs.loaders import classify_position, load_busy, load_employees, resolve_store
from auto_scheduling.inputs.shift_codes import load_shift_codes, repair_code
from auto_scheduling.issues import IssueLog
from auto_scheduling.timeutil import parse_hhmm, parse_weekday

from conftest import SHIFT_CODES_PATH


def emp_df(rows):
    cols = ["employee_id", "store_id", "name", "position", "employment_type", "labor_group", "status"]
    return pd.DataFrame(rows, columns=cols)


BASE = [
    ["E1", "2001", "A", "Store Manager", "FT", "Regular", "Active"],
    ["E2", "2001", "B", "Crew Member", "PT", "Regular", "Active"],
]


# ------------------------------------------------------------------ helpers
def test_parse_hhmm_variants():
    assert parse_hhmm("7:00") == 420 and parse_hhmm("07:30") == 450
    assert parse_hhmm("24:00") == 1440 and parse_hhmm("") is None and parse_hhmm("25:00") is None
    assert parse_hhmm(0.5) == 720


def test_parse_weekday_vi_en():
    assert parse_weekday("Mon") == 0 and parse_weekday("Thứ Hai") == 0 and parse_weekday("CN") == 6 and parse_weekday("T7") == 5


def test_classify_position():
    assert classify_position("Store Manager")[:3] == ("Store Manager", True, 1)
    assert classify_position("Assistant Store Manager")[:3] == ("Assistant Store Manager", True, 2)
    assert classify_position("Shift Supervisor")[:3] == ("Shift Supervisor", True, 3)
    assert classify_position("Quản lý")[1] is True and classify_position("QL")[1] is True
    bt = classify_position("Barista Trainer")
    assert bt[1] is False and bt[3] is True
    assert classify_position("Crew Member")[1] is False


# ------------------------------------------------------------------ employees
def test_employees_ok_and_classified():
    log = IssueLog()
    emps = load_employees(emp_df(BASE + [["E3", "2001", "C", "Crew Member", "PT", "NSO", "Active"]]), log, "2001")
    assert not log.has_critical()
    by = {e.employee_id: e for e in emps}
    assert by["E1"].is_fixed and by["E1"].counts_as_mod
    assert not by["E2"].is_fixed and not by["E2"].is_special_pt
    assert by["E3"].is_special_pt


@pytest.mark.parametrize("group,code", [("", "LABOR_GROUP_REQUIRED"), ("Intern", "INVALID_LABOR_GROUP")])
def test_labor_group_validation(group, code):
    log = IssueLog()
    load_employees(emp_df(BASE + [["E9", "2001", "X", "Crew Member", "PT", group, "Active"]]), log, "2001")
    assert code in log.codes("CRITICAL")


def test_inactive_excluded_and_duplicates_warned():
    log = IssueLog()
    emps = load_employees(emp_df(BASE + [["E2", "2001", "B2", "Crew Member", "PT", "Regular", "Active"],
                                         ["E4", "2001", "D", "Crew Member", "PT", "Regular", "Terminated"]]), log, "2001")
    assert [e.employee_id for e in emps] == ["E1", "E2"]
    assert "DUPLICATE_EMPLOYEE_KEY" in log.codes("WARNING")


def test_no_manager_training_manager_does_not_count():
    log = IssueLog()
    load_employees(emp_df([["E1", "2001", "A", "Shift Supervisor", "FT", "Training", "Active"],
                           ["E2", "2001", "B", "Crew Member", "PT", "Regular", "Active"]]), log, "2001")
    assert "NO_MANAGER" in log.codes("CRITICAL")


# ------------------------------------------------------------------ busy
def test_busy_rules():
    log = IssueLog()
    emps = load_employees(emp_df(BASE), log, "2001")
    busy = pd.DataFrame([
        ["E2", "Mon", "08:00", "12:00"],
        ["E2", "Tue", "12:00", "08:00"],      # bad
        ["E1", "Wed", "AL", "AL"],            # AL fixed -> ok
        ["E2", "Thu", "AL", "AL"],            # AL for PT -> ignored
        ["E404", "Fri", "08:00", "10:00"],    # orphan
    ], columns=["employee_id", "weekday", "busy_from", "busy_to"])
    blocks = load_busy(busy, emps, log)
    assert "BAD_BUSY_TIME" in log.codes("CRITICAL")
    assert "ORPHAN_AVAILABILITY_RECORD" in log.codes("WARNING")
    assert "AL_FOR_NON_FIXED_IGNORED" in log.codes("WARNING")
    assert any(b.is_al and b.employee_id == "E1" and b.weekday == 2 for b in blocks)
    assert any(b.employee_id == "E2" and (b.start_min, b.end_min) == (480, 720) for b in blocks)


# ------------------------------------------------------------------ store
def _store_frames(**over):
    ds = {"store_id": "2001", "short_name": "S", "opening_time": "07:00", "closing_time": "22:00", "is_24h": "0",
          "closed_sat": "0", "closed_sun": "0"}
    ds.update(over)
    return pd.DataFrame([ds]), pd.DataFrame([{"store_id": "2001", "tcph_target": "8"}])


def test_resolve_store_defaults():
    ds, ops = _store_frames()
    log = IssueLog()
    s = resolve_store("2001", ds, ops, Config(), log)
    assert (s.opening_min, s.closing_min, s.setup_minutes, s.clean_minutes) == (420, 1320, 30, 30)
    assert (s.open_staff, s.close_staff, s.min_staff_per_slot, s.tcph_ceiling_mult) == (2, 2, 2, 1.05)


def test_store_hours_missing():
    ds, ops = _store_frames(opening_time="")
    log = IssueLog()
    assert resolve_store("2001", ds, ops, Config(), log) is None
    assert "STORE_HOURS_MISSING" in log.codes("CRITICAL")


def test_setup_clean_from_config_not_dim_store():
    ds, ops = _store_frames(setup_minutes="60", clean_minutes="60")   # legacy columns are ignored
    s = resolve_store("2001", ds, ops, Config(), IssueLog())
    assert (s.setup_minutes, s.clean_minutes) == (30, 30)
    s = resolve_store("2001", ds, ops, Config().with_overrides(setup_minutes=15, clean_minutes=45), IssueLog())
    assert (s.setup_minutes, s.clean_minutes) == (15, 45)


def test_24h_store_no_setup_clean():
    ds, ops = _store_frames(opening_time="", closing_time="", is_24h="1")
    s = resolve_store("2001", ds, ops, Config(), IssueLog())
    assert s.is_24h and (s.setup_minutes, s.clean_minutes, s.opening_min, s.closing_min) == (0, 0, 0, 1440)


@pytest.mark.parametrize("target", ["", "0", "-1"])
def test_tcph_target_missing(target):
    ds, _ = _store_frames()
    log = IssueLog()
    assert resolve_store("2001", ds, pd.DataFrame([{"store_id": "2001", "tcph_target": target}]), Config(), log) is None
    assert "TCPH_TARGET_MISSING" in log.codes("CRITICAL")


# ------------------------------------------------------------------ shift codes
def test_repair_code():
    assert repair_code("110") == "11E1" and repair_code("11000") == "11E3" and repair_code("110000000") == "11E7"
    assert repair_code("1100") == "11E2" and repair_code("1180") == "1180" and repair_code("11C1") == "11C1"


@pytest.mark.skipif(not SHIFT_CODES_PATH.exists(), reason="shift code csv not available")
def test_shift_code_table_real():
    log = IssueLog()
    t = load_shift_codes(SHIFT_CODES_PATH, log)
    assert len(t) == 210
    assert len(log.by_code("SHIFT_CODE_SCI_NOTATION_REPAIRED")) == 7
    assert t.lookup(420, 900) == "1180"            # AL pair 07:00-15:00
    assert t.lookup(1110, 1350) == "11E1"           # 18:30-22:30 (was '110')
    assert t.lookup(480, 960) == "1114"             # duplicate 1114/11A8 -> first
    assert t.lookup(1320, 1800) == "1125"           # overnight 22:00-06:00
    assert t.lookup(330, 810) == "11C1"             # 05:30-13:30 duplicate 11C1/11E2
    # SPEC Appendix A: all 105 shifts of a 07:00-22:00 store have a code
    starts = range(390, 1110 + 1, 30)
    pairs = [(s, s + h * 60) for s in starts for h in range(4, 9) if s + h * 60 <= 1350]
    assert len(pairs) == 105 and all(t.has(*p) for p in pairs)


@pytest.mark.integration
def test_db_shift_codes_match_hr_file():
    """dbo.dim_shift_code (seeded by migration 0005) = the HR file with the Excel-corrupted codes repaired; no repair warning."""
    from auto_scheduling.db import get_engine
    from auto_scheduling.inputs.sql_source import load_sql_shift_codes
    log = IssueLog()
    db = load_shift_codes(load_sql_shift_codes(get_engine()), log)
    file = load_shift_codes(SHIFT_CODES_PATH, IssueLog())
    assert "SHIFT_CODE_SCI_NOTATION_REPAIRED" not in log.codes()
    assert db.by_pair == file.by_pair and len(db) == len(file) == 210
    assert db.lookup(7 * 60, 15 * 60) == "1180" and db.lookup(16 * 60, 24 * 60) == "1171"       # AL / away pair, overnight to 00:00
