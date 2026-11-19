"""Load real input data into the dbo tables owned by the ASP.NET app (EF).

* dim_employee              upsert by EmployeeNumber (unique)
* employee_availability_slot replace (PlantCode, WeekStartMonday): one row per employee x day,
                             BusyFrom/BusyTo NULL = free all day (same convention as the .NET app)
* ops_store_config          upsert by dim_store.Id; optional delete of test rows

Source for employees / busy: the store "Availability File {store}.xlsx" (sheets Employee Master + Availability;
"Bận từ / Bận đến" = busy time [DECISION 13-Nov-2026]). Everything runs in one transaction per call; a DQ report
lists what changed. Idempotent: running twice gives the same rows.
"""
from __future__ import annotations

import getpass
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from ..inputs.availability_file import _AVAIL_COLS, _EMP_COLS, AVAILABILITY_SHEET, EMPLOYEE_SHEET, _blank, _rename
from ..inputs.loaders import norm_id, parse_employment_type, parse_labor_group
from ..timeutil import DAY_MINUTES, norm_text, parse_hhmm, parse_weekday

EMPLOYEE_COLS = ("FullName", "PlantCode", "Position", "EmploymentType", "LaborGroup", "Status")


@dataclass
class LoadReport:
    store: str
    week_start: date | None = None
    employees_inserted: list[str] = field(default_factory=list)
    employees_updated: list[str] = field(default_factory=list)
    employees_unchanged: int = 0
    availability_deleted: int = 0
    availability_inserted: int = 0
    busy_days: int = 0
    al_days: int = 0
    warnings: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [f"## Store {self.store}" + (f" · tuần {self.week_start}" if self.week_start else "")]
        out.append(f"- Nhân viên: thêm {len(self.employees_inserted)}, cập nhật {len(self.employees_updated)}, giữ nguyên {self.employees_unchanged}")
        if self.employees_updated:
            out.append(f"  - cập nhật: {', '.join(self.employees_updated)}")
        if self.week_start:
            out.append(f"- Lịch bận: xóa {self.availability_deleted} dòng cũ, ghi {self.availability_inserted} dòng "
                       f"({self.busy_days} ngày có giờ bận, {self.al_days} ngày nghỉ phép)")
        out += [f"- ⚠ {w}" for w in self.warnings]
        return out


