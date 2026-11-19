"""Coverage evaluation per slot + daily TCPH (SPEC 5.3).

Single implementation shared by greedy, CP-SAT comparison, validation and tests.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import pandas as pd

from ..calendar import StoreCalendar
from ..models import Shift

COVERAGE_COLS = ["store_id", "date", "hour", "forecast_tc", "is_peak_forecast", "labor_hours", "required_staff",
                 "scheduled_staff", "scheduled_manager", "actual_manager", "acting_manager",
                 "staff_gap", "manager_gap", "overstaff", "status"]


def evaluate_coverage(demand: pd.DataFrame, shifts: Iterable[Shift], calendar: StoreCalendar,
                      required_manager: int = 1) -> pd.DataFrame:
    """slot_coverage table for the demand grid.

    scheduled_staff counts every labor group (MOD and NSO included).
    scheduled_manager = #manager-group (non-Training), else min(1, #Barista Trainer non-Training).
    status: MANAGER_GAP > STAFF_GAP > OVERSTAFF (scheduled > required_staff) > OK.
    Paid-leave (AL) shifts never cover slots.
    """
    staff = defaultdict(int)
    mgr = defaultdict(int)
    acting = defaultdict(int)
    for sh in shifts:
        if sh.is_paid_leave:
            continue
        for key in calendar.shift_slots(sh):
            staff[key] += 1
            if sh.labor_group != "Training":
                if sh.is_manager:
                    mgr[key] += 1
                elif sh.can_act_as_manager:
                    acting[key] += 1

    df = demand.copy()
    keys = list(zip(df["date"], df["hour"]))
    df["scheduled_staff"] = [staff.get(k, 0) for k in keys]
    df["actual_manager"] = [mgr.get(k, 0) for k in keys]
    df["acting_manager"] = [acting.get(k, 0) for k in keys]
    df["scheduled_manager"] = [m if m > 0 else min(1, a) for m, a in zip(df["actual_manager"], df["acting_manager"])]
    df["staff_gap"] = (df["required_staff"] - df["scheduled_staff"]).clip(lower=0)
    df["manager_gap"] = (required_manager - df["scheduled_manager"]).clip(lower=0)
    df["overstaff"] = (df["scheduled_staff"] - df["labor_hours"]).clip(lower=0)
    df["status"] = "OK"
    # [DECISION 13-Nov-2026] status compares whole people with the rounded need shown to users
    # (4 scheduled / 4 needed = OK). The fractional `overstaff` (scheduled - labor_hours) stays as the
    # efficiency metric used by the objective and the KPI, but no longer drives the slot status.
    df.loc[df["scheduled_staff"] > df["required_staff"], "status"] = "OVERSTAFF"
    df.loc[df["staff_gap"] > 0, "status"] = "STAFF_GAP"
    df.loc[df["manager_gap"] > 0, "status"] = "MANAGER_GAP"
    return df[[c for c in COVERAGE_COLS if c in df.columns]]


def daily_labor(shifts: Iterable[Shift]) -> pd.DataFrame:
    """Paid labor hours per start date by labor group (AL excluded)."""
    rows = defaultdict(lambda: {"labor_reg": 0.0, "labor_train": 0.0, "labor_nso": 0.0})
    for sh in shifts:
        if sh.is_paid_leave:
            continue
        col = {"Training": "labor_train", "NSO": "labor_nso"}.get(sh.labor_group, "labor_reg")
        rows[sh.date][col] += sh.hours
    return pd.DataFrame([{"date": d, **v} for d, v in rows.items()], columns=["date", "labor_reg", "labor_train", "labor_nso"])


def daily_tcph(daily: pd.DataFrame, shifts: Iterable[Shift]) -> pd.DataFrame:
    """daily (from demand.slots.daily_demand) + labor -> tcph (NSO excluded) and tcph_nso (all hours)."""
    lab = daily_labor(shifts)
    out = daily.merge(lab, on="date", how="left").fillna({"labor_reg": 0.0, "labor_train": 0.0, "labor_nso": 0.0})
    tcph_hours = out["labor_reg"] + out["labor_train"]
    all_hours = tcph_hours + out["labor_nso"]
    out["tcph"] = (out["adtc"] / tcph_hours).where(tcph_hours > 0)
    out["tcph_nso"] = (out["adtc"] / all_hours).where(all_hours > 0)
    return out
