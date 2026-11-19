"""Store-week pipeline.

* `prepare_store_week()` - load + validate inputs and build demand (P0 + P1).
* `run_store_week()`     - pre-flight (6.0) + greedy optimizer (6.4) + validation (6.1 / 8)
                           + output tables (7.1), review workbook and File 2 (7.2).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from .calendar import StoreCalendar
from .config import DATA_DIR, REPORTS_DIR, Config
from .demand.slots import PeakWindow, build_slot_demand, daily_demand, week_peak_windows
from .inputs.availability_file import default_availability_path, load_availability_file
from .inputs.forecast import load_store_week_forecast, read_forecast
from .inputs.loaders import load_busy, load_employees, resolve_store
from .inputs.shift_codes import ShiftCodeTable, load_shift_codes
from .issues import IssueLog
from .models import BusyBlock, Employee, StoreParams
from .optimizer.greedy import optimise
from .optimizer.preflight import TemplateSet, build_templates
from .optimizer.roster import Roster
from .output.attendance import format_errors, write_attendance_file
from .output.review import write_review_workbook
from .output.tables import build_daily_kpi, build_schedule, build_slot_coverage, build_validation_issues, roster_grid
from .planning_window import can_publish, check_planning_window
from .validation.kpi import WeekKPI, compute_kpi
from .validation.rules import validate_roster


@dataclass(frozen=True)
class InputPaths:
    """File source for offline debugging (the platform reads SQL, see SqlSource): CSV/XLSX in the SPEC Section 2 layout.
    Employees + busy come from `availability_dir/Availability File {store}.xlsx`, else from dim_employee / busy."""
    dim_store: Path
    ops_input: Path
    dim_employee: Path | None = None
    busy: Path | None = None
    availability_dir: Path | None = DATA_DIR    # per-store "Availability File {store}.xlsx" (preferred when present)
    shift_codes: Path | None = None             # CSV shift_code,start,end,duration_hours (the platform uses dbo.dim_shift_code)
    forecast: Path = DATA_DIR / "forecast_tc_hourly.parquet"
    busy_semantics: str = "busy"                # see inputs.availability_file

    def employee_sources(self, store_id: str) -> tuple[object, object, str]:
        """-> (dim_employee source, busy source, description)."""
        if self.availability_dir is not None:
            p = default_availability_path(self.availability_dir, store_id)
            if p.exists():
                emp, busy = load_availability_file(p, store_id, self.busy_semantics)
                return emp, busy, f"{p.name} (busy_semantics={self.busy_semantics})"
        if self.dim_employee is None or self.busy is None:
            raise FileNotFoundError(f"no Availability File for store {store_id} and no dim_employee / busy files given")
        return self.dim_employee, self.busy, f"{self.dim_employee.name} + {self.busy.name}"


@dataclass(frozen=True)
class SqlSource:
    """Read inputs from SQL Server views sched.vw_engine_* (dbo tables of the ASP.NET app).
    availability_week: busy data of that week is reused for the schedule week (back-test); None = same week."""
    conn: str | None = None
    availability_week: date | None = None


@dataclass
class StoreWeekInput:
    store: StoreParams
    calendar: StoreCalendar
    week_start: date
    employees: list[Employee]
    busy: list[BusyBlock]
    shift_codes: ShiftCodeTable
    demand: pd.DataFrame                    # slot grid with required_staff
    daily: pd.DataFrame                     # per date budget / band / feasibility
    peak_windows: list[PeakWindow] = field(default_factory=list)
    employee_source: str = ""
    availability_week: date | None = None


@dataclass
class RunResult:
    store_id: str
    week_start: date
    issues: IssueLog
    swi: StoreWeekInput | None = None
    templates: TemplateSet | None = None
    roster: Roster | None = None
    schedule: pd.DataFrame | None = None
    coverage: pd.DataFrame | None = None
    daily_kpi: pd.DataFrame | None = None
    validation_issues: pd.DataFrame | None = None
    grid: pd.DataFrame | None = None
    kpi: WeekKPI | None = None
    out_dir: Path | None = None
    files: dict[str, Path] = field(default_factory=dict)
    file2_errors: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.roster is None


def check_manager_capacity(cal: StoreCalendar, week_start: date, employees: list[Employee],
                           busy: list[BusyBlock], cfg: Config, issues: IssueLog) -> None:
    """SPEC 4.4: MOD-hours needed ~ window x open days vs 48h per manager-group employee."""
    n_open = len(cal.open_dates(week_start))
    span = 24.0 if cal.store.is_24h else cal.window_hours
    need = span * n_open
    al = {b.employee_id for b in busy if b.is_al}
    al_hours = {e: cfg.al_paid_hours * sum(1 for b in busy if b.is_al and b.employee_id == e) for e in al}
    mods = [e for e in employees if e.counts_as_mod]
    trainers = [e for e in employees if e.can_act_as_manager and e.labor_group != "Training"]
    cap_mod = sum(cfg.ft_max_weekly_hours - al_hours.get(e.employee_id, 0) for e in mods)
    cap_all = cap_mod + sum(cfg.ft_max_weekly_hours - al_hours.get(e.employee_id, 0) for e in trainers)
    if cap_all < need:
        issues.warning("INSUFFICIENT_MANAGER_CAPACITY",
                       f"MOD hours needed ~{need:.0f}h ({span:g}h x {n_open} days) but {len(mods)} manager-group "
                       f"+ {len(trainers)} Barista Trainer give at most {cap_all:.0f}h; MANAGER_GAP expected")
    elif cap_mod < need:
        issues.info("MANAGER_CAPACITY_NEEDS_TRAINER",
                    f"MOD hours needed ~{need:.0f}h; managers give {cap_mod:.0f}h, Barista Trainer fallback required")


def check_fixed_labor_vs_band(daily: pd.DataFrame, employees: list[Employee], busy: list[BusyBlock], store: StoreParams,
                              cfg: Config, issues: IssueLog) -> None:
    """Band-first sanity check: fixed employees (FT / manager) always work 6 x 8h. If that alone exceeds the
    weekly band max hours (TC / tcph_target), the band cannot be met and PT get no hours."""
    fixed = [e for e in employees if e.is_fixed]
    away_days = {e.employee_id: sum(1 for b in busy if (b.is_al or b.away_to) and b.employee_id == e.employee_id) for e in fixed}

    def local_days(e: Employee) -> int:
        if e.is_borrowed:
            return len(e.borrowed_weekdays or ())
        return cfg.ft_work_days_per_week - away_days[e.employee_id]

    fixed_hours = sum(cfg.ft_shift_hours * max(0, local_days(e)) for e in fixed)
    band_max = float(daily["band_max_hours"].sum())
    band_min = float(daily["band_min_hours"].sum())
    adtc = float(daily["adtc"].sum())
    if fixed_hours > band_max + 1e-6:
        tcph = adtc / fixed_hours if fixed_hours else float("nan")
        issues.warning("FIXED_LABOR_EXCEEDS_TCPH_BAND",
                       f"{len(fixed)} fixed employees give {fixed_hours:g}h/week before any PT, but the band allows "
                       f"{band_min:.0f}-{band_max:.0f}h (TC {adtc:.0f} / tcph {store.tcph_target:g}); weekly TCPH <= {tcph:.2f} "
                       f"even with 0 PT hours. Band-first will leave PT unused; review headcount or tcph_target")


def prepare_store_week(store_id: str, week_start: date, cfg: Config, paths: InputPaths | SqlSource = SqlSource(),
                       issues: IssueLog | None = None, now=None) -> tuple[StoreWeekInput | None, IssueLog]:
    issues = issues if issues is not None else IssueLog(store_id=store_id, week_start=week_start)

    if not check_planning_window(week_start, cfg, issues, now=now):
        return None, issues

    availability_week = None
    if isinstance(paths, SqlSource):
        from .db import get_engine
        from .inputs.sql_source import load_sql_inputs, load_sql_shift_codes

        engine = get_engine(paths.conn)
        shift_codes = load_shift_codes(load_sql_shift_codes(engine), issues)          # dbo.dim_shift_code
        sql = load_sql_inputs(engine, store_id, week_start, paths.availability_week)
        availability_week = sql.availability_week
        store = resolve_store(store_id, sql.dim_store, sql.ops, cfg, issues)
        employees = load_employees(sql.employees, issues, store_id=store_id)
        employees += borrowed_employees(sql.secondments_in, store_id, issues)
        busy = load_busy(sql.busy, employees, issues, store_id=store_id)
        busy += away_blocks(sql.secondments_out, {e.employee_id for e in employees}, issues)
        forecast_frame = read_forecast(sql.forecast) if len(sql.forecast) else None
        src_label = "SQL Server" + (f" (lịch bận tuần {availability_week})" if availability_week != week_start else "")
    else:
        if paths.shift_codes is None:
            raise ValueError("file source needs InputPaths.shift_codes (CSV); the platform reads dbo.dim_shift_code")
        shift_codes = load_shift_codes(paths.shift_codes, issues)
        store = resolve_store(store_id, paths.dim_store, paths.ops_input, cfg, issues)
        emp_src, busy_src, src_label = paths.employee_sources(store_id)
        employees = load_employees(emp_src, issues, store_id=store_id)
        busy = load_busy(busy_src, employees, issues, store_id=store_id)
        forecast_frame = read_forecast(paths.forecast)
    if store is None:
        return None, issues
    if forecast_frame is None:
        issues.critical("FORECAST_MISSING_WEEK", f"no forecast rows for store {store_id}, week_start {week_start}", store_id=store_id)
        return None, issues

    cal = StoreCalendar(store)
    fc = load_store_week_forecast(forecast_frame, cal, week_start, cfg, issues)
    if fc.empty:
        return None, issues
    demand = build_slot_demand(fc, store, cfg)
    daily = daily_demand(demand, store, issues)
    check_manager_capacity(cal, week_start, employees, busy, cfg, issues)
    check_fixed_labor_vs_band(daily, employees, busy, store, cfg, issues)

    # Returned even with CRITICAL issues (e.g. NO_MANAGER) so demand can still be inspected;
    # the optimizer must refuse to run when issues.has_critical().
    return StoreWeekInput(
        store=store, calendar=cal, week_start=week_start, employees=employees, busy=busy,
        shift_codes=shift_codes, demand=demand, daily=daily, peak_windows=week_peak_windows(demand, cfg, store.min_staff_per_slot),
        employee_source=src_label, availability_week=availability_week,
    ), issues


def borrowed_employees(secondments, store_id: str, issues: IssueLog) -> list[Employee]:
    """Employees lent to this store: they can work here only on the secondment dates."""
    from .inputs.loaders import classify_position, parse_employment_type, parse_labor_group

    out: list[Employee] = []
    for s in secondments:
        et, lg = parse_employment_type(s.employment_type), parse_labor_group(s.labor_group)
        if et is None or lg is None:
            issues.warning("SECONDMENT_EMPLOYEE_INVALID", f"{s.employee_id} {s.name}: employment_type / labor_group invalid; not added",
                           employee_id=s.employee_id)
            continue
        disp, is_mgr, rank, can_act = classify_position(s.position)
        out.append(Employee(
            employee_id=s.employee_id, store_id=store_id, name=s.name, position=s.position, position_display=disp,
            employment_type=et, labor_group=lg, is_manager=is_mgr, manager_rank=rank, can_act_as_manager=can_act,
            is_fixed=et == "FT" or is_mgr, is_special_pt=et == "PT" and lg in ("Training", "NSO"),
            home_store=s.home_store, borrowed_weekdays=frozenset(d.weekday() for d in s.dates),
        ))
        issues.info("SECONDMENT_IN", f"{s.employee_id} {s.name} (store {s.home_store}) works here on "
                    f"{', '.join(d.strftime('%a %d/%m') for d in s.dates)}", employee_id=s.employee_id)
    return out


def away_blocks(secondments, employee_ids: set[str], issues: IssueLog) -> list[BusyBlock]:
    """This store's employees lent elsewhere: away the whole day (counts as a working day for H08)."""
    out: list[BusyBlock] = []
    for s in secondments:
        if s.employee_id not in employee_ids:
            continue
        for d in s.dates:
            out.append(BusyBlock(s.employee_id, d.weekday(), None, None, away_to=s.receiving_store))
        issues.info("SECONDMENT_OUT", f"{s.employee_id} {s.name} works at store {s.receiving_store} on "
                    f"{', '.join(d.strftime('%a %d/%m') for d in s.dates)}", employee_id=s.employee_id)
    return out


