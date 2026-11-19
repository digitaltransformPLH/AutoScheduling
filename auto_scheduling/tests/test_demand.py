"""P1: forecast loader, time model, required headcount, coverage, planning window (SPEC 4.2-4.5, 5, 8.4, 9)."""
from datetime import date, datetime

import pandas as pd
import pytest

from auto_scheduling.calendar import StoreCalendar
from auto_scheduling.config import Config
from auto_scheduling.demand.coverage import daily_tcph, evaluate_coverage
from auto_scheduling.demand.slots import build_slot_demand, daily_demand, peak_windows, round_half_up
from auto_scheduling.inputs.forecast import load_store_week_forecast, normalise_forecast, read_forecast
from auto_scheduling.issues import IssueLog
from auto_scheduling.models import Shift
from auto_scheduling.planning_window import check_planning_window

from conftest import FORECAST_PATH, WEEK, make_forecast, make_store, requires_forecast


# ------------------------------------------------------------------ required headcount
@pytest.mark.parametrize("tc,expected", [(48, 6), (12, 2), (20, 3), (31.09, 4), (1.01, 2), (19.9, 2), (36, 5)])
def test_required_staff(tc, expected, cfg):
    store = make_store(tcph=8)
    df = pd.DataFrame({"date": [WEEK], "hour": [13], "forecast_tc": [tc]})
    assert build_slot_demand(df, store, cfg)["required_staff"].iloc[0] == expected


def test_round_half_up_not_bankers():
    assert round_half_up(2.5) == 3 and round_half_up(4.5) == 5 and round_half_up(2.49) == 2


# ------------------------------------------------------------------ forecast loader
def _load(fc, store=None, cfg=None):
    store = store or make_store()
    log = IssueLog(store_id=store.store_id, week_start=WEEK)
    out = load_store_week_forecast(normalise_forecast(fc), StoreCalendar(store), WEEK, cfg or Config(), log)
    return out, log


def test_forecast_latest_run_and_outside_hours():
    old = make_forecast(tc=99, created_at="2026-11-10 08:00")
    new = make_forecast(hours=range(6, 24), tc=10, created_at="2026-11-11 08:00")
    new.loc[new.hour.isin([22, 23]), "tc_p50"] = 5
    out, log = _load(pd.concat([old, new]))
    assert set(out["forecast_tc"]) == {10}                  # latest run only
    assert sorted(out["hour"].unique()) == list(range(7, 22))
    w = log.by_code("FORECAST_OUTSIDE_OPENING_HOURS")
    assert len(w) == 1 and w[0].severity == "INFO" and "[6, 22, 23]" in w[0].message and "%" in w[0].message
    assert "FORECAST_OUTSIDE_OPENING_HOURS" not in log.codes("WARNING")
    assert "FORECAST_MULTIPLE_RUNS" in log.codes("INFO")


def test_forecast_missing_hour_filled_zero():
    fc = make_forecast()
    fc = fc[~((fc.forecast_date == pd.Timestamp(WEEK)) & (fc.hour == 9))]
    out, log = _load(fc)
    row = out[(out.date == WEEK) & (out.hour == 9)]
    assert row["forecast_tc"].iloc[0] == 0 and row["is_missing_hour"].iloc[0]
    assert "FORECAST_MISSING_HOUR" in log.codes("WARNING")


@pytest.mark.parametrize("mutate,code", [
    (lambda fc: pd.concat([fc, fc.head(1)]), "FORECAST_DUPLICATE_KEY"),
    (lambda fc: fc.assign(tc_p50=fc.tc_p50.where(fc.index != 0, -1)), "FORECAST_NEGATIVE_TC"),
    (lambda fc: fc[fc.forecast_date != pd.Timestamp(WEEK)], "FORECAST_MISSING_DAY"),
])
def test_forecast_errors(mutate, code):
    out, log = _load(mutate(make_forecast()))
    assert out.empty and code in log.codes("CRITICAL")


def test_closed_sunday_not_required():
    store = make_store(closed_weekdays=frozenset({6}))
    fc = make_forecast()
    fc = fc[fc.forecast_date.dt.dayofweek != 6]
    out, log = _load(fc, store)
    assert not log.has_critical() and out["date"].nunique() == 6


