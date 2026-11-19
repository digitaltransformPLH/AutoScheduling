"""Store "Availability File" workbook -> dim_employee + busy frames (SPEC Section 2 contracts).

One workbook per store (e.g. `data/Availability File 2189.xlsx`) with two sheets:

* `Employee Master`: Employee Name | Employee ID | Position | Employment Type | Labor group | Status
* `Availability`:    Employee Name | Employee ID | Position | Employment Type | Ngày | Bận từ | Bận đến

Rows of `Availability` with an empty "Bận từ"/"Bận đến" mean *available all day*.
`busy_semantics` says how a filled row is read:

* "busy"      (default, as the header says): the employee is busy in [Bận từ, Bận đến).
* "available": the store filled the inverse (the window the employee CAN work); busy
               = everything outside that window. Some stores fill the sheet this way
               (e.g. "07:00-23:00" on every day for a PT who is available all week).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..timeutil import DAY_MINUTES, fmt_hhmm, norm_text, parse_hhmm
from .loaders import norm_id

EMPLOYEE_SHEET = "Employee Master"
AVAILABILITY_SHEET = "Availability"
BUSY_SEMANTICS = ("busy", "available")

_EMP_COLS = {"employeename": "name", "employeeid": "employee_id", "position": "position",
             "employmenttype": "employment_type", "laborgroup": "labor_group", "status": "status"}
_AVAIL_COLS = {"employeeid": "employee_id", "employeename": "name", "ngay": "weekday", "weekday": "weekday", "day": "weekday",
               "bantu": "busy_from", "busyfrom": "busy_from", "banden": "busy_to", "busyto": "busy_to"}


def _rename(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    cols = {}
    for c in df.columns:
        key = norm_text(c)
        if key in mapping:
            cols[c] = mapping[key]
    return df.rename(columns=cols)


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip().lower() in ("", "nan", "none", "nat")


def default_availability_path(data_dir: Path, store_id: str) -> Path:
    return Path(data_dir) / f"Availability File {store_id}.xlsx"


def load_availability_file(path: str | Path, store_id: str, busy_semantics: str = "busy") -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> (dim_employee, busy) DataFrames in the SPEC Section 2 column layout."""
    if busy_semantics not in BUSY_SEMANTICS:
        raise ValueError(f"busy_semantics must be one of {BUSY_SEMANTICS}")
    xl = pd.ExcelFile(path)
    sheets = {norm_text(s): s for s in xl.sheet_names}
    emp_sheet = sheets.get(norm_text(EMPLOYEE_SHEET)) or xl.sheet_names[0]
    av_sheet = sheets.get(norm_text(AVAILABILITY_SHEET)) or (xl.sheet_names[1] if len(xl.sheet_names) > 1 else None)

    emp = _rename(xl.parse(emp_sheet, dtype=str), _EMP_COLS)
    missing = {"employee_id", "name", "position", "employment_type", "labor_group"} - set(emp.columns)
    if missing:
        raise ValueError(f"{path}: sheet {emp_sheet!r} missing columns {sorted(missing)}")
    if "status" not in emp.columns:
        emp["status"] = "Active"
    emp = emp[~emp["employee_id"].map(_blank)].copy()
    emp["employee_id"] = emp["employee_id"].map(norm_id)
    emp.insert(1, "store_id", store_id)
    emp = emp[["employee_id", "store_id", "name", "position", "employment_type", "labor_group", "status"]]
    for c in emp.columns:
        emp[c] = emp[c].map(lambda v: "" if _blank(v) else str(v).strip())

    busy_rows: list[dict] = []
    if av_sheet is not None:
        av = _rename(xl.parse(av_sheet, dtype=str), _AVAIL_COLS)
        need = {"employee_id", "weekday", "busy_from", "busy_to"}
        if need - set(av.columns):
            raise ValueError(f"{path}: sheet {av_sheet!r} missing columns {sorted(need - set(av.columns))}")
        for r in av.to_dict("records"):
            emp_id = norm_id(r["employee_id"])
            if not emp_id or _blank(r["weekday"]):
                continue
            f_raw, t_raw = r["busy_from"], r["busy_to"]
            if _blank(f_raw) and _blank(t_raw):
                continue                                    # available all day
            if norm_text(f_raw) == "al" or norm_text(t_raw) == "al":
                busy_rows.append({"employee_id": emp_id, "store_id": store_id, "weekday": str(r["weekday"]).strip(),
                                  "busy_from": "AL", "busy_to": "AL"})
                continue
            s, e = parse_hhmm(f_raw), parse_hhmm(t_raw)
            if s is None or e is None:
                # keep the raw text so load_busy reports BAD_BUSY_TIME with the original value
                busy_rows.append({"employee_id": emp_id, "store_id": store_id, "weekday": str(r["weekday"]).strip(),
                                  "busy_from": str(f_raw).strip(), "busy_to": str(t_raw).strip()})
                continue
            if busy_semantics == "busy":
                blocks = [(s, e)]
            else:                                           # window the employee CAN work -> busy outside it
                blocks = [(0, s), (e, DAY_MINUTES)]
            for bs, be in blocks:
                if be > bs:
                    busy_rows.append({"employee_id": emp_id, "store_id": store_id, "weekday": str(r["weekday"]).strip(),
                                      "busy_from": fmt_hhmm(bs), "busy_to": "24:00" if be >= DAY_MINUTES else fmt_hhmm(be)})
    busy = pd.DataFrame(busy_rows, columns=["employee_id", "store_id", "weekday", "busy_from", "busy_to"])
    return emp, busy
