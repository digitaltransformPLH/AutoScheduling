"""Secondment (employee lent to another store), both sides of the loan."""
from datetime import date, timedelta

import pytest
from auto_scheduling.inputs.sql_source import Secondment
from auto_scheduling.issues import IssueLog
from auto_scheduling.models import BusyBlock
from auto_scheduling.optimizer.greedy import optimise
from auto_scheduling.optimizer.preflight import build_templates
from auto_scheduling.pipeline import away_blocks, borrowed_employees
from auto_scheduling.validation.rules import validate_roster
from conftest import WEEK
from test_optimizer import make_swi, team_a


def _run(cfg, employees, extra_busy=()):
    swi, issues = make_swi(cfg, employees)
    swi.busy = list(swi.busy) + list(extra_busy)
    templates = build_templates(swi.calendar, swi.shift_codes, cfg, issues)
    r = optimise(swi, templates, cfg, issues)
    validate_roster(r, swi.shift_codes, cfg, issues)
    return swi, r, issues


def test_home_store_away_days_count_as_work_days(cfg):
    # FT2 works at store 2023 on Mon + Tue: no shift here those days, 4 shifts + 2 away + 1 OFF, 48h
    away = [BusyBlock("FT2", 0, None, None, away_to="2023"), BusyBlock("FT2", 1, None, None, away_to="2023")]
    swi, r, issues = _run(cfg, team_a(), away)
    assert r.shift_of("FT2", WEEK) is None and r.shift_of("FT2", WEEK + timedelta(days=1)) is None
    assert r.days_worked("FT2") == 4 and r.weekly_hours("FT2") == 48
    off = [d for d in r.dates if d in r.off.get("FT2", ())]
    assert len(off) == 1 and off[0] not in (WEEK, WEEK + timedelta(days=1))          # OFF never on a secondment day
    assert "INVALID_FT_WEEKLY_RULE" not in issues.codes() and "EMPLOYEE_BUSY_CONFLICT" not in issues.codes()


def test_file2_secondment_day_keeps_hours(cfg):
    # File 2: a day lent to another store is uploaded with the away shift (07:00-15:00, 1180), never OFF [DECISION 19-Nov-2026]
    from auto_scheduling.output.attendance import build_attendance_rows
    from auto_scheduling.output.tables import build_schedule
    swi, r, issues = _run(cfg, team_a(), [BusyBlock("FT2", 0, None, None, away_to="2023")])
    rows, errors = build_attendance_rows(build_schedule(r, swi.shift_codes, cfg), swi.employees, swi.store, WEEK,
                                         swi.shift_codes, cfg, away=r.away)
    assert not errors
    mon = next(x for x in rows if x[1] == "FT2" and x[4] == WEEK.strftime("%d.%m.%Y"))
    assert mon[6] == 1180 and mon[7].hour == 7 and mon[8].hour == 15


def test_receiving_store_uses_borrowed_employee_only_on_loan_days(cfg):
    loan = [WEEK + timedelta(days=2), WEEK + timedelta(days=3)]                       # Wed, Thu
    log = IssueLog()
    borrowed = borrowed_employees([Secondment("B1", "Mượn A", "Crew member", "FT", "Regular", "9999", "T001", loan)], "T001", log)
    assert borrowed[0].is_borrowed and borrowed[0].borrowed_weekdays == frozenset({2, 3}) and "SECONDMENT_IN" in log.codes("INFO")
    swi, r, issues = _run(cfg, team_a() + borrowed)
    worked = {d for (e, d) in r.shifts if e == "B1"}
    assert worked <= set(loan) and worked                                            # only on loan days, and used
    assert all(r.shift_of("B1", d) is None for d in r.dates if d not in loan)
    assert not any(i.employee_id == "B1" and i.severity == "CRITICAL" for i in issues)   # no 6-day / OFF rule here


def test_away_blocks_only_for_own_employees():
    log = IssueLog()
    s = Secondment("SM", "Quản lý", "Store Manager", "FT", "Regular", "T001", "2023", [WEEK])
    other = Secondment("X9", "Không thuộc store", "Crew member", "PT", "Regular", "T001", "2023", [WEEK])
    blocks = away_blocks([s, other], {"SM"}, log)
    assert [(b.employee_id, b.weekday, b.away_to) for b in blocks] == [("SM", 0, "2023")]


@pytest.mark.integration
def test_sql_source_reads_pilot_store():
    """Needs SCHED_SQL_CONN (real DB): run with `pytest -m integration`."""
    from auto_scheduling.db import get_engine
    from auto_scheduling.inputs.sql_source import load_sql_inputs
    sql = load_sql_inputs(get_engine(), "2184", date(2026, 11, 9), date(2026, 11, 16))
    assert len(sql.employees) == 21 and sql.dim_store.iloc[0]["opening_time"] == "06:30" and float(sql.ops.iloc[0]["tcph_target"]) == 6.08
    assert len(sql.forecast) > 0 and sql.availability_week == date(2026, 11, 16)
    assert [s.dates for s in sql.secondments_out] == [[date(2026, 11, 9), date(2026, 11, 10)]]   # 16-17/11 shifted to 09-10/11