@requires_forecast
def test_real_forecast_store_2001():
    """SPEC 9: store 2001, 2026-10-26, tcph 8: hour 13 -> 3.89 -> 4; hour 7 -> 2."""
    store = make_store(store_id="2001", tcph=8)
    log = IssueLog()
    fc = load_store_week_forecast(read_forecast(FORECAST_PATH), StoreCalendar(store), date(2026, 10, 26), Config(), log)
    d = build_slot_demand(fc, store, Config()).set_index(["date", "hour"])
    r13, r7 = d.loc[(date(2026, 10, 26), 13)], d.loc[(date(2026, 10, 26), 7)]
    assert r13["labor_hours"] == pytest.approx(3.886, abs=1e-3) and r13["required_staff"] == 4
    assert r7["required_staff"] == 2
    assert "FORECAST_OUTSIDE_OPENING_HOURS" in log.codes("INFO")      # store 2001 forecasts hour 22 (ignored)


# ------------------------------------------------------------------ time model / slot mapping
def test_window_and_slots(cal_07_22):
    assert (cal_07_22.setup_start, cal_07_22.clean_end) == (390, 1350)
    assert cal_07_22.operating_hours == list(range(7, 22)) and len(cal_07_22.operating_hours) == 15
    cal6 = StoreCalendar(make_store(opening=360))
    assert (cal6.setup_start, cal6.clean_end, len(cal6.operating_hours)) == (330, 1350, 16)


def test_slot_mapping_demo(cal_07_22):
    assert [h for _, h in cal_07_22.covered_slots(390, 870)] == list(range(7, 15))   # 06:30-14:30 -> 07..14
    assert [h for _, h in cal_07_22.covered_slots(870, 1350)] == list(range(14, 22))  # 14:30-22:30 -> 14..21
    assert cal_07_22.is_opener(390) and cal_07_22.is_closer(870, 1350)
    assert cal_07_22.ft_open_shift() == (390, 870) and cal_07_22.ft_close_shift() == (870, 1350)


def test_24h_overnight_shift():
    cal = StoreCalendar(make_store(is_24h=True))
    assert cal.operating_hours == list(range(24))
    slots = cal.covered_slots(22 * 60, 30 * 60)   # 22:00-06:00
    assert slots == [(0, 22), (0, 23)] + [(1, h) for h in range(6)]
    assert not cal.is_opener(0) and not cal.is_closer(840, 1440)


# ------------------------------------------------------------------ coverage
def _demand_one_slot(required_tc=24.0):
    store = make_store()
    df = pd.DataFrame({"store_id": store.store_id, "date": [WEEK], "hour": [10], "forecast_tc": [required_tc], "is_peak_forecast": [False]})
    return build_slot_demand(df, store, Config()), StoreCalendar(store)


def _shift(eid, mgr=False, bt=False, group="Regular", start=600, end=660, al=False):
    return Shift(eid, "T001", WEEK, start, end, labor_group=group, is_manager=mgr, can_act_as_manager=bt, is_paid_leave=al)


def test_mod_inside_required_staff():
    demand, cal = _demand_one_slot(24.0)   # 3 people
    assert demand["required_staff"].iloc[0] == 3
    ok = evaluate_coverage(demand, [_shift("M", mgr=True), _shift("A"), _shift("B")], cal).iloc[0]
    assert ok["status"] == "OK" and ok["staff_gap"] == 0 and ok["manager_gap"] == 0
    gap = evaluate_coverage(demand, [_shift("A"), _shift("B"), _shift("C")], cal).iloc[0]
    assert gap["status"] == "MANAGER_GAP"


def test_manager_rules_training_and_trainer():
    demand, cal = _demand_one_slot(16.0)
    r = evaluate_coverage(demand, [_shift("T", mgr=True, group="Training"), _shift("A")], cal).iloc[0]
    assert r["manager_gap"] == 1                      # Training manager is never MOD
    r = evaluate_coverage(demand, [_shift("BT1", bt=True), _shift("BT2", bt=True)], cal).iloc[0]
    assert r["scheduled_manager"] == 1 and r["manager_gap"] == 0   # acting capped at 1
    r = evaluate_coverage(demand, [_shift("M1", mgr=True), _shift("M2", mgr=True)], cal).iloc[0]
    assert r["scheduled_manager"] == 2 and r["status"] in ("OK", "OVERSTAFF")   # 2 MODs allowed
    r = evaluate_coverage(demand, [_shift("M1", mgr=True, al=True), _shift("A")], cal).iloc[0]
    assert r["scheduled_staff"] == 1 and r["manager_gap"] == 1      # AL never covers


