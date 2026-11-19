"""KPI thresholds, planning status and recommendations (SPEC 8.1-8.3)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from ..issues import CRITICAL, WARNING, IssueLog

SYSTEM_DATA_CODES = frozenset({"SHIFT_CODE_SCI_NOTATION_REPAIRED"})


def utilization_status(u: float | None) -> str:
    if u is None or math.isnan(u):
        return "FAIL"
    if 0.90 <= u <= 1.05:
        return "GOOD"
    if 0.80 <= u < 0.90 or 1.05 < u <= 1.15:
        return "ATTENTION"
    return "FAIL"


def coverage_status(pct: float) -> str:
    return "PASS" if pct >= 100 - 1e-9 else "RISK" if pct >= 95 else "FAIL"


@dataclass
class WeekKPI:
    demand_labor_hours: float
    scheduled_labor_hours: float
    utilization: float | None
    utilization_status: str
    coverage_pct: float
    coverage_status: str
    manager_coverage_pct: float
    manager_coverage_status: str
    weekly_tcph: float | None
    tcph_in_band: bool
    planning_status: str
    status_label: str
    recommendations: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "recommendations"}
        return d


def compute_kpi(coverage: pd.DataFrame, schedule: pd.DataFrame, daily: pd.DataFrame, store, issues: IssueLog) -> WeekKPI:
    demand_hours = float(coverage["labor_hours"].sum())
    sched_hours = float(schedule.loc[~schedule["is_paid_leave"].astype(bool), "hours"].sum()) if len(schedule) else 0.0
    util = demand_hours / sched_hours if sched_hours > 0 else None
    req = float(coverage["required_staff"].sum())
    cov = float((coverage[["required_staff", "scheduled_staff"]].min(axis=1)).sum())
    cov_pct = 100.0 * cov / req if req else 100.0
    mgr_pct = 100.0 * float((coverage["scheduled_manager"] >= 1).mean()) if len(coverage) else 100.0
    tcph_hours = float(daily["labor_reg"].sum() + daily["labor_train"].sum()) if len(daily) else 0.0
    wk_tcph = float(daily["adtc"].sum()) / tcph_hours if tcph_hours > 0 else None
    in_band = wk_tcph is not None and store.tcph_target - 1e-9 <= wk_tcph <= store.tcph_ceiling + 1e-9

    u_st, c_st, m_st = utilization_status(util), coverage_status(cov_pct), coverage_status(mgr_pct)
    # warnings about system reference data (e.g. the shift-code CSV) say nothing about this roster
    relevant = [i for i in issues if i.code not in SYSTEM_DATA_CODES]
    has_critical = any(i.severity == CRITICAL for i in relevant)
    has_warning = any(i.severity == WARNING for i in relevant)
    if has_critical or "FAIL" in (u_st, c_st, m_st):
        status, label = "CRITICAL", "Rủi ro cao"
    elif has_warning or "ATTENTION" in (u_st,) or "RISK" in (c_st, m_st) or not in_band:
        status, label = "ATTENTION", "Cần chú ý"
    else:
        status, label = "HEALTHY", "Tốt"
    kpi = WeekKPI(demand_hours, sched_hours, util, u_st, cov_pct, c_st, mgr_pct, m_st, wk_tcph, in_band, status, label)
    kpi.recommendations = recommendations(coverage, schedule)
    return kpi


def recommendations(coverage: pd.DataFrame, schedule: pd.DataFrame, top: int = 5) -> list[dict]:
    """SPEC 8.3: gap windows, overstaff, PT fairness, short PT shifts, zero buffer. Ranked by impact."""
    recs: list[dict] = []
    for d, g in coverage.sort_values(["date", "slot"]).groupby("date"):
        # gap windows = consecutive slots with staff_gap > 0
        run: list[tuple[int, int]] = []
        for slot, gap in zip(g["slot"], g["staff_gap"]):
            if gap > 0:
                run.append((int(slot), int(gap)))
            elif run:
                recs.append(_gap_rec(d, run))
                run = []
        if run:
            recs.append(_gap_rec(d, run))
        over = float(g["overstaff"].sum())
        if over >= 2:
            recs.append({"date": d, "type": "OVERSTAFF", "impact": over,
                         "text": f"{d}: {over:.1f}h overstaff vs forecast labor; shorten / remove PT shifts"})
        buf = (g["scheduled_staff"] - g["labor_hours"]) < 0.25
        streak = 0
        for slot, b, gap in zip(g["slot"], buf, g["staff_gap"]):
            streak = streak + 1 if (b and gap == 0) else 0
            if streak == 3:
                recs.append({"date": d, "type": "ZERO_BUFFER", "impact": 1.0,
                             "text": f"{d}: >= 3 consecutive slots ending {int(slot):02d}:00 with zero buffer; one absence creates a gap"})
    if len(schedule):
        pt = schedule[(schedule["employment_type"] == "PT") & (~schedule["is_paid_leave"].astype(bool))]
        if len(pt):
            hrs = pt.groupby("employee_id")["hours"].sum()
            if len(hrs) > 1 and hrs.max() - hrs.min() >= 8:
                recs.append({"date": None, "type": "PT_FAIRNESS", "impact": float(hrs.max() - hrs.min()),
                             "text": f"PT weekly hours range {hrs.min():g}-{hrs.max():g}h (>= 8h spread); rebalance PT shifts"})
            short = int((pt["hours"] <= 4).sum())
            if short >= 4:
                recs.append({"date": None, "type": "SHORT_PT_SHIFTS", "impact": float(short),
                             "text": f"{short} PT shifts of <= 4h; merge into longer shifts"})
    recs.sort(key=lambda x: -x["impact"])
    return recs[:top]


def _gap_rec(d, run: list[tuple[int, int]]) -> dict:
    hours = len(run)
    gap_h = sum(g for _, g in run)
    s, e = run[0][0], run[-1][0] + 1
    if hours >= 8:
        text = f"{d}: {hours}h gap window {s:02d}:00-{e:02d}:00 ({gap_h} staff-h); add 1 FT or 2 PT"
    else:
        text = f"{d}: gap {s:02d}:00-{e:02d}:00 ({gap_h} staff-h); add {math.ceil(gap_h / 4)} PT shift(s)"
    return {"date": d, "type": "GAP_WINDOW", "impact": float(gap_h), "text": text}