def run_store_week(store_id: str, week_start: date, cfg: Config, paths: InputPaths | SqlSource = SqlSource(),
                   out_dir: Path | None = None, export_file2: bool = False, write_outputs: bool = True, now=None) -> RunResult:
    swi, issues = prepare_store_week(store_id, week_start, cfg, paths, now=now)
    res = RunResult(store_id=store_id, week_start=week_start, issues=issues, swi=swi)
    if swi is None or issues.has_critical():
        return res

    res.templates = build_templates(swi.calendar, swi.shift_codes, cfg, issues)       # 6.0
    if issues.has_critical():
        return res

    roster = optimise(swi, res.templates, cfg, issues)                                 # 6.4
    validate_roster(roster, swi.shift_codes, cfg, issues)                              # 6.1 / 8
    res.roster = roster
    res.schedule = build_schedule(roster, swi.shift_codes, cfg)                        # 7.1
    res.coverage = build_slot_coverage(swi, roster, cfg)
    res.daily_kpi = build_daily_kpi(swi, roster, res.coverage)
    res.grid = roster_grid(roster, cfg)
    res.kpi = compute_kpi(res.coverage, res.schedule, res.daily_kpi, swi.store, issues)
    res.validation_issues = build_validation_issues(issues)

    if write_outputs:
        out = out_dir or (REPORTS_DIR / f"schedule_{store_id}_{week_start:%Y%m%d}")
        out.mkdir(parents=True, exist_ok=True)
        res.out_dir = out
        for name, df in (("schedule", res.schedule), ("slot_coverage", res.coverage), ("daily_kpi", res.daily_kpi),
                         ("validation_issues", res.validation_issues), ("roster_grid", res.grid)):
            p = out / f"{name}.csv"
            df.to_csv(p, index=False, encoding="utf-8-sig")
            res.files[name] = p
        kpi_path = out / "kpi.json"
        kpi_path.write_text(json.dumps({**res.kpi.as_dict(), "recommendations": res.kpi.recommendations}, default=str, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        res.files["kpi"] = kpi_path
        res.files["review"] = write_review_workbook(out / f"review_{store_id}_{week_start:%Y%m%d}.xlsx", res.grid, res.coverage,
                                                   res.daily_kpi, res.validation_issues, res.kpi.as_dict(), res.kpi.recommendations,
                                                   res.schedule)
        if export_file2:
            if not can_publish(cfg):
                issues.warning("FILE2_EXPORT_BACKTEST", "File 2 written in back-test mode (allow_past_weeks) for review only; publishing is blocked")
            p, errs = write_attendance_file(res.schedule, swi.employees, swi.store, week_start, swi.shift_codes, cfg, out,
                                           away=res.roster.away if res.roster is not None else None)
            if p is not None:
                res.files["file2"] = p
            else:
                res.file2_errors = errs
                issues.critical("FILE2_BLOCKED", "File 2 not written: " + format_errors(errs))
            res.validation_issues = build_validation_issues(issues)
            res.validation_issues.to_csv(res.files["validation_issues"], index=False, encoding="utf-8-sig")
    return res