def test_status_uses_rounded_need_not_fractional_labor(cal_07_22):
    # labor 3.90 -> need 4; 4 scheduled = OK (was OVERSTAFF because 4 > 3.90); 5 scheduled = OVERSTAFF
    from datetime import date
    from auto_scheduling.demand.coverage import evaluate_coverage
    from auto_scheduling.models import Shift
    d = date(2026, 11, 9)
    demand = pd.DataFrame([{"store_id": "T001", "date": d, "hour": 7, "forecast_tc": 31.2, "is_peak_forecast": False,
                            "labor_hours": 3.9, "required_staff": 4}])
    mk = lambda i, mgr=False: Shift(f"E{i}", "T001", d, 6 * 60 + 30, 14 * 60 + 30, is_manager=mgr)
    four = evaluate_coverage(demand, [mk(0, True), mk(1), mk(2), mk(3)], cal_07_22).iloc[0]
    assert four["status"] == "OK" and round(four["overstaff"], 2) == 0.1
    five = evaluate_coverage(demand, [mk(0, True), mk(1), mk(2), mk(3), mk(4)], cal_07_22).iloc[0]
    assert five["status"] == "OVERSTAFF"


def test_daily_tcph_excludes_nso_and_al():
    daily = pd.DataFrame({"date": [WEEK], "adtc": [160.0]})
    shifts = [_shift("A", start=420, end=900), _shift("B", group="Training", start=420, end=900),
              _shift("C", group="NSO", start=420, end=660), _shift("D", start=420, end=900, al=True)]
    r = daily_tcph(daily, shifts).iloc[0]
    assert r["tcph"] == pytest.approx(160 / 16) and r["tcph_nso"] == pytest.approx(160 / 20)


def test_tcph_infeasible_warning():
    store = make_store(tcph=8)
    df = pd.DataFrame({"date": [WEEK] * 15, "hour": range(7, 22), "forecast_tc": [10.0] * 15, "day_type": "NORMAL"})
    log = IssueLog()
    d = daily_demand(build_slot_demand(df, store, Config()), store, log).iloc[0]
    assert d["max_achievable_tcph"] == pytest.approx(150 / 30) and not d["target_feasible"]
    assert d["band_max_hours"] == pytest.approx(150 / 8) and d["band_min_hours"] == pytest.approx(150 / 8.4)
    assert "TCPH_TARGET_INFEASIBLE" in log.codes("WARNING")


def test_peak_window_merge_and_extend():
    hours = list(range(7, 22))
    lab = [1, 1, 3, 3, 1, 3, 1, 1, 1, 1, 1, 3, 1, 1, 1]   # peaks 9,10 | 12 | 18
    day = pd.DataFrame({"date": WEEK, "hour": hours, "labor_hours": lab, "required_staff": [max(2, round(x)) for x in lab]})
    ws = peak_windows(day, Config())
    assert [(w.start_hour, w.end_hour) for w in ws] == [(9, 13), (15, 19)]   # 9-10 + 12 merged; 18 extended to 4h
    assert ws[0].source_hours == (9, 10, 12)


# ------------------------------------------------------------------ planning window
@pytest.mark.parametrize("week,ok", [(date(2026, 11, 16), False), (date(2026, 11, 23), True), (date(2026, 11, 24), False)])
def test_planning_window(week, ok):
    now = datetime(2026, 11, 16, 9, 0)     # Monday 09:00 Asia/Ho_Chi_Minh
    assert check_planning_window(week, Config(), IssueLog(), now=now) is ok


def test_planning_window_server_tz():
    from zoneinfo import ZoneInfo
    # Sunday 20:00 UTC = Monday 03:00 in Vietnam -> current week is 16-Nov
    now = datetime(2026, 11, 15, 20, 0, tzinfo=ZoneInfo("UTC"))
    assert check_planning_window(date(2026, 11, 16), Config(), IssueLog(), now=now) is False


def test_allow_past_weeks():
    assert check_planning_window(date(2026, 10, 26), Config(allow_past_weeks=True), IssueLog()) is True
