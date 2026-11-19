"""Required headcount per slot (SPEC 5.2) + daily budget, feasibility, peak windows."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from ..config import Config
from ..issues import IssueLog
from ..models import StoreParams
from ..timeutil import WEEKDAYS


def round_half_up(x: float) -> int:
    """Demo rounding: floor if frac < 0.5 else ceil (2.5 -> 3). Never use round() (banker's)."""
    f = math.floor(x)
    return f if x - f < 0.5 else math.ceil(x)


def build_slot_demand(fc_slots: pd.DataFrame, store: StoreParams, cfg: Config) -> pd.DataFrame:
    """Add labor_hours / required_staff / required_manager / is_peak_candidate.

    60-min slot => labor hours == people. MOD is INSIDE required_staff (3 = 1 MOD + 2 staff).
    """
    df = fc_slots.copy()
    df["labor_hours"] = df["forecast_tc"] / store.tcph_target
    df["required_staff"] = df["labor_hours"].map(round_half_up).clip(lower=store.min_staff_per_slot).astype(int)
    df["required_manager"] = cfg.required_manager_per_slot
    df["is_peak_candidate"] = df["labor_hours"] > store.min_staff_per_slot
    return df


def daily_demand(demand: pd.DataFrame, store: StoreParams, issues: IssueLog) -> pd.DataFrame:
    """Per date: ADTC, labor budget, TCPH band in hours, max achievable TCPH (2-person floor).

    Band: TCPH in [target, target*mult]  <=>  hours in [TC/(target*mult), TC/target].
    max_achievable_tcph = TC_day / (min_staff * n_slots): if target > it -> TCPH_TARGET_INFEASIBLE.
    """
    g = demand.groupby("date").agg(
        adtc=("forecast_tc", "sum"),
        n_slots=("hour", "size"),
        labor_hours_raw=("labor_hours", "sum"),
        required_staff_hours=("required_staff", "sum"),
        peak_required=("required_staff", "max"),
        day_type=("day_type", "first"),
    ).reset_index()
    g["band_min_hours"] = g["adtc"] / store.tcph_ceiling
    g["band_max_hours"] = g["adtc"] / store.tcph_target
    g["floor_hours"] = store.min_staff_per_slot * g["n_slots"]
    g["max_achievable_tcph"] = g["adtc"] / g["floor_hours"]
    g["target_feasible"] = store.tcph_target <= g["max_achievable_tcph"] + 1e-9
    for r in g[~g["target_feasible"]].itertuples():
        issues.warning(
            "TCPH_TARGET_INFEASIBLE",
            f"{r.date} ({WEEKDAYS[r.date.weekday()]}): tcph_target {store.tcph_target:g} > max achievable {r.max_achievable_tcph:.2f} "
            f"(TC {r.adtc:.0f} / floor {store.min_staff_per_slot}x{r.n_slots} slots); band cannot be met even with a perfect roster",
            date=r.date,
        )
    return g


@dataclass(frozen=True)
class PeakWindow:
    date: object
    start_hour: int          # slot start of first slot in window
    end_hour: int            # exclusive (slot end of last slot)
    source_hours: tuple[int, ...]
    max_rounded_gap: int     # max(required_staff - min_staff) over source slots

    @property
    def hours(self) -> int:
        return self.end_hour - self.start_hour


def peak_windows(day: pd.DataFrame, cfg: Config, min_staff: int | None = None) -> list[PeakWindow]:
    """Demo PeakWindowEngine (scoring only): adjacent slots with labor_hours > min_staff form a
    cluster; merge clusters if gap <= 1 slot and merged length <= pt_max_hours; extend each
    window to >= pt_min_hours (earlier first, then later)."""
    min_staff = cfg.min_staff_per_slot if min_staff is None else min_staff
    day = day.sort_values("hour").reset_index(drop=True)
    if day.empty:
        return []
    peaks = day.index[day["labor_hours"] > min_staff].tolist()
    clusters: list[list[int]] = []
    for i in peaks:
        if clusters and i == clusters[-1][-1] + 1:
            clusters[-1].append(i)
        else:
            clusters.append([i])
    merged: list[list[int]] = []
    for c in clusters:
        if merged and c[0] - merged[-1][-1] - 1 <= 1 and c[-1] - merged[-1][0] + 1 <= cfg.pt_max_hours:
            merged[-1] = merged[-1] + c
        else:
            merged.append(list(c))
    out = []
    last = len(day) - 1
    for c in merged:
        s, e = c[0], c[-1]
        while e - s + 1 < cfg.pt_min_hours:
            if s > 0:
                s -= 1
            elif e < last:
                e += 1
            else:
                break
        hours = day["hour"].tolist()
        out.append(PeakWindow(
            date=day["date"].iloc[0], start_hour=hours[s], end_hour=hours[e] + 1,
            source_hours=tuple(hours[i] for i in c),
            max_rounded_gap=int(max(day.loc[i, "required_staff"] - min_staff for i in c)),
        ))
    return out


def week_peak_windows(demand: pd.DataFrame, cfg: Config, min_staff: int | None = None) -> list[PeakWindow]:
    return [w for _, day in demand.groupby("date") for w in peak_windows(day, cfg, min_staff)]
