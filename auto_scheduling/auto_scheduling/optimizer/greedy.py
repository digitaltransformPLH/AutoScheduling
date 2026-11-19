"""Greedy optimizer v0 (SPEC 6.4), band-first [DECISION 12-Nov-2026].

Steps (numbers follow 6.4):
 1  weekly OFF days (managers first, lowest-demand days, max 1 manager OFF/day, forced OFF from busy; AL never on the OFF)
 2  lock manager open + close shifts (H10), MOD gap-fill (4.4), pair Training managers (H12)
 3  remaining fixed (FT / manager / Barista Trainer) 8h shifts on the best window
 4  open / close headcount with PT (H09)
 5  PT gap fill: new shift for the lowest-hour PT first, then extend existing PT shifts (objective-gated => band-first)
 6-7  efficiency / balance pass on non-locked PT: shorten, remove, move, extend; accept when the objective improves,
      never below the H09 / H11 / H13 floors
 8-9  daily + weekly TCPH band report
 10 evening repair is part of the objective (S08 terms) and of steps 5 / 7
 11 weekly PT fairness swaps (S07)
 12 hard repair: >= min_staff every slot (H13)
 13 special PT (Training / NSO) 4h shifts toward 5 days / 20h (S09)
 14 validation runs in `validation.rules` after this module
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from ..config import Config
from ..issues import IssueLog
from ..models import Employee
from ..timeutil import WEEKDAYS, fmt_hhmm
from .objective import Objective
from .preflight import FIXED, PT, SPECIAL, Template, TemplateSet
from .roster import DayDemand, DayState, Roster


def build_day_demand(swi) -> dict[date, DayDemand]:
    peaks: dict[date, set[int]] = defaultdict(set)
    for w in swi.peak_windows:
        peaks[w.date].update(range(w.start_hour, w.end_hour))
    daily = swi.daily.set_index("date")
    out: dict[date, DayDemand] = {}
    for d, g in swi.demand.groupby("date"):
        g = g.sort_values("hour")
        out[d] = DayDemand(
            date=d, hours=g["hour"].tolist(),
            required={int(h): int(v) for h, v in zip(g["hour"], g["required_staff"])},
            labor={int(h): float(v) for h, v in zip(g["hour"], g["labor_hours"])},
            peak=peaks.get(d, set()), adtc=float(daily.loc[d, "adtc"]),
            band_min_hours=float(daily.loc[d, "band_min_hours"]), band_max_hours=float(daily.loc[d, "band_max_hours"]),
        )
    return out


class GreedyScheduler:
    def __init__(self, swi, templates: TemplateSet, cfg: Config, issues: IssueLog):
        self.swi = swi
        self.cfg = cfg
        self.issues = issues
        self.cal = swi.calendar
        self.store = swi.store
        self.r = Roster(swi.employees, swi.busy, swi.calendar, swi.week_start, templates, cfg)
        self.demand = build_day_demand(swi)
        self.obj = Objective(self.r, self.demand, cfg.tcph_priority)
        self.ops = self.cal.operating_hours
        self.templates = templates

    # ------------------------------------------------------------------ helpers
    def _emps(self, pred) -> list[Employee]:
        return [e for e in self.r.emps.values() if pred(e)]

    def managers(self) -> list[Employee]:
        return self._emps(lambda e: e.counts_as_mod)

    def trainers(self) -> list[Employee]:
        return self._emps(lambda e: e.can_act_as_manager and e.labor_group != "Training")

    def regular_pt(self) -> list[Employee]:
        return self._emps(lambda e: not e.is_fixed and not e.is_special_pt)

    def special_pt(self) -> list[Employee]:
        return self._emps(lambda e: e.is_special_pt)

    def by_hours(self, emps: list[Employee]) -> list[Employee]:
        return sorted(emps, key=lambda e: (self.r.weekly_hours(e.employee_id), e.employee_id))

    def covered(self, t: Template) -> list[int]:
        return [h for off, h in self.cal.covered_slots(t.start_min, t.end_min) if off == 0 and h in self.demand_hours]

    def presence(self, s: int, e: int) -> int:
        """Minutes the shift is really on the floor inside the slots it is credited with.
        Tie-break [DECISION 13-Nov-2026, option C]: the 60-min slot mapping credits 06:30-14:30 with the
        whole 14:00-15:00 slot, so it scores the same as 07:00-15:00; prefer the shift that is present for
        the full hour (480 vs 450 min) to avoid an unstaffed half hour at hand-over."""
        total = 0
        for off, h in self.cal.covered_slots(s, e):
            if h not in self.demand_hours:
                continue
            a, b = (off * 24 + h) * 60, (off * 24 + h + 1) * 60
            total += max(0, min(e, b) - max(s, a))
        return total

    @staticmethod
    def _better(delta: float, pres: int, best) -> bool:
        """best = (delta, presence, ...): lower delta wins; equal delta -> more presence wins."""
        if best is None:
            return True
        if delta < best[0] - 1e-6:
            return True
        return abs(delta - best[0]) <= 1e-6 and pres > best[1]

    @property
    def demand_hours(self) -> set[int]:
        return set(self.ops)

    def _pick_manager(self, d: date, s: int, e: int, order: str) -> str | None:
        """S06: SM -> ASM -> SS (tie: fewer weekly hours); Barista Trainer only when no manager can."""
        cands = [m for m in self.managers() if self.r.available(m.employee_id, d, s, e)]
        if cands:
            if order == "rank":
                key = lambda m: (m.manager_rank or 9, self.r.weekly_hours(m.employee_id), m.employee_id)
            else:
                key = lambda m: (self.r.weekly_hours(m.employee_id), m.manager_rank or 9, m.employee_id)
            return min(cands, key=key).employee_id
        bts = [t for t in self.trainers() if self.r.available(t.employee_id, d, s, e)]
        if bts:
            return min(bts, key=lambda t: (self.r.weekly_hours(t.employee_id), t.employee_id)).employee_id
        return None

    def _hard_ok(self, old: DayState, new: DayState) -> bool:
        """Never go below the H13 / H11 / H09 floors (or below the current level if already under)."""
        st = self.store
        for h in self.ops:
            if new.staff.get(h, 0) < min(st.min_staff_per_slot, old.staff.get(h, 0)):
                return False
            if new.scheduled_manager(h) < min(1, old.scheduled_manager(h)):
                return False
        if not st.is_24h:
            if new.openers < min(st.open_staff, old.openers) or new.closers < min(st.close_staff, old.closers):
                return False
        return True

    # ------------------------------------------------------------------ run
    def run(self) -> Roster:
        self.step1_off_days()
        self.step2_manager_open_close()
        self.step3_fixed_windows()
        self.step4_pt_open_close()
        self.step5_pt_gap_fill()
        self.step7_efficiency_pass()
        self.step9_band_report()
        self.step11_pt_fairness()
        self.step12_floor_repair()
        self.step13_special_pt()
        self.report_unfilled_gaps()
        self.r.invalidate()
        return self.r

    # ------------------------------------------------------------------ step 1
    def step1_off_days(self) -> None:
        """OFF on the day where fixed labor exceeds the TCPH band the most (band-first), tie -> lowest
        demand; managers first and at most 1 manager OFF per day (S04); forced OFF from busy blocks."""
        r = self.r
        h8 = self.cfg.ft_shift_hours
        adtc = {d: self.demand[d].adtc for d in r.open_dates}
        band_max = {d: self.demand[d].band_max_hours for d in r.open_dates}
        n_off: dict[date, int] = defaultdict(int)
        mgr_off: dict[date, int] = defaultdict(int)
        closed = [d for d in r.dates if d not in r.open_dates]
        # borrowed employees (secondment in) keep their weekly OFF at the home store: no OFF here
        fixed = sorted(self._emps(lambda e: e.is_fixed and not e.is_borrowed),
                       key=lambda e: (0 if e.counts_as_mod else 1 if e.can_act_as_manager else 2, e.manager_rank or 9, e.employee_id))
        # projected fixed labor per day while OFF days are still unassigned (everyone not on AL / away works)
        fixed_hours = {d: h8 * sum(1 for e in fixed if not r.unavailable_all_day(e.employee_id, d)) for d in r.open_dates}
        for emp in fixed:
            eid = emp.employee_id
            r.off[eid].update(closed)
            # AL and secondment days are working days elsewhere: never the weekly OFF
            cands = [d for d in r.open_dates if not r.unavailable_all_day(eid, d)]
            forced = {d for d in cands if not r.has_fixed_window(eid, d)}
            r.forced_off[eid] = forced
            for d in forced:
                fixed_hours[d] -= h8
            if len(forced) > 1:
                r.off[eid].update(forced)
                self.issues.critical(
                    "FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS",
                    f"{eid} {emp.name}: busy blocks leave no 8h shift on {len(forced)} days "
                    f"({', '.join(WEEKDAYS[d.weekday()] for d in sorted(forced))}); H15 allows at most 1 forced OFF",
                    employee_id=eid)
                for d in sorted(forced):
                    n_off[d] += 1
                continue
            chosen: date | None = None
            if forced:
                chosen = next(iter(forced))
                r.off[eid].add(chosen)
            elif len(r.open_dates) == 7 and cands:              # H08: open 7 days -> exactly 1 OFF

                def key(d: date) -> tuple:
                    overshoot = fixed_hours[d] - band_max[d]        # fixed labor above the band max -> OFF wanted here
                    mgr_pen = 1e3 if emp.counts_as_mod and mgr_off[d] else 0.0
                    return (mgr_pen - overshoot + 0.5 * n_off[d], adtc[d], d)

                chosen = min(cands, key=key)
                r.off[eid].add(chosen)
            if chosen is not None:
                n_off[chosen] += 1
                fixed_hours[chosen] -= h8
                if emp.counts_as_mod:
                    mgr_off[chosen] += 1

    # ------------------------------------------------------------------ step 2
    def step2_manager_open_close(self) -> None:
        r, cal, cfg = self.r, self.cal, self.cfg
        if not self.store.is_24h:
            o, c = cal.ft_open_shift(cfg.ft_shift_hours), cal.ft_close_shift(cfg.ft_shift_hours)
            for d in r.open_dates:
                for tag, (s, e) in (("OPEN", o), ("CLOSE", c)):
                    pick = self._pick_manager(d, s, e, order="rank")
                    if pick is not None:
                        r.add(pick, d, s, e, {tag}, locked=True)
                self._mod_gap_fill(d, cfg.max_manager_gap_fill_shifts)
        else:
            for d in r.open_dates:
                self._mod_gap_fill(d, max(cfg.max_manager_gap_fill_shifts, 3))
        self._pair_training_managers()

    def _mod_gap_fill(self, d: date, max_shifts: int) -> None:
        r = self.r
        for _ in range(max_shifts):
            st = r.day_state(d)
            uncovered = {h for h in self.ops if st.scheduled_manager(h) < 1}
            if not uncovered:
                return
            best = None
            for t in self.templates.fixed:
                cov = set(self.covered(t)) & uncovered
                if not cov:
                    continue
                pick = self._pick_manager(d, t.start_min, t.end_min, order="hours")
                if pick is None:
                    continue
                key = (len(cov), self.presence(t.start_min, t.end_min), -t.start_min)
                if best is None or key > best[0]:
                    best = (key, t, pick)
            if best is None:
                return
            _, t, pick = best
            r.add(pick, d, t.start_min, t.end_min, {"MOD_FILL"}, locked=True)

    def _pair_training_managers(self) -> None:
        r = self.r
        for emp in self._emps(lambda e: e.is_manager and e.labor_group == "Training"):
            eid = emp.employee_id
            for d in r.open_dates:
                if r.shift_of(eid, d) is not None:
                    continue
                regs = [s for s in r.shifts_on(d) if s.is_manager and s.labor_group != "Training"]
                regs.sort(key=lambda s: (s.start_min, s.employee_id))
                for s in regs:
                    if r.available(eid, d, s.start_min, s.end_min):
                        r.add(eid, d, s.start_min, s.end_min, {"PAIR"}, locked=True)
                        break

    # ------------------------------------------------------------------ step 3
    def step3_fixed_windows(self) -> None:
        r = self.r
        order = sorted(self._emps(lambda e: e.is_fixed),
                       key=lambda e: (0 if e.counts_as_mod else 1 if e.can_act_as_manager else 2, e.manager_rank or 9, e.employee_id))
        for d in r.open_dates:
            dem = self.demand[d]
            for emp in order:
                eid = emp.employee_id
                if r.shift_of(eid, d) is not None:
                    continue
                cands = r.available_templates(eid, d, FIXED)
                if not cands:
                    continue
                st = r.day_state(d)
                can_mod = emp.counts_as_mod or (emp.can_act_as_manager and emp.labor_group != "Training")

                def score(t: Template) -> tuple[float, int]:
                    s = 0.0
                    for h in self.covered(t):
                        sch = st.staff.get(h, 0)
                        if can_mod and st.scheduled_manager(h) < 1:
                            s += 160
                        s += 100 * min(1.0, max(0.0, dem.labor[h] - sch))
                        if h in dem.peak:
                            s += 20
                        s -= 30 * max(0.0, sch + 1 - dem.labor[h])
                    return (s, self.presence(t.start_min, t.end_min), -t.start_min)

                t = max(cands, key=score)
                r.add(eid, d, t.start_min, t.end_min)
        self._improve_fixed_windows()

    def _improve_fixed_windows(self) -> None:
        """Second pass of step 3: move non-locked fixed shifts to another coded 8h window while the
        objective improves (spreads FT across the day instead of stacking them in the morning)."""
        r, obj = self.r, self.obj
        for d in r.open_dates:
            for _ in range(60):
                old_st = r.day_state(d)
                best = None
                for sh in r.shifts_on(d):
                    eid = sh.employee_id
                    if not r.emps[eid].is_fixed or r.is_locked(eid, d):
                        continue
                    cur_pres = self.presence(sh.start_min, sh.end_min)
                    for t in r.available_templates(eid, d, FIXED, ignore_existing=True):
                        if (t.start_min, t.end_min) == (sh.start_min, sh.end_min):
                            continue
                        extra = [r.make_shift(eid, d, t.start_min, t.end_min)]
                        new_st = r.day_state(d, extra, {(eid, d)})
                        if not self._hard_ok(old_st, new_st):
                            continue
                        delta = obj.delta(d, extra, {(eid, d)})
                        pres = self.presence(t.start_min, t.end_min)
                        # improve the objective, or keep it equal while being present for more of the credited hours
                        if not (delta < -1e-6 or (abs(delta) <= 1e-6 and pres > cur_pres)):
                            continue
                        if self._better(delta, pres, best):
                            best = (delta, pres, eid, t)
                if best is None:
                    break
                _, _, eid, t = best
                r.replace(eid, d, t.start_min, t.end_min)

    # ------------------------------------------------------------------ step 4
    def step4_pt_open_close(self) -> None:
        r, cal, store = self.r, self.cal, self.store
        if store.is_24h:
            return
        for d in r.open_dates:
            dem = self.demand[d]
            st = r.day_state(d)
            sides = sorted([("OPEN", store.open_staff - st.openers), ("CLOSE", store.close_staff - st.closers)], key=lambda x: -x[1])
            for side, gap in sides:
                for _ in range(max(0, gap)):
                    if not self._add_anchored_pt(d, side, dem):
                        break

    def _add_anchored_pt(self, d: date, side: str, dem: DayDemand) -> bool:
        r, cal = self.r, self.cal
        st = r.day_state(d)
        for kind, emps in ((PT, self.by_hours(self.regular_pt())), (SPECIAL, self.by_hours(self.special_pt()))):
            tpls = [t for t in self.templates.of_kind(kind)
                    if (side == "OPEN" and cal.is_opener(t.start_min)) or (side == "CLOSE" and cal.is_closer(t.start_min, t.end_min))]
            for emp in emps:
                eid = emp.employee_id
                avail = [t for t in tpls if r.available(eid, d, t.start_min, t.end_min)]
                if not avail:
                    continue

                def score(t: Template) -> tuple[float, float]:
                    s = sum(1.0 if dem.required[h] - st.staff.get(h, 0) > 0 else -0.3 for h in self.covered(t))
                    return (s, -t.hours)

                t = max(avail, key=score)
                r.add(eid, d, t.start_min, t.end_min, {side})
                return True
        return False

    # ------------------------------------------------------------------ step 5
    def step5_pt_gap_fill(self) -> None:
        r, obj = self.r, self.obj
        w_unused = obj.w["unused"]
        for d in r.open_dates:
            dem = self.demand[d]
            while True:
                st = r.day_state(d)
                gaps = {h for h in self.ops if dem.required[h] - st.staff.get(h, 0) > 0}
                ds = obj.day(d)
                above_ceiling = ds.tcph is None or ds.tcph > self.store.tcph_ceiling
                if not gaps and not above_ceiling:
                    break
                accepted = False
                # (a) new shift for the lowest-hour PT first
                for emp in self.by_hours(self.regular_pt()):
                    eid = emp.employee_id
                    best = None
                    bonus = w_unused if r.weekly_hours(eid) == 0 else 0.0
                    for t in r.available_templates(eid, d, PT):
                        if gaps and not any(h in gaps for h in self.covered(t)):
                            continue
                        delta = obj.delta(d, extra=[r.make_shift(eid, d, t.start_min, t.end_min)]) - bonus
                        pres = self.presence(t.start_min, t.end_min)
                        if delta < -1e-6 and self._better(delta, pres, best):
                            best = (delta, pres, t)
                    if best is not None:
                        r.add(eid, d, best[2].start_min, best[2].end_min)
                        accepted = True
                        break
                if accepted:
                    continue
                # (b) extend an existing non-locked regular PT shift
                best = None
                for sh in r.shifts_on(d):
                    eid = sh.employee_id
                    emp = r.emps[eid]
                    if emp.is_fixed or emp.is_special_pt or r.is_locked(eid, d):
                        continue
                    for ns, ne in ((sh.start_min - 60, sh.end_min), (sh.start_min, sh.end_min + 60),
                                   (sh.start_min - 30, sh.end_min), (sh.start_min, sh.end_min + 30)):
                        t = self.templates.get(ns, ne)
                        if t is None or t.hours > self.cfg.pt_max_hours or not r.available(eid, d, ns, ne, ignore_existing=True):
                            continue
                        delta = obj.delta(d, extra=[r.make_shift(eid, d, ns, ne)], without={(eid, d)})
                        pres = self.presence(ns, ne)
                        if delta < -1e-6 and self._better(delta, pres, best):
                            best = (delta, pres, eid, t)
                if best is not None:
                    _, _, eid, t = best
                    r.replace(eid, d, t.start_min, t.end_min)
                    continue
                break

    def report_unfilled_gaps(self) -> None:
        """Final state (after steps 7-13): why remaining staff gaps were left open."""
        r, cfg = self.r, self.cfg
        for d in r.open_dates:
            dem = self.demand[d]
            st = r.day_state(d)
            gaps = {h for h in self.ops if dem.required[h] - st.staff.get(h, 0) > 0}
            if not gaps:
                continue
            gap_hours = sum(dem.required[h] - st.staff.get(h, 0) for h in gaps)
            slots = ", ".join(f"{h:02d}" for h in sorted(gaps))
            lab = f"{d} ({WEEKDAYS[d.weekday()]})"
            any_available = any(
                any(set(self.covered(t)) & gaps for t in r.available_templates(e.employee_id, d, PT))
                for e in self.regular_pt())
            hours_tcph = st.hours_reg + st.hours_train
            if any_available and hours_tcph + cfg.pt_min_hours > dem.band_max_hours + 1e-6:
                self.issues.warning(
                    "COVERAGE_SACRIFICED_FOR_TCPH_BAND",
                    f"{lab}: {gap_hours} staff-hour gap left open at slot(s) {slots} to keep TCPH >= {self.store.tcph_target:g} "
                    f"(labor {hours_tcph:g}h, band max {dem.band_max_hours:.1f}h; a {cfg.pt_min_hours}h PT shift would breach it)",
                    date=d, slot=min(gaps))
            elif any_available:
                self.issues.info("STAFF_GAP_NOT_WORTH_FILLING",
                                 f"{lab}: {gap_hours} staff-hour gap at slot(s) {slots}; no PT shift improves the objective (overstaff elsewhere)",
                                 date=d, slot=min(gaps))
            else:
                self.issues.warning("STAFF_GAP_NO_AVAILABLE_STAFF",
                                    f"{lab}: {gap_hours} staff-hour gap at slot(s) {slots}; no available PT covers them",
                                    date=d, slot=min(gaps))

    # ------------------------------------------------------------------ step 6-7
    def step7_efficiency_pass(self) -> None:
        r, obj, cfg = self.r, self.obj, self.cfg
        for d in r.open_dates:
            for _ in range(200):
                old_st = r.day_state(d)
                best = None
                for sh in r.shifts_on(d):
                    eid = sh.employee_id
                    emp = r.emps[eid]
                    if emp.is_fixed or emp.is_special_pt or r.is_locked(eid, d):
                        continue
                    moves: list[Template | None] = [None]                       # None = remove
                    s0, e0 = sh.start_min, sh.end_min
                    cur_pres = self.presence(s0, e0)
                    for ns, ne in ((s0 + 60, e0), (s0, e0 - 60), (s0 + 30, e0), (s0, e0 - 30),
                                   (s0 - 60, e0 - 60), (s0 + 60, e0 + 60), (s0 - 30, e0 - 30), (s0 + 30, e0 + 30),
                                   (s0 - 60, e0), (s0, e0 + 60)):
                        t = self.templates.get(ns, ne)
                        if t is None or not (cfg.pt_min_hours <= t.hours <= cfg.pt_max_hours):
                            continue
                        if r.available(eid, d, ns, ne, ignore_existing=True):
                            moves.append(t)
                    for t in moves:
                        extra = [r.make_shift(eid, d, t.start_min, t.end_min)] if t is not None else None
                        new_st = r.day_state(d, extra, {(eid, d)})
                        if not self._hard_ok(old_st, new_st):
                            continue
                        delta = obj.delta(d, extra, {(eid, d)})
                        if t is None and r.weekly_hours(eid) - sh.hours == 0:
                            delta += obj.w["unused"]
                        pres = 0 if t is None else self.presence(t.start_min, t.end_min)
                        # equal-objective move only to a same-length shift that is present for more of its credited hours
                        same_len_better = t is not None and abs(delta) <= 1e-6 and t.hours == sh.hours and pres > cur_pres
                        if not (delta < -1e-6 or same_len_better):
                            continue
                        if self._better(delta, pres, best):
                            best = (delta, pres, eid, t)
                if best is None:
                    break
                _, _, eid, t = best
                if t is None:
                    r.remove(eid, d)
                else:
                    r.replace(eid, d, t.start_min, t.end_min)

    # ------------------------------------------------------------------ step 8-9
    def step9_band_report(self) -> None:
        r, store = self.r, self.store
        tot_tc = tot_h = 0.0
        for d in r.open_dates:
            ds = self.obj.day(d)
            dem = self.demand[d]
            st = r.day_state(d)
            tot_tc += dem.adtc
            tot_h += st.hours_reg + st.hours_train
            if ds.tcph_out_of_band > 1e-9:
                self.issues.warning(
                    "TCPH_OUT_OF_BAND",
                    f"{d} ({WEEKDAYS[d.weekday()]}): daily TCPH {ds.tcph if ds.tcph is not None else 0:.2f} outside "
                    f"[{store.tcph_target:g}, {store.tcph_ceiling:.2f}] (labor {st.hours_reg + st.hours_train:g}h, band "
                    f"{dem.band_min_hours:.1f}-{dem.band_max_hours:.1f}h, FT alone {self._fixed_hours(d):g}h)",
                    date=d)
        if tot_h > 0:
            wk = tot_tc / tot_h
            if not (store.tcph_target - 1e-9 <= wk <= store.tcph_ceiling + 1e-9):
                self.issues.warning("TCPH_OUT_OF_BAND", f"weekly TCPH {wk:.2f} outside [{store.tcph_target:g}, {store.tcph_ceiling:.2f}]")

    def _fixed_hours(self, d: date) -> float:
        return sum(s.hours for s in self.r.shifts_on(d) if self.r.emps[s.employee_id].is_fixed and not s.is_paid_leave)

    # ------------------------------------------------------------------ step 11
    def step11_pt_fairness(self) -> None:
        r = self.r
        pts = self.regular_pt()
        if len(pts) < 2:
            return
        for _ in range(30):
            hrs = {e.employee_id: r.weekly_hours(e.employee_id) for e in pts}
            hi = max(hrs, key=lambda k: (hrs[k], k))
            lo = min(hrs, key=lambda k: (hrs[k], k))
            if hrs[hi] - hrs[lo] < 8:
                break
            moved = False
            for sh in sorted((s for (e, _), s in r.shifts.items() if e == hi and not r.is_locked(e, s.date)),
                             key=lambda s: -s.hours):
                if r.emps[lo].can_act_as_manager != r.emps[hi].can_act_as_manager:
                    break
                if r.available(lo, sh.date, sh.start_min, sh.end_min):
                    tags = {t for t in sh.tags if t != "LOCKED"}
                    r.remove(hi, sh.date)
                    r.add(lo, sh.date, sh.start_min, sh.end_min, tags)
                    moved = True
                    break
            if not moved:
                break

    # ------------------------------------------------------------------ step 12
    def step12_floor_repair(self) -> None:
        r, store = self.r, self.store
        for d in r.open_dates:
            while True:
                st = r.day_state(d)
                under = {h for h in self.ops if st.staff.get(h, 0) < store.min_staff_per_slot}
                if not under:
                    break
                best = None
                for emp in self.by_hours(self.regular_pt()) + self.by_hours(self.special_pt()):
                    eid = emp.employee_id
                    for t in r.available_templates(eid, d):
                        cov = set(self.covered(t)) & under
                        if not cov:
                            continue
                        key = (len(cov), self.presence(t.start_min, t.end_min), -t.hours)
                        if best is None or key > best[0]:
                            best = (key, eid, t)
                if best is None:
                    break
                _, eid, t = best
                r.add(eid, d, t.start_min, t.end_min, {"FLOOR"})

    # ------------------------------------------------------------------ step 13
    def step13_special_pt(self) -> None:
        r, cfg, obj = self.r, self.cfg, self.obj
        for emp in sorted(self.special_pt(), key=lambda e: e.employee_id):
            eid = emp.employee_id
            is_nso = emp.labor_group == "NSO"
            days = r.days_worked(eid)
            cand_days = [d for d in r.open_dates if r.shift_of(eid, d) is None]

            def gap_hours(d: date) -> int:
                st = r.day_state(d)
                return sum(max(0, self.demand[d].required[h] - st.staff.get(h, 0)) for h in self.ops)

            cand_days.sort(key=lambda d: (-gap_hours(d), -self.demand[d].adtc, d))
            for d in cand_days:
                if days >= cfg.special_pt_days_target or r.weekly_hours(eid) + cfg.special_pt_hours > cfg.special_pt_weekly_max:
                    break
                best = None
                for t in r.available_templates(eid, d, SPECIAL):
                    delta = obj.delta(d, extra=[r.make_shift(eid, d, t.start_min, t.end_min)])
                    if best is None or delta < best[0]:
                        best = (delta, t)
                if best is not None and (is_nso or best[0] < -1e-6):
                    r.add(eid, d, best[1].start_min, best[1].end_min)
                    days += 1
            if days < cfg.special_pt_days_target:
                self.issues.info("SPECIAL_PT_UNDER_TARGET",
                                 f"{eid} {emp.name} ({emp.labor_group} PT): {days} day(s) / {r.weekly_hours(eid):g}h, "
                                 f"target {cfg.special_pt_days_target} days / {cfg.special_pt_weekly_max}h"
                                 + ("" if is_nso else "; extra Training hours would push TCPH below the band"),
                                 employee_id=eid)


def optimise(swi, templates: TemplateSet, cfg: Config, issues: IssueLog) -> Roster:
    return GreedyScheduler(swi, templates, cfg, issues).run()
