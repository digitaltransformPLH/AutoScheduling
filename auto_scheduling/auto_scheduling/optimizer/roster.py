"""Roster state for one store-week: shifts, OFF / AL days, availability checks (H02, H03, H17)
and per-day coverage snapshots used by the objective and the greedy steps.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from ..calendar import StoreCalendar
from ..config import Config
from ..models import BusyBlock, Employee, Shift
from ..timeutil import DAY_MINUTES, parse_hhmm, week_dates
from .preflight import FIXED, PT, SPECIAL, Template, TemplateSet


@dataclass
class DayDemand:
    date: date
    hours: list[int]                    # operating slot start hours
    required: dict[int, int]
    labor: dict[int, float]
    peak: set[int]                      # hours inside a peak window (scoring only)
    adtc: float
    band_min_hours: float
    band_max_hours: float


@dataclass
class DayState:
    """Coverage snapshot of one date computed from a list of shifts."""
    staff: dict[int, int]
    mod: dict[int, int]                 # manager-group non-Training
    acting: dict[int, int]              # Barista Trainer non-Training
    openers: int = 0
    closers: int = 0
    hours_reg: float = 0.0
    hours_train: float = 0.0
    hours_nso: float = 0.0
    short_pt: int = 0
    n_shifts: int = 0

    def scheduled_manager(self, h: int) -> int:
        m = self.mod.get(h, 0)
        return m if m > 0 else min(1, self.acting.get(h, 0))


class Roster:
    def __init__(self, employees: list[Employee], busy: list[BusyBlock], cal: StoreCalendar, week_start: date,
                 templates: TemplateSet, cfg: Config):
        self.cal = cal
        self.store = cal.store
        self.cfg = cfg
        self.week_start = week_start
        self.dates = week_dates(week_start)
        self.open_dates = cal.open_dates(week_start)
        self.templates = templates
        self.emps: dict[str, Employee] = {e.employee_id: e for e in employees}
        self.shifts: dict[tuple[str, date], Shift] = {}
        self.locked: set[tuple[str, date]] = set()
        self.off: dict[str, set[date]] = defaultdict(set)
        self.forced_off: dict[str, set[date]] = defaultdict(set)
        self.al: dict[str, set[date]] = defaultdict(set)
        self.busy: dict[tuple[str, int], list[BusyBlock]] = defaultdict(list)
        self.away: dict[str, dict[date, str]] = defaultdict(dict)      # secondment out: date -> receiving store
        self.not_here: dict[str, set[date]] = defaultdict(set)         # borrowed employee: dates at the home store
        for b in busy:
            if b.away_to:
                for d in self.dates:
                    if d.weekday() == b.weekday:
                        self.away[b.employee_id][d] = b.away_to
            elif b.is_al:
                for d in self.dates:
                    if d.weekday() == b.weekday:
                        self.al[b.employee_id].add(d)
            else:
                self.busy[(b.employee_id, b.weekday)].append(b)
        for e in employees:
            if e.is_borrowed:
                self.not_here[e.employee_id] = {d for d in self.dates if d.weekday() not in (e.borrowed_weekdays or frozenset())}
        self.morning_cutoff = parse_hhmm(cfg.morning_shift_cutoff) or 12 * 60
        self._state_cache: dict[date, DayState] = {}

    # ------------------------------------------------------------------ queries
    def shift_of(self, emp_id: str, d: date) -> Shift | None:
        return self.shifts.get((emp_id, d))

    def shifts_on(self, d: date) -> list[Shift]:
        return [s for (e, sd), s in self.shifts.items() if sd == d]

    def all_shifts(self) -> list[Shift]:
        return sorted(self.shifts.values(), key=lambda s: (s.date, s.start_min, s.employee_id))

    def is_locked(self, emp_id: str, d: date) -> bool:
        return (emp_id, d) in self.locked

    def weekly_hours(self, emp_id: str, paid: bool = True) -> float:
        """Hours worked here; for fixed employees `paid` adds AL days and days working at another store
        (secondment, counted as one 8h shift) so the 48h / 6-day rules see the whole week."""
        h = sum(s.hours for (e, _), s in self.shifts.items() if e == emp_id and not s.is_paid_leave)
        if paid and self.emps[emp_id].is_fixed:
            h += self.cfg.al_paid_hours * len(self.al.get(emp_id, ()))
            h += self.cfg.ft_shift_hours * len(self.away.get(emp_id, {}))
        return h

    def unavailable_all_day(self, emp_id: str, d: date) -> bool:
        return d in self.al.get(emp_id, ()) or d in self.away.get(emp_id, {}) or d in self.not_here.get(emp_id, ())

    def days_worked(self, emp_id: str) -> int:
        return sum(1 for (e, _), s in self.shifts.items() if e == emp_id and not s.is_paid_leave)

    def busy_conflict(self, emp_id: str, d: date, s: int, e: int) -> bool:
        for b in self.busy.get((emp_id, d.weekday()), ()):
            if s < b.end_min and min(e, DAY_MINUTES) > b.start_min:
                return True
        if e > DAY_MINUTES:                                   # overnight part on the next weekday
            for b in self.busy.get((emp_id, (d.weekday() + 1) % 7), ()):
                if 0 < b.end_min and (e - DAY_MINUTES) > b.start_min:
                    return True
        return False

    def night_before(self, emp_id: str, d: date) -> bool:
        prev = self.shift_of(emp_id, d - timedelta(days=1))
        return prev is not None and prev.crosses_midnight

    def available(self, emp_id: str, d: date, s: int, e: int, ignore_existing: bool = False) -> bool:
        """H02 (one shift per day), H03 (busy), OFF / AL days, H17 (24h stores)."""
        if d not in self.open_dates or d in self.off.get(emp_id, ()) or self.unavailable_all_day(emp_id, d):
            return False
        if not ignore_existing and (emp_id, d) in self.shifts:
            return False
        if self.busy_conflict(emp_id, d, s, e):
            return False
        if self.store.is_24h:
            if s < self.morning_cutoff and self.night_before(emp_id, d):
                return False
            if e > DAY_MINUTES:
                nxt = self.shift_of(emp_id, d + timedelta(days=1))
                if nxt is not None and nxt.start_min < self.morning_cutoff:
                    return False
        return True

    def template_kind(self, emp: Employee) -> str:
        if emp.is_fixed:
            return FIXED
        return SPECIAL if emp.is_special_pt else PT

    def available_templates(self, emp_id: str, d: date, kind: str | None = None, ignore_existing: bool = False) -> list[Template]:
        emp = self.emps[emp_id]
        kind = kind or self.template_kind(emp)
        return [t for t in self.templates.of_kind(kind) if self.available(emp_id, d, t.start_min, t.end_min, ignore_existing)]

    def has_fixed_window(self, emp_id: str, d: date) -> bool:
        """Any coded 8h shift that fits the busy blocks of that weekday (OFF/AL/existing ignored)."""
        return any(not self.busy_conflict(emp_id, d, t.start_min, t.end_min) for t in self.templates.fixed)

    # ------------------------------------------------------------------ mutations
    def make_shift(self, emp_id: str, d: date, s: int, e: int, tags: set[str] | None = None) -> Shift:
        emp = self.emps[emp_id]
        return Shift(employee_id=emp_id, store_id=self.store.store_id, date=d, start_min=s, end_min=e,
                     labor_group=emp.labor_group, position_display=emp.position_display, is_manager=emp.is_manager,
                     can_act_as_manager=emp.can_act_as_manager, tags=set(tags or ()))

    def add(self, emp_id: str, d: date, s: int, e: int, tags: set[str] | None = None, locked: bool = False) -> Shift:
        if (emp_id, d) in self.shifts:
            raise ValueError(f"{emp_id} already has a shift on {d}")
        tags = set(tags or ())
        if self.cal.is_opener(s):
            tags.add("OPEN")
        if self.cal.is_closer(s, e):
            tags.add("CLOSE")
        if locked:
            tags.add("LOCKED")
            self.locked.add((emp_id, d))
        sh = self.make_shift(emp_id, d, s, e, tags)
        self.shifts[(emp_id, d)] = sh
        self._state_cache.pop(d, None)
        if e > DAY_MINUTES:
            self._state_cache.pop(d + timedelta(days=1), None)
        return sh

    def remove(self, emp_id: str, d: date) -> Shift | None:
        sh = self.shifts.pop((emp_id, d), None)
        self.locked.discard((emp_id, d))
        self._state_cache.pop(d, None)
        if sh is not None and sh.end_min > DAY_MINUTES:
            self._state_cache.pop(d + timedelta(days=1), None)
        return sh

    def replace(self, emp_id: str, d: date, s: int, e: int) -> Shift:
        old = self.remove(emp_id, d)
        keep = {t for t in (old.tags if old else set()) if t not in ("OPEN", "CLOSE")}
        return self.add(emp_id, d, s, e, keep)

    # ------------------------------------------------------------------ coverage
    def day_state(self, d: date, extra: list[Shift] | None = None, without: set[tuple[str, date]] | None = None) -> DayState:
        """Coverage of date d. `extra` shifts are added and `without` keys removed hypothetically
        (no mutation), so candidate moves can be scored without touching the roster."""
        if not extra and not without and d in self._state_cache:
            return self._state_cache[d]
        shifts = [s for s in self.shifts.values() if not without or (s.employee_id, s.date) not in without]
        if extra:
            shifts = shifts + list(extra)
        st = self._compute_state(d, shifts)
        if not extra and not without:
            self._state_cache[d] = st
        return st

    def _compute_state(self, d: date, shifts: list[Shift]) -> DayState:
        st = DayState(staff=defaultdict(int), mod=defaultdict(int), acting=defaultdict(int))
        ops = set(self.cal.operating_hours)
        for sh in shifts:
            if sh.is_paid_leave:
                continue
            same_day = sh.date == d
            prev_day = sh.date == d - timedelta(days=1) and sh.end_min > DAY_MINUTES
            if not same_day and not prev_day:
                continue
            emp = self.emps.get(sh.employee_id)
            for off, h in self.cal.covered_slots(sh.start_min, sh.end_min):
                if (same_day and off == 0) or (prev_day and off == 1):
                    if h in ops:
                        st.staff[h] += 1
                        if sh.labor_group != "Training":
                            if sh.is_manager:
                                st.mod[h] += 1
                            elif sh.can_act_as_manager:
                                st.acting[h] += 1
            if same_day:
                st.n_shifts += 1
                if self.cal.is_opener(sh.start_min):
                    st.openers += 1
                if self.cal.is_closer(sh.start_min, sh.end_min):
                    st.closers += 1
                col = {"Training": "hours_train", "NSO": "hours_nso"}.get(sh.labor_group, "hours_reg")
                setattr(st, col, getattr(st, col) + sh.hours)
                if emp is not None and not emp.is_fixed and sh.hours <= self.cfg.pt_min_hours:
                    st.short_pt += 1
        return st

    def invalidate(self) -> None:
        self._state_cache.clear()
