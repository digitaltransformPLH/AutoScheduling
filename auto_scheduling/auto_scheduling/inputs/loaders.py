"""Input contracts + fail-fast validation (SPEC Section 2).

Every loader accepts a path (csv / parquet / xlsx) or a DataFrame, returns clean
objects, and writes problems to an `IssueLog`. Severity CRITICAL = the spec's
"error": the affected store cannot be scheduled.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, VALID_LABOR_GROUPS
from ..issues import IssueLog
from ..models import MANAGER_RANK, BusyBlock, Employee, StoreParams
from ..timeutil import DAY_MINUTES, WEEKDAYS, norm_text, parse_hhmm, parse_weekday

Source = str | Path | pd.DataFrame

INACTIVE_STATUSES = {"inactive", "terminated", "resigned", "nghiviec", "danghiviec", "off"}


# --------------------------------------------------------------------------- utils
def read_table(source: Source) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        p = Path(source)
        suffix = p.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(p)
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(p, dtype=str)
        else:
            df = pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def norm_id(value) -> str:
    """'2001', 2001, 2001.0, ' 2001 ' -> '2001'."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return "" if s.lower() in ("nan", "none") else s


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip() in ("", "nan", "None")


def _to_bool(v) -> bool:
    return norm_text(v) in ("1", "true", "yes", "y", "x", "co")


def _to_float(v) -> float | None:
    if _blank(v):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


# --------------------------------------------------------------------------- employees
def classify_position(position: str) -> tuple[str, bool, int | None, bool]:
    """-> (position_display, is_manager, manager_rank, can_act_as_manager). SPEC 4.1 / demo U.pos."""
    r = norm_text(position)
    if "baristatrainer" in r:
        return "Barista Trainer", False, None, True
    if "assistantstoremanager" in r or r in ("asm",):
        disp = "Assistant Store Manager"
    elif "shiftsupervisor" in r or r in ("ss",):
        disp = "Shift Supervisor"
    elif "storemanager" in r or "quanly" in r or "manager" in r or r in ("ql", "sm"):
        disp = "Store Manager"
    else:
        return "Crew Member", False, None, False
    return disp, True, MANAGER_RANK[disp], False


def parse_employment_type(v) -> str | None:
    r = norm_text(v)
    if r in ("pt", "parttime") or "part" in r:
        return "PT"
    if r in ("ft", "fulltime") or "full" in r:
        return "FT"
    return None


def parse_labor_group(v) -> str | None:
    r = norm_text(v)
    for g in VALID_LABOR_GROUPS:
        if r == g.lower():
            return g
    return None


def load_employees(source: Source, issues: IssueLog, store_id: str | None = None) -> list[Employee]:
    """dim_employee -> active, de-duplicated, classified employees (optionally one store)."""
    df = read_table(source)
    required = {"employee_id", "store_id", "name", "position", "employment_type", "labor_group"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"dim_employee missing columns: {sorted(missing)}")
    if "status" not in df.columns:
        df["status"] = "Active"

    df["store_id"] = df["store_id"].map(norm_id)
    if store_id is not None:
        df = df[df["store_id"] == store_id]

    out: list[Employee] = []
    seen: set[str] = set()
    for r in df.to_dict("records"):
        emp_id = norm_id(r["employee_id"])
        if not emp_id:
            issues.warning("EMPLOYEE_ID_MISSING", f"row without employee_id skipped ({r.get('name')!r})")
            continue
        if norm_text(r["status"]) in INACTIVE_STATUSES:
            continue
        if emp_id in seen:
            issues.warning("DUPLICATE_EMPLOYEE_KEY", f"duplicate employee_id {emp_id}; keeping first row", employee_id=emp_id)
            continue
        seen.add(emp_id)

        raw_group = r.get("labor_group")
        group = parse_labor_group(raw_group)
        if _blank(raw_group):
            issues.critical("LABOR_GROUP_REQUIRED", f"{emp_id} {r['name']}: labor_group is required", employee_id=emp_id, store_id=r["store_id"])
            continue
        if group is None:
            issues.critical("INVALID_LABOR_GROUP", f"{emp_id} {r['name']}: labor_group {raw_group!r} not in {VALID_LABOR_GROUPS}",
                            employee_id=emp_id, store_id=r["store_id"])
            continue
        emp_type = parse_employment_type(r["employment_type"])
        if emp_type is None:
            issues.critical("INVALID_EMPLOYMENT_TYPE", f"{emp_id} {r['name']}: employment_type {r['employment_type']!r} must be FT/PT",
                            employee_id=emp_id, store_id=r["store_id"])
            continue

        disp, is_mgr, rank, can_act = classify_position(r["position"])
        out.append(Employee(
            employee_id=emp_id, store_id=r["store_id"], name=str(r["name"]).strip(),
            position=str(r["position"]).strip(), position_display=disp,
            employment_type=emp_type, labor_group=group,
            is_manager=is_mgr, manager_rank=rank, can_act_as_manager=can_act,
            is_fixed=emp_type == "FT" or is_mgr,
            is_special_pt=emp_type == "PT" and group in ("Training", "NSO"),
        ))

    stores = {store_id} if store_id is not None else {e.store_id for e in out}
    for sid in stores:
        if not any(e.store_id == sid and e.counts_as_mod for e in out):
            issues.critical("NO_MANAGER", f"store {sid}: no active non-Training manager-group employee", store_id=sid)
    return out


