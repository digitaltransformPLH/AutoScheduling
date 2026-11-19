"""Pre-flight (SPEC 6.0): candidate shift templates filtered by `dim_shift_code`.

Only shifts with an attendance code can be generated (H16). Templates are built on the
:00/:30 grid inside the store window (4.2) or on the full day for 24h stores (4.5).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..calendar import StoreCalendar
from ..config import Config
from ..inputs.shift_codes import ShiftCodeTable
from ..issues import IssueLog
from ..timeutil import DAY_MINUTES, fmt_hhmm

FIXED, PT, SPECIAL = "fixed", "pt", "special"


@dataclass(frozen=True)
class Template:
    start_min: int
    end_min: int
    kind: str                   # fixed (8h) / pt (4-8h regular PT) / special (4h Training-NSO PT)
    code: str

    @property
    def hours(self) -> float:
        return (self.end_min - self.start_min) / 60

    @property
    def label(self) -> str:
        return f"{fmt_hhmm(self.start_min)}-{fmt_hhmm(self.end_min)}"


@dataclass
class TemplateSet:
    fixed: list[Template] = field(default_factory=list)
    pt: list[Template] = field(default_factory=list)
    special: list[Template] = field(default_factory=list)
    dropped: list[tuple[int, int]] = field(default_factory=list)
    by_pair: dict[tuple[int, int], Template] = field(default_factory=dict)

    def of_kind(self, kind: str) -> list[Template]:
        return {FIXED: self.fixed, PT: self.pt, SPECIAL: self.special}[kind]

    def get(self, start_min: int, end_min: int, kind: str | None = None) -> Template | None:
        t = self.by_pair.get((int(start_min), int(end_min)))
        if t is None or (kind is not None and t.kind != kind and not (kind == PT and t.hours in (4, 5, 6, 7, 8))):
            return None
        return t

    def __len__(self) -> int:
        return len(self.fixed) + len(self.pt) + len(self.special)


def build_templates(cal: StoreCalendar, codes: ShiftCodeTable, cfg: Config, issues: IssueLog) -> TemplateSet:
    """SPEC 6.0 steps 1-3. REQUIRED_SHIFT_NO_CODE (CRITICAL) when the FT open / close shift or a
    MOD gap-fill 8h template has no code; dropped templates are logged once (INFO)."""
    store = cal.store
    ts = TemplateSet()
    if store.is_24h:
        starts = range(0, DAY_MINUTES, 30)
        lo, hi = 0, DAY_MINUTES * 2
    else:
        lo, hi = cal.setup_start, cal.clean_end
        starts = range(lo, hi, 30)

    def _add(kind: str, s: int, e: int) -> Template | None:
        if e <= s or e > hi or (not store.is_24h and s < lo):
            return None
        code = codes.lookup(s, e)
        if code is None:
            ts.dropped.append((s, e))
            return None
        t = Template(s, e, kind, code)
        ts.of_kind(kind).append(t)
        ts.by_pair.setdefault((s, e), t)
        return t

    seen: set[tuple[int, int]] = set()
    for s in starts:
        for h in range(cfg.pt_min_hours, cfg.pt_max_hours + 1):
            e = s + h * 60
            if (s, e) in seen:
                continue
            seen.add((s, e))
            if h == cfg.ft_shift_hours:
                _add(FIXED, s, e)
            if cfg.pt_min_hours <= h <= cfg.pt_max_hours:
                _add(PT, s, e)
            if h == cfg.special_pt_hours:
                _add(SPECIAL, s, e)
    ts.dropped = sorted(set(ts.dropped))

    if ts.dropped:
        sample = ", ".join(f"{fmt_hhmm(s)}-{fmt_hhmm(e)}" for s, e in ts.dropped[:8])
        issues.info("SHIFT_TEMPLATE_NO_CODE", f"{len(ts.dropped)} candidate shift(s) have no code in dim_shift_code and are not used, e.g. {sample}")

    if not store.is_24h:
        for label, (s, e) in (("FT open shift", cal.ft_open_shift(cfg.ft_shift_hours)), ("FT close shift", cal.ft_close_shift(cfg.ft_shift_hours))):
            if codes.lookup(s, e) is None:
                issues.critical("REQUIRED_SHIFT_NO_CODE", f"{label} {fmt_hhmm(s)}-{fmt_hhmm(e)} has no code in dim_shift_code; store-week cannot be scheduled")
        # MOD gap between open and close shift must be coverable by some coded 8h template
        os_, oe = cal.ft_open_shift(cfg.ft_shift_hours)
        cs, ce = cal.ft_close_shift(cfg.ft_shift_hours)
        covered = {h for _, h in cal.covered_slots(os_, oe)} | {h for _, h in cal.covered_slots(cs, ce)}
        for h in cal.operating_hours:
            if h not in covered and not any((0, h) in cal.covered_slots(t.start_min, t.end_min) for t in ts.fixed):
                issues.critical("REQUIRED_SHIFT_NO_CODE", f"no coded 8h shift covers the MOD gap at slot {h:02d}:00 between open and close shift")
                break
    return ts
