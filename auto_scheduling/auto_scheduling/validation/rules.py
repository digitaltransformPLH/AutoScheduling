"""Hard-rule validation of a finished roster (SPEC 6.1 H01-H17) + soft-rule reports (S04).

Every violation is logged as CRITICAL (the spec's "error") with the SPEC error code, so the
planning status (8.2) becomes CRITICAL; soft breaches are WARNING.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from ..config import Config
from ..inputs.shift_codes import ShiftCodeTable
from ..issues import IssueLog
from ..optimizer.roster import Roster
from ..timeutil import DAY_MINUTES, WEEKDAYS, fmt_hhmm


def validate_roster(r: Roster, codes: ShiftCodeTable, cfg: Config, issues: IssueLog) -> None:
    cal, store = r.cal, r.store
    emps = r.emps
    ops = cal.operating_hours

    # ---- per-shift rules: H01, H03, H04, H05, H06, H16
    for sh in r.all_shifts():
        emp = emps[sh.employee_id]
        who = f"{emp.employee_id} {emp.name} {sh.date} ({WEEKDAYS[sh.date.weekday()]}) {sh.start_hhmm}-{sh.end_hhmm}"
        ctx = dict(employee_id=emp.employee_id, date=sh.date)
        if not cal.inside_window(sh.start_min, sh.end_min):
            code = "INVALID_OPEN_SHIFT_START" if sh.start_min < cal.setup_start else "INVALID_SHIFT_AFTER_CLEAN_END"
            issues.critical(code, f"H01 {who}: outside window {fmt_hhmm(cal.setup_start)}-{fmt_hhmm(cal.clean_end)}", **ctx)
        if r.busy_conflict(emp.employee_id, sh.date, sh.start_min, sh.end_min):
            issues.critical("EMPLOYEE_BUSY_CONFLICT", f"H03 {who}: overlaps a busy block", **ctx)
        if sh.date in r.al.get(emp.employee_id, ()):
            issues.critical("EMPLOYEE_BUSY_CONFLICT", f"H03 {who}: shift on an AL day", **ctx)
        if sh.date in r.away.get(emp.employee_id, {}) or sh.date in r.not_here.get(emp.employee_id, ()):
            issues.critical("EMPLOYEE_BUSY_CONFLICT", f"H03 {who}: employee is at another store that day (secondment)", **ctx)
        if emp.is_fixed and abs(sh.hours - cfg.ft_shift_hours) > 1e-9:
            issues.critical("INVALID_MANAGER_SHIFT_LENGTH" if emp.is_manager else "INVALID_FT_SHIFT_LENGTH",
                            f"H04 {who}: {sh.hours:g}h, fixed shift must be {cfg.ft_shift_hours}h", **ctx)
        elif emp.is_special_pt and abs(sh.hours - cfg.special_pt_hours) > 1e-9:
            issues.critical("INVALID_SPECIAL_LABOR_PT_SHIFT_LENGTH", f"H06 {who}: {sh.hours:g}h, special PT must be {cfg.special_pt_hours}h", **ctx)
        elif not emp.is_fixed and not emp.is_special_pt and (sh.hours != int(sh.hours) or not cfg.pt_min_hours <= sh.hours <= cfg.pt_max_hours):
            issues.critical("INVALID_PT_FRACTIONAL_SHIFT_LENGTH", f"H05 {who}: {sh.hours:g}h, PT must be {cfg.pt_min_hours}-{cfg.pt_max_hours} whole hours", **ctx)
        if codes.lookup(sh.start_min, sh.end_min) is None:
            issues.critical("REQUIRED_SHIFT_NO_CODE", f"H16 {who}: no shift code", **ctx)

    # ---- per-employee rules: H07, H08, H15, H06 weekly, H02
    seen_days: dict[str, set] = defaultdict(set)
    for (eid, d) in r.shifts:
        if d in seen_days[eid]:
            issues.critical("MULTIPLE_SHIFTS_PER_DAY", f"H02 {eid}: more than one shift on {d}", employee_id=eid, date=d)
        seen_days[eid].add(d)
    for eid, emp in emps.items():
        hrs = r.weekly_hours(eid)
        if emp.is_fixed and emp.is_borrowed:
            continue                                           # weekly rules are checked at the home store
        if emp.is_fixed:
            if hrs > cfg.ft_max_weekly_hours + 1e-9:
                issues.critical("WEEKLY_HOUR_LIMIT", f"H07 {eid} {emp.name}: {hrs:g} paid hours > {cfg.ft_max_weekly_hours}", employee_id=eid)
            forced = r.forced_off.get(eid, set())
            if len(forced) > 1:
                continue                                       # H15 already logged by the optimizer
            worked = {d for (e, d) in r.shifts if e == eid}
            # AL and secondment days count as working days (never the weekly OFF)
            al = set(r.al.get(eid, set())) | set(r.away.get(eid, {}))
            if len(r.open_dates) == 7:
                off_days = [d for d in r.dates if d not in worked and d not in al]
                if len(off_days) != 1 or len(worked) + len(al) != 6:
                    issues.critical("INVALID_FT_WEEKLY_RULE",
                                    f"H08 {eid} {emp.name}: {len(worked)} worked + {len(al)} AL + {len(off_days)} OFF days; expected 6 + 1 OFF",
                                    employee_id=eid)
            else:
                missing = [d for d in r.open_dates if d not in worked and d not in al]
                if missing or len(worked) > 6:
                    issues.critical("INVALID_FT_WEEKLY_RULE", f"H08 {eid} {emp.name}: must work every open day (max 6); missing {missing}",
                                    employee_id=eid)
        elif emp.is_special_pt and hrs > cfg.special_pt_weekly_max + 1e-9:
            issues.critical("INVALID_SPECIAL_LABOR_PT_SHIFT_LENGTH", f"H06 {eid} {emp.name}: {hrs:g}h > {cfg.special_pt_weekly_max}h/week", employee_id=eid)
        elif not emp.is_fixed and cfg.pt_regular_weekly_cap is not None and hrs > cfg.pt_regular_weekly_cap:
            issues.critical("WEEKLY_HOUR_LIMIT", f"{eid} {emp.name}: {hrs:g}h > PT cap {cfg.pt_regular_weekly_cap}", employee_id=eid)

    # ---- per-day rules: H09, H10, H11, H13, H12, S04
    for d in r.open_dates:
        st = r.day_state(d)
        ctx = dict(date=d)
        lab = f"{d} ({WEEKDAYS[d.weekday()]})"
        if not store.is_24h:
            if st.openers < store.open_staff:
                issues.critical("INSUFFICIENT_OPENERS", f"H09 {lab}: {st.openers} opener(s) < {store.open_staff}", **ctx)
            if st.closers < store.close_staff:
                issues.critical("INSUFFICIENT_CLOSERS", f"H09 {lab}: {st.closers} closer(s) < {store.close_staff}", **ctx)
            o, c = cal.ft_open_shift(cfg.ft_shift_hours), cal.ft_close_shift(cfg.ft_shift_hours)
            day_shifts = r.shifts_on(d)
            mgr_open = any(s.is_manager and s.labor_group != "Training" and (s.start_min, s.end_min) == o for s in day_shifts)
            mgr_close = any(s.is_manager and s.labor_group != "Training" and (s.start_min, s.end_min) == c for s in day_shifts)
            if not mgr_open:
                issues.critical("MANAGER_OPEN_GAP", f"H10 {lab}: no manager-group opener {fmt_hhmm(o[0])}-{fmt_hhmm(o[1])}", **ctx)
            if not mgr_close:
                issues.critical("MANAGER_CLOSE_GAP", f"H10 {lab}: no manager-group closer {fmt_hhmm(c[0])}-{fmt_hhmm(c[1])}", **ctx)
        no_mod = [h for h in ops if st.scheduled_manager(h) < 1]
        if no_mod:
            issues.critical("INVALID_MANAGER_COVERAGE", f"H11 {lab}: no MOD at slot(s) {', '.join(f'{h:02d}' for h in no_mod)}", slot=no_mod[0], **ctx)
        under = [h for h in ops if st.staff.get(h, 0) < store.min_staff_per_slot]
        if under:
            issues.critical("MIN_STORE_COVERAGE_VIOLATION", f"H13 {lab}: < {store.min_staff_per_slot} staff at slot(s) {', '.join(f'{h:02d}' for h in under)}",
                            slot=under[0], **ctx)
        regs = {(s.start_min, s.end_min) for s in r.shifts_on(d) if s.is_manager and s.labor_group != "Training"}
        for s in r.shifts_on(d):
            if s.is_manager and s.labor_group == "Training" and (s.start_min, s.end_min) not in regs:
                issues.critical("TRAINING_MANAGER_REGULAR_PAIR_REQUIRED", f"H12 {lab}: Training manager {s.employee_id} shift has no Regular manager pair",
                                employee_id=s.employee_id, **ctx)
        mgr_off = [e for e, emp in emps.items() if emp.counts_as_mod and d in r.off.get(e, ()) and d not in r.forced_off.get(e, ())]
        if len(mgr_off) > 1:
            issues.warning("MANAGER_GROUP_SAME_DAY_OFF_BREACH", f"S04 {lab}: {len(mgr_off)} manager-group employees OFF ({', '.join(mgr_off)})", **ctx)

    # ---- H17 (24h stores) + week boundary
    if store.is_24h:
        cutoff = r.morning_cutoff
        for (eid, d), sh in r.shifts.items():
            if sh.end_min > DAY_MINUTES:
                nxt = r.shift_of(eid, d + timedelta(days=1))
                if nxt is not None and nxt.start_min < cutoff:
                    issues.critical("MORNING_AFTER_NIGHT_SHIFT", f"H17 {eid}: night shift {d} then morning shift {nxt.date} {nxt.start_hhmm}",
                                    employee_id=eid, date=nxt.date)
        issues.warning("PREVIOUS_WEEK_OVERFLOW_MISSING", "24h store: previous week's Sunday overnight roster not available; Monday 00:00-06:00 treated as uncovered")