# --------------------------------------------------------------------------- busy
def load_busy(source: Source, employees: list[Employee], issues: IssueLog, store_id: str | None = None) -> list[BusyBlock]:
    """busy exceptions -> BusyBlock list. No row = available all week.
    busy_from = busy_to = 'AL' -> annual leave (fixed employees only).
    When `store_id` is given and the table has a store_id column, other stores' rows are skipped."""
    df = read_table(source)
    missing = {"employee_id", "weekday", "busy_from", "busy_to"} - set(df.columns)
    if missing:
        raise ValueError(f"busy missing columns: {sorted(missing)}")
    if store_id is not None and "store_id" in df.columns:
        df = df[df["store_id"].map(norm_id) == store_id]
    emp_by_id = {e.employee_id: e for e in employees}
    out: list[BusyBlock] = []
    for r in df.to_dict("records"):
        emp_id = norm_id(r["employee_id"])
        emp = emp_by_id.get(emp_id)
        if emp is None:
            issues.warning("ORPHAN_AVAILABILITY_RECORD", f"busy row for unknown/inactive employee {emp_id}", employee_id=emp_id)
            continue
        wd = parse_weekday(r["weekday"])
        if wd is None:
            issues.critical("BAD_BUSY_WEEKDAY", f"{emp_id}: weekday {r['weekday']!r} not recognised", employee_id=emp_id)
            continue
        f_raw, t_raw = str(r["busy_from"]).strip(), str(r["busy_to"]).strip()
        if norm_text(f_raw) == "al" or norm_text(t_raw) == "al":
            if not emp.is_fixed:
                issues.warning("AL_FOR_NON_FIXED_IGNORED", f"{emp_id} {emp.name}: AL on {WEEKDAYS[wd]} ignored (AL is FT/manager only)",
                               employee_id=emp_id)
                continue
            out.append(BusyBlock(emp_id, wd, None, None, is_al=True))
            continue
        s, e = parse_hhmm(f_raw), parse_hhmm(t_raw)
        if s is None or e is None or e <= s:
            issues.critical("BAD_BUSY_TIME", f"{emp_id} {emp.name} {WEEKDAYS[wd]}: busy {f_raw!r}-{t_raw!r} (busy_to must be > busy_from)",
                            employee_id=emp_id)
            continue
        out.append(BusyBlock(emp_id, wd, s, min(e, DAY_MINUTES)))

    al_days: dict[str, list[int]] = {}
    for b in out:
        if b.is_al:
            al_days.setdefault(b.employee_id, []).append(b.weekday)
    for emp_id, days in al_days.items():
        if len(days) > 6:
            issues.critical("TOO_MANY_AL_DAYS", f"{emp_id}: {len(days)} AL days; at most 6 (1 OFF is never AL)", employee_id=emp_id)
    return out


# --------------------------------------------------------------------------- store
def resolve_store(store_id: str, dim_store: Source, ops_input: Source, cfg: Config, issues: IssueLog) -> StoreParams | None:
    """dim_store row + ops_input row -> StoreParams, or None (CRITICAL logged)."""
    ds = read_table(dim_store)
    ds["store_id"] = ds["store_id"].map(norm_id)
    rows = ds[ds["store_id"] == store_id]
    if rows.empty:
        issues.critical("STORE_NOT_FOUND", f"store {store_id} not in dim_store", store_id=store_id)
        return None
    r = rows.iloc[0].to_dict()
    is_24h = _to_bool(r.get("is_24h"))

    if is_24h:
        opening, closing, setup, clean = 0, DAY_MINUTES, 0, 0      # SPEC 4.5
    else:
        opening, closing = parse_hhmm(r.get("opening_time")), parse_hhmm(r.get("closing_time"))
        if opening is None or closing is None:
            issues.critical("STORE_HOURS_MISSING", f"store {store_id}: opening_time/closing_time missing or invalid "
                            f"({r.get('opening_time')!r}/{r.get('closing_time')!r})", store_id=store_id)
            return None
        if closing <= opening:
            issues.critical("STORE_HOURS_INVALID", f"store {store_id}: closing {r.get('closing_time')} <= opening {r.get('opening_time')}",
                            store_id=store_id)
            return None
        setup, clean = cfg.setup_minutes, cfg.clean_minutes          # fixed, not read from dim_store
        if opening % 60 or closing % 60:
            issues.warning("STORE_HOURS_NOT_ON_HOUR", f"store {store_id}: opening/closing not on the hour; 60-min slots only cover whole hours",
                           store_id=store_id)

    closed = frozenset(d for d, col in ((5, "closed_sat"), (6, "closed_sun")) if _to_bool(r.get(col)))

    ops = read_table(ops_input)
    ops["store_id"] = ops["store_id"].map(norm_id)
    orow = ops[ops["store_id"] == store_id]
    o = orow.iloc[0].to_dict() if not orow.empty else {}
    target = _to_float(o.get("tcph_target"))
    if target is None or target <= 0:
        issues.critical("TCPH_TARGET_MISSING", f"store {store_id}: ops_input.tcph_target missing or <= 0 (set per store by OPS)",
                        store_id=store_id)
        return None

    def _opt(col, default, cast):
        v = _to_float(o.get(col))
        return cast(v) if v is not None else default

    return StoreParams(
        store_id=store_id,
        short_name=str(r.get("short_name") or store_id).strip(),
        opening_min=opening, closing_min=closing, is_24h=is_24h,
        closed_weekdays=closed, setup_minutes=setup, clean_minutes=clean,
        tcph_target=target,
        tcph_ceiling_mult=_opt("tcph_ceiling_mult", cfg.tcph_ceiling_mult, float),
        open_staff=_opt("open_staff", cfg.open_staff, int),
        close_staff=_opt("close_staff", cfg.close_staff, int),
        min_staff_per_slot=_opt("min_staff_per_slot", cfg.min_staff_per_slot, int),
    )
