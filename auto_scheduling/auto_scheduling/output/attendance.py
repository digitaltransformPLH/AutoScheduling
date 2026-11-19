"""File 2 - attendance upload "Upload Phân Công" (SPEC 7.2), built from `schedule` only."""
from __future__ import annotations

import re
from datetime import date, time, timedelta
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from ..config import Config
from ..inputs.shift_codes import ShiftCodeTable
from ..models import Employee, StoreParams
from ..timeutil import parse_hhmm
from .tables import sorted_employees

HEADERS = [
    "Mã CH", "Mã nhân viên", "Tên nhân viên", "Template", "Ngày bắt đầu (dd.MM.yyyy)", "Ngày kết thúc (dd.MM.yyyy)",
    "Mã ca làm việc/Loại nghỉ/ công tác (Tr.hợp phân loại nghỉ phép/ công tác thì phải phân ca của 2003 kèm theo, không phân ca OFF)",
    "Giờ vào (HH:mm)", "Giờ ra (HH:mm)",
]
COL_WIDTHS = [8, 14, 28, 10, 25, 25, 62, 16, 16]
TEMPLATE = 2003


def attendance_store_code(store_id: str) -> str:
    digits = re.sub(r"\D", "", store_id)
    return f"PL{digits[-4:]}" if digits else store_id


def attendance_file_name(store: StoreParams, week_start: date) -> str:
    short = re.sub(r"[^A-Za-z0-9]+", "_", store.short_name).strip("_") or store.store_id
    return f"{store.store_id}_{short}_Upload_Phan_Cong_{week_start:%Y%m%d}-{week_start + timedelta(days=6):%Y%m%d}.xlsx"


def _cell_code(code: str):
    return int(code) if code.isdigit() else code


def _xl_time(hhmm: str) -> time:
    m = parse_hhmm(hhmm)
    return time(m // 60 % 24, m % 60)


def build_attendance_rows(schedule: pd.DataFrame, employees: list[Employee], store: StoreParams, week_start: date,
                          codes: ShiftCodeTable, cfg: Config, away: dict[str, dict[date, str]] | None = None) -> tuple[list[list], list[str]]:
    """-> (rows, errors). Errors = shifts (or the AL / secondment pair) without a code: 'id - name - dd.MM.yyyy: HH:mm-HH:mm'.

    away = {employee_id: {date: receiving_store}}: days lent to another store keep their paid hours (away shift), never OFF.
    """
    away = away or {}
    aw_code = codes.lookup(parse_hhmm(cfg.away_shift_start), parse_hhmm(cfg.away_shift_end))
    by_key = {(r.employee_id, r.date): r for r in schedule.itertuples(index=False)}
    al_code = codes.lookup(parse_hhmm(cfg.al_shift_start), parse_hhmm(cfg.al_shift_end))
    code_cell = attendance_store_code(store.store_id)
    rows, errors = [], []
    for emp in sorted_employees(employees):
        for i in range(7):
            d = week_start + timedelta(days=i)
            ds = d.strftime("%d.%m.%Y")
            r = by_key.get((emp.employee_id, d))
            base = [code_cell, emp.employee_id, emp.name, TEMPLATE, ds, ds]
            if r is None and d in away.get(emp.employee_id, {}):
                if aw_code is None:
                    errors.append(f"{emp.employee_id} - {emp.name} - {ds}: hỗ trợ {cfg.away_shift_start}-{cfg.away_shift_end}")
                    rows.append(base + ["OFF", None, None])
                else:
                    rows.append(base + [_cell_code(aw_code), _xl_time(cfg.away_shift_start), _xl_time(cfg.away_shift_end)])
                continue
            if r is None:
                rows.append(base + ["OFF", None, None])
                continue
            if bool(r.is_paid_leave):
                if al_code is None:
                    errors.append(f"{emp.employee_id} - {emp.name} - {ds}: AL {cfg.al_shift_start}-{cfg.al_shift_end}")
                    rows.append(base + ["OFF", None, None])
                else:
                    rows.append(base + [_cell_code(al_code), _xl_time(cfg.al_shift_start), _xl_time(cfg.al_shift_end)])
                continue
            code = codes.lookup(parse_hhmm(r.start), parse_hhmm(r.end) + (0 if parse_hhmm(r.end) > parse_hhmm(r.start) else 1440))
            if code is None:
                errors.append(f"{emp.employee_id} - {emp.name} - {ds}: {r.start}-{r.end}")
                rows.append(base + ["OFF", None, None])
            else:
                rows.append(base + [_cell_code(code), _xl_time(r.start), _xl_time(r.end)])
    return rows, errors


def format_errors(errors: list[str], limit: int = 20) -> str:
    shown = errors[:limit]
    rest = len(errors) - len(shown)
    return "\n".join(shown) + (f"\n... and {rest} more" if rest > 0 else "")


def write_attendance_file(schedule: pd.DataFrame, employees: list[Employee], store: StoreParams, week_start: date,
                          codes: ShiftCodeTable, cfg: Config, out_dir: Path,
                          away: dict[str, dict[date, str]] | None = None) -> tuple[Path | None, list[str]]:
    """Writes the xlsx; returns (path, []) or (None, errors) when blocked (SPEC 7.2 blocking validation)."""
    if week_start.weekday() != 0:
        return None, [f"week_start {week_start} is not a Monday"]
    if schedule is None or schedule.empty:
        return None, ["no final roster"]
    rows, errors = build_attendance_rows(schedule, employees, store, week_start, codes, cfg, away)
    if errors:
        return None, errors
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
        n = ws.max_row
        for col in (8, 9):
            ws.cell(row=n, column=col).number_format = "HH:mm"
    for i, w in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / attendance_file_name(store, week_start)
    wb.save(path)
    return path, []
