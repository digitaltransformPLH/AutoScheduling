"""Objective (SPEC 6.3), band-first by default [DECISION 12-Nov-2026].

score = 1e8*tcph_out_of_band**2 + 1e6*manager_gap**2 + 1e4*close_gap
      + 1e4*dist_to_band_center**2 + 1e3*staff_gap**2 + 1e3*overtime**2
      + 250*evening_gap + 25*overstaff + 25*daypart_imbalance
      + 10*unused_available + 2*short_pt_shifts

Daily terms are computed per date from a `DayState`; weekly terms (overtime, unused
available staff) are added once by `week_score`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .roster import DayDemand, DayState, Roster

BAND_FIRST = {"band": 1e8, "manager_gap": 1e6, "close_gap": 1e4, "center": 1e4, "staff_gap": 1e3, "overtime": 1e3,
              "evening_gap": 250, "overstaff": 25, "imbalance": 25, "unused": 10, "short_pt": 2}
COVERAGE_FIRST = {"band": 1e5, "manager_gap": 1e8, "close_gap": 1e6, "center": 0, "staff_gap": 1e3, "overtime": 1e3,
                  "evening_gap": 250, "overstaff": 25, "imbalance": 25, "unused": 10, "short_pt": 2, "peak_gap": 1e7}


def weights(priority: str) -> dict[str, float]:
    return COVERAGE_FIRST if priority == "coverage_first" else BAND_FIRST


@dataclass
class DayScore:
    tcph: float | None
    tcph_out_of_band: float
    dist_center: float
    manager_gap: int
    staff_gap: int
    peak_gap: int
    evening_gap: int
    overstaff: float
    open_gap: int
    close_gap: int
    imbalance: float
    short_pt: int
    total: float


def day_score(dem: DayDemand, st: DayState, store, w: dict[str, float], evening_from: int) -> DayScore:
    hours_tcph = st.hours_reg + st.hours_train
    target, ceiling = store.tcph_target, store.tcph_ceiling
    if hours_tcph > 0:
        tcph = dem.adtc / hours_tcph
        out = max(0.0, target - tcph, tcph - ceiling)
        center = abs(tcph - (target + ceiling) / 2)
    else:
        tcph, out, center = None, ceiling, ceiling     # no labor at all: far outside the band
    mg = sg = pg = eg = 0
    over = 0.0
    m_req = m_cov = e_req = e_cov = 0
    for h in dem.hours:
        req, lab = dem.required[h], dem.labor[h]
        sch = st.staff.get(h, 0)
        gap = max(0, req - sch)
        sg += gap
        if h in dem.peak:
            pg += gap
        if h >= evening_from:
            eg += gap
            e_req += req
            e_cov += min(sch, req)
        else:
            m_req += req
            m_cov += min(sch, req)
        over += max(0.0, sch - lab)
        if st.scheduled_manager(h) < 1:
            mg += 1
    m_ratio = m_cov / m_req if m_req else 1.0
    e_ratio = e_cov / e_req if e_req else 1.0
    imbalance = max(0.0, (m_ratio - e_ratio - 0.05) * 100)
    open_gap = max(0, store.open_staff - st.openers) if not store.is_24h else 0
    close_gap = max(0, store.close_staff - st.closers) if not store.is_24h else 0
    total = (w["band"] * out ** 2 + w["manager_gap"] * mg ** 2 + w["close_gap"] * (close_gap + open_gap)
             + w["center"] * center ** 2 + w["staff_gap"] * sg ** 2 + w.get("peak_gap", 0) * pg ** 2
             + w["evening_gap"] * eg + w["overstaff"] * over + w["imbalance"] * imbalance + w["short_pt"] * st.short_pt)
    return DayScore(tcph, out, center, mg, sg, pg, eg, over, open_gap, close_gap, imbalance, st.short_pt, total)


class Objective:
    def __init__(self, roster: Roster, demand: dict[date, DayDemand], priority: str = "band_first"):
        self.r = roster
        self.demand = demand
        self.w = weights(priority)
        ops = roster.cal.operating_hours
        self.evening_from = ops[len(ops) // 2] if ops else 12

    def day(self, d: date, extra=None, without=None) -> DayScore:
        return day_score(self.demand[d], self.r.day_state(d, extra, without), self.r.store, self.w, self.evening_from)

    def weekly_terms(self) -> float:
        r, cfg = self.r, self.r.cfg
        overtime = sum(max(0.0, r.weekly_hours(e) - cfg.ft_max_weekly_hours) for e, emp in r.emps.items() if emp.is_fixed)
        unused = 0
        for e, emp in r.emps.items():
            if not emp.is_fixed and r.weekly_hours(e) == 0 and any(r.available_templates(e, d) for d in r.open_dates):
                unused += 1
        return self.w["overtime"] * overtime ** 2 + self.w["unused"] * unused

    def week(self) -> float:
        return sum(self.day(d).total for d in self.r.open_dates) + self.weekly_terms()

    def delta(self, d: date, extra=None, without=None) -> float:
        """Change of the daily score of `d` if `extra` were added and `without` removed."""
        return self.day(d, extra, without).total - self.day(d).total