def _time(minutes: int | None) -> time | None:
    if minutes is None:
        return None
    m = min(int(minutes), DAY_MINUTES - 1)          # SQL time has no 24:00 -> 23:59
    return time(m // 60, m % 60)


def read_workbook(path: str | Path, store: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> (employees, availability) with one availability row per employee x weekday (0..6)."""
    xl = pd.ExcelFile(path)
    sheets = {norm_text(s): s for s in xl.sheet_names}
    emp = _rename(xl.parse(sheets.get(norm_text(EMPLOYEE_SHEET), xl.sheet_names[0]), dtype=str), _EMP_COLS)
    emp = emp[~emp["employee_id"].map(_blank)].copy()
    emp["employee_id"] = emp["employee_id"].map(norm_id)
    for c in ("name", "position", "employment_type", "labor_group", "status"):
        emp[c] = emp.get(c, "").map(lambda v: "" if _blank(v) else str(v).strip())
    emp["status"] = emp["status"].replace("", "Active")
    emp = emp.drop_duplicates("employee_id")

    av_name = sheets.get(norm_text(AVAILABILITY_SHEET))
    rows = []
    if av_name is not None:
        av = _rename(xl.parse(av_name, dtype=str), _AVAIL_COLS)
        for r in av.to_dict("records"):
            eid = norm_id(r.get("employee_id"))
            wd = parse_weekday(r.get("weekday"))
            if not eid or wd is None:
                continue
            f_raw, t_raw = r.get("busy_from"), r.get("busy_to")
            is_al = norm_text(f_raw) == "al" or norm_text(t_raw) == "al"
            s = None if is_al or _blank(f_raw) else parse_hhmm(f_raw)
            e = None if is_al or _blank(t_raw) else parse_hhmm(t_raw)
            rows.append({"employee_id": eid, "weekday": wd, "busy_from": s, "busy_to": e, "is_al": is_al})
    avail = pd.DataFrame(rows, columns=["employee_id", "weekday", "busy_from", "busy_to", "is_al"])
    return emp, avail


def load_store_workbook(engine: Engine, store: str, path: str | Path, week_start: date | None, user: str | None = None) -> LoadReport:
    """Upsert the store's employees; when week_start is given also replace that week's availability."""
    emp, avail = read_workbook(path, store)
    rep = LoadReport(store=store, week_start=week_start)
    with engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM dbo.dim_store WHERE Code = :c"), {"c": store}).scalar() == 0:
            raise ValueError(f"store {store} not in dbo.dim_store")
        existing = {str(r.EmployeeNumber): r for r in conn.execute(text(
            "SELECT Id, EmployeeNumber, FullName, PlantCode, Position, EmploymentType, LaborGroup, Status FROM dbo.dim_employee "
            "WHERE EmployeeNumber IN :ids").bindparams(_expanding("ids")), {"ids": [int(x) for x in emp["employee_id"]]})}

        for r in emp.to_dict("records"):
            eid = r["employee_id"]
            et, lg = parse_employment_type(r["employment_type"]), parse_labor_group(r["labor_group"])
            if et is None or lg is None:
                rep.warnings.append(f"{eid} {r['name']}: employment_type/labor_group không hợp lệ ({r['employment_type']!r}/{r['labor_group']!r}) — bỏ qua")
                continue
            vals = {"FullName": r["name"], "PlantCode": store, "Position": r["position"], "EmploymentType": et, "LaborGroup": lg,
                    "Status": r["status"], "n": int(eid)}
            old = existing.get(eid)
            if old is None:
                conn.execute(text(
                    "INSERT INTO dbo.dim_employee (FullName, EmployeeNumber, PlantCode, Position, EmploymentType, LaborGroup, Status, CreatedAt, UpdatedAt) "
                    "VALUES (:FullName, :n, :PlantCode, :Position, :EmploymentType, :LaborGroup, :Status, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET())"), vals)
                rep.employees_inserted.append(eid)
            else:
                if old.PlantCode != store:
                    rep.warnings.append(f"{eid} {r['name']}: đang thuộc store {old.PlantCode}, chuyển sang {store}")
                if any(str(getattr(old, c) or "").strip() != str(vals[c]) for c in EMPLOYEE_COLS):
                    conn.execute(text(
                        "UPDATE dbo.dim_employee SET FullName=:FullName, PlantCode=:PlantCode, Position=:Position, EmploymentType=:EmploymentType, "
                        "LaborGroup=:LaborGroup, Status=:Status, UpdatedAt=SYSDATETIMEOFFSET() WHERE EmployeeNumber=:n"), vals)
                    rep.employees_updated.append(eid)
                else:
                    rep.employees_unchanged += 1

        if week_start is not None:
            if week_start.weekday() != 0:
                raise ValueError(f"week_start {week_start} is not a Monday")
            ids = {str(r.EmployeeNumber): r.Id for r in conn.execute(text(
                "SELECT Id, EmployeeNumber FROM dbo.dim_employee WHERE PlantCode = :s"), {"s": store})}
            rep.availability_deleted = conn.execute(text(
                "DELETE FROM dbo.employee_availability_slot WHERE PlantCode = :s AND WeekStartMonday = :w"), {"s": store, "w": week_start}).rowcount
            by_key = {(a["employee_id"], a["weekday"]): a for a in avail.to_dict("records")}
            rows = []
            for eid in emp["employee_id"]:
                if eid not in ids:
                    continue
                for wd in range(7):
                    a = by_key.get((eid, wd))
                    is_al = bool(a and a["is_al"])
                    s = None if a is None or pd.isna(a["busy_from"]) else int(a["busy_from"])
                    e = None if a is None or pd.isna(a["busy_to"]) else int(a["busy_to"])
                    if (s is None) != (e is None) or (s is not None and e <= s):
                        rep.warnings.append(f"{eid} thứ {wd + 2}: giờ bận không hợp lệ ({s}-{e}) — coi như rảnh")
                        s = e = None
                    rep.busy_days += s is not None
                    rep.al_days += is_al
                    rows.append({"p": store, "n": int(eid), "i": ids[eid], "w": week_start, "d": week_start + timedelta(days=wd),
                                 "f": _time(s), "t": _time(e), "al": is_al})
            if rows:
                conn.execute(text(
                    "INSERT INTO dbo.employee_availability_slot (PlantCode, EmployeeNumber, EmployeeId, WeekStartMonday, WorkDate, BusyFrom, BusyTo, "
                    "IsPaidLeave, CreatedAt, UpdatedAt) VALUES (:p, :n, :i, :w, :d, :f, :t, :al, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET())"), rows)
            rep.availability_inserted = len(rows)
        _bump_version(conn, "inputs", f"{store} employees" + (f" + availability {week_start}" if week_start else ""), user)
    return rep


def upsert_ops_config(engine: Engine, targets: dict[str, float], user: str | None = None,
                      delete_store_codes: tuple[str, ...] = ()) -> list[str]:
    """targets = {store_code: tcph_target}; other columns keep the table defaults (1.05 / 2 / 2 / 2)."""
    user = user or getpass.getuser()
    log = []
    with engine.begin() as conn:
        for code in delete_store_codes:
            n = conn.execute(text("DELETE o FROM dbo.ops_store_config o JOIN dbo.dim_store s ON s.Id = o.store_id WHERE s.Code = :c"),
                             {"c": code}).rowcount
            log.append(f"xóa dòng test store {code}: {n}")
        for code, tcph in targets.items():
            sid = conn.execute(text("SELECT Id FROM dbo.dim_store WHERE Code = :c"), {"c": code}).scalar()
            if sid is None:
                raise ValueError(f"store {code} not in dbo.dim_store")
            n = conn.execute(text("UPDATE dbo.ops_store_config SET tcph_target = :t, updated_at = SYSDATETIMEOFFSET(), updated_by = :u "
                                  "WHERE store_id = :s"), {"t": tcph, "u": user, "s": sid}).rowcount
            if n == 0:
                conn.execute(text("INSERT INTO dbo.ops_store_config (store_id, tcph_target, tcph_ceiling_mult, open_staff, close_staff, "
                                  "min_staff_per_slot, created_at, updated_at, updated_by) VALUES (:s, :t, 1.05, 2, 2, 2, SYSDATETIMEOFFSET(), "
                                  "SYSDATETIMEOFFSET(), :u)"), {"s": sid, "t": tcph, "u": user})
            log.append(f"store {code} (Id {sid}): tcph_target = {tcph} ({'cập nhật' if n else 'thêm mới'})")
        _bump_version(conn, "inputs", "ops_store_config " + ", ".join(targets), user)
    return log


def _expanding(name: str):
    from sqlalchemy import bindparam
    return bindparam(name, expanding=True)


def _bump_version(conn, component: str, detail: str, user: str | None) -> int:
    v = int(conn.execute(text("SELECT ISNULL(MAX(DataVersion), 0) + 1 FROM sched.meta_build")).scalar())
    conn.execute(text("INSERT INTO sched.meta_build (Component, DataVersion, BuiltAt, BuiltBy, Detail) "
                      "VALUES (:c, :v, CAST(SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time' AS DATETIME2(0)), :u, :d)"),
                 {"c": component, "v": v, "u": user or getpass.getuser(), "d": detail[:1000]})
    return v
