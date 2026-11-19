"""Output tables (SPEC 7.1): schedule, slot_coverage, daily_kpi, validation_issues."""
from __future__ import annotations

from datetime import date

import pandas as pd

from ..config import Config
from ..demand.coverage import daily_tcph, evaluate_coverage
from ..inputs.shift_codes import ShiftCodeTable
from ..issues import IssueLog
from ..models import Employee
from ..optimizer.roster import Roster
from ..timeutil import WEEKDAYS, fmt_hhmm, parse_hhmm

ROLE_ORDER = {"Store Manager": 0, "Assistant Store Manager": 1, "Shift Supervisor": 2, "Barista Trainer": 3, "Crew Member": 4}
GROUP_ORDER = {"Regular": 0, "Training": 1, "NSO": 2}
SCHEDULE_COLS = ["employee_id", "store_id", "date", "start", "end", "position", "labor_group", "is_paid_leave", "tags",
                 "name", "employment_type", "shift_code", "hours", "weekday"]


def employee_sort_key(e: Employee) -> tuple:
    """SPEC 7.2 row order: labor group -> role -> FT before PT -> name -> employee_id."""
    return (GROUP_ORDER.get(e.labor_group, 9), ROLE_ORDER.get(e.position_display, 9), 0 if e.employment_type == "FT" else 1,
            e.name, e.employee_id)


def sorted_employees(employees: list[Employee]) -> list[Employee]:
    return sorted(employees, key=employee_sort_key)


def build_schedule(r: Roster, codes: ShiftCodeTable, cfg: Config) -> pd.DataFrame:
    rows = []
    al_s, al_e = parse_hhmm(cfg.al_shift_start), parse_hhmm(cfg.al_shift_end)
    for sh in r.all_shifts():
        emp = r.emps[sh.employee_id]
        rows.append({"employee_id": emp.employee_id, "store_id": sh.store_id, "date": sh.date, "start": sh.start_hhmm, "end": sh.end_hhmm,
                     "position": emp.position_display, "labor_group": emp.labor_group, "is_paid_leave": False,
                     "tags": "|".join(sorted(sh.tags)), "name": emp.name, "employment_type": emp.employment_type,
                     "shift_code": codes.lookup(sh.start_min, sh.end_min), "hours": sh.hours, "weekday": WEEKDAYS[sh.date.weekday()]})
    for eid, days in r.al.items():
        emp = r.emps[eid]
        for d in sorted(days):
            rows.append({"employee_id": eid, "store_id": r.store.store_id, "date": d, "start": fmt_hhmm(al_s), "end": fmt_hhmm(al_e),
                         "position": emp.position_display, "labor_group": emp.labor_group, "is_paid_leave": True, "tags": "AL",
                         "name": emp.name, "employment_type": emp.employment_type, "shift_code": codes.lookup(al_s, al_e),
                         "hours": float(cfg.al_paid_hours), "weekday": WEEKDAYS[d.weekday()]})
    df = pd.DataFrame(rows, columns=SCHEDULE_COLS)
    return df.sort_values(["date", "start", "employee_id"]).reset_index(drop=True)


def build_slot_coverage(swi, r: Roster, cfg: Config) -> pd.DataFrame:
    cov = evaluate_coverage(swi.demand, r.all_shifts(), swi.calendar, cfg.required_manager_per_slot)
    cov = cov.rename(columns={"hour": "slot", "is_peak_forecast": "is_peak"})
    return cov.sort_values(["date", "slot"]).reset_index(drop=True)


def build_daily_kpi(swi, r: Roster, coverage: pd.DataFrame) -> pd.DataFrame:
    d = daily_tcph(swi.daily, r.all_shifts())
    lineage = swi.demand.groupby("date")[["forecast_run_id", "method_version"]].first().reset_index()
    d = d.merge(lineage, on="date", how="left")
    cov = coverage.groupby("date").agg(required_hours=("required_staff", "sum"), scheduled_hours=("scheduled_staff", "sum"),
                                       staff_gap_hours=("staff_gap", "sum"), manager_gap_slots=("manager_gap", "sum"),
                                       overstaff_hours=("overstaff", "sum")).reset_index()
    d = d.merge(cov, on="date", how="left")
    open_dates = set(r.open_dates)
    rows = []
    for dd in r.dates:
        if dd in open_dates:
            continue
        rows.append({"date": dd, "status": "CLOSED"})
    d["status"] = "OPEN"
    if rows:
        d = pd.concat([d, pd.DataFrame(rows)], ignore_index=True)
    d.insert(0, "store_id", r.store.store_id)
    d["weekday"] = [WEEKDAYS[x.weekday()] for x in d["date"]]
    d["tcph_in_band"] = d["tcph"].between(r.store.tcph_target - 1e-9, r.store.tcph_ceiling + 1e-9)
    for c in ("publish_id", "publish_version", "published_at"):
        d[c] = None
    cols = ["store_id", "date", "weekday", "status", "day_type", "adtc", "labor_reg", "labor_train", "labor_nso", "tcph", "tcph_nso",
            "tcph_in_band", "band_min_hours", "band_max_hours", "max_achievable_tcph", "required_hours", "scheduled_hours",
            "staff_gap_hours", "manager_gap_slots", "overstaff_hours", "forecast_run_id", "method_version",
            "publish_id", "publish_version", "published_at"]
    return d[[c for c in cols if c in d.columns]].sort_values("date").reset_index(drop=True)


def build_validation_issues(issues: IssueLog) -> pd.DataFrame:
    df = issues.to_frame()
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    df["_o"] = df["severity"].map(order)
    return df.sort_values(["_o", "code", "date"], na_position="last").drop(columns="_o").reset_index(drop=True)


def roster_grid(r: Roster, cfg: Config) -> pd.DataFrame:
    """Review grid: one row per employee, one column per day ('06:30-14:30' / 'OFF' / 'AL' / '-')."""
    rows = []
    for emp in sorted_employees(list(r.emps.values())):
        eid = emp.employee_id
        row = {"employee_id": eid, "name": emp.name, "position": emp.position_display, "type": emp.employment_type,
               "labor_group": emp.labor_group}
        for d in r.dates:
            key = f"{WEEKDAYS[d.weekday()]} {d:%d/%m}"
            sh = r.shift_of(eid, d)
            if sh is not None:
                row[key] = f"{sh.start_hhmm}-{sh.end_hhmm}" + ("*" if "LOCKED" in sh.tags else "")
            elif d in r.al.get(eid, ()):
                row[key] = "AL"
            elif d in r.away.get(eid, {}):
                row[key] = f"HT {r.away[eid][d]}"           # hỗ trợ store khác
            elif d in r.not_here.get(eid, ()):
                row[key] = "·"                               # nhân viên mượn: ngày ở store gốc
            elif d not in r.open_dates or d in r.off.get(eid, ()):
                row[key] = "OFF"
            else:
                row[key] = "-"
        row["hours"] = r.weekly_hours(eid)
        row["days"] = r.days_worked(eid)
        rows.append(row)
    return pd.DataFrame(rows)
