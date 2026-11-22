#!/usr/bin/env python3
"""Generate dim_store + dim_store_detail MERGE scripts from Danh sách CH PLH Excel."""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

EXCEL_PATH = Path(
    r"c:\Users\tienlta\OneDrive - WIN\Project\weekly_workforce_planning\Danh sách CH PLH - 2026 (6).xlsx"
)
OUT_DIR = Path(__file__).resolve().parent.parent
OUT_DIM_STORE = OUT_DIR / "007_dim_store_seed.sql"
OUT_DIM_DETAIL = OUT_DIR / "007_dim_store_detail_seed.sql"
OUT_REPORT = OUT_DIR / "007_dim_store_import_report.txt"

TIME_PAIR_RE = re.compile(r"(\d{1,2}:\d{2})")
CLOSE_IN_TEXT_RE = re.compile(
    r"(?:close[d]?\s*:?\s*|CLOSED\s+)(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2}|T\d+\.\d+)",
    re.IGNORECASE,
)
DATE_TOKEN_RE = re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})")


def esc(value: str | None) -> str:
    if value is None:
        return "NULL"
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return "NULL"
    return "N'" + s.replace("'", "''") + "'"


def esc_required(value: str | None) -> str:
    """SQL string for NOT NULL columns; empty values become N''."""
    if value is None:
        return "N''"
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return "N''"
    return "N'" + s.replace("'", "''") + "'"


def esc_date(d: date | None) -> str:
    return "NULL" if d is None else f"'{d.isoformat()}'"


def norm_code(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return str(int(value))
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s


def parse_cell_date(value) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    first_line = s.splitlines()[0].strip()
    if CLOSE_IN_TEXT_RE.search(first_line) and not DATE_TOKEN_RE.search(first_line.split()[0] if first_line else ""):
        pass
    try:
        return pd.to_datetime(first_line, dayfirst=True).date()
    except Exception:
        m = DATE_TOKEN_RE.search(first_line)
        if not m:
            return None
        try:
            return pd.to_datetime(m.group(1), dayfirst=True).date()
        except Exception:
            return None


def parse_close_date_from_e(value, extra_line: str | None = None) -> date | None:
    texts: list[str] = []
    if value is not None and not (isinstance(value, float) and pd.isna(value)):
        texts.extend(str(value).splitlines())
    if extra_line:
        texts.append(extra_line)

    for raw in texts:
        raw = raw.strip()
        if not raw:
            continue
        m = CLOSE_IN_TEXT_RE.search(raw)
        if not m:
            continue
        token = m.group(1)
        if token.upper().startswith("T") and "." in token:
            # e.g. T9.24 -> ambiguous; leave NULL (logged in report)
            return None
        try:
            return pd.to_datetime(token.replace(".", "/"), dayfirst=True).date()
        except Exception:
            continue
    return None


def parse_open_close_from_operation_hour(raw) -> tuple[str | None, str | None, str | None, str | None]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None, None, None, None
    s = str(raw).strip()
    if not s:
        return None, None, None, None

    times = TIME_PAIR_RE.findall(s)
    if len(times) < 2:
        return None, None, None, None

    def to_time(t: str) -> time:
        h, m = t.split(":")
        return time(int(h), int(m))

    open_t = to_time(times[0])
    close_t = to_time(times[1])
    open_time = open_t.strftime("%H:%M")
    close_time = close_t.strftime("%H:%M")

    open_dt = datetime.combine(date.today(), open_t) - timedelta(minutes=30)
    close_dt = datetime.combine(date.today(), close_t) + timedelta(minutes=30)
    open_shift = open_dt.time().strftime("%H:%M")
    close_shift = close_dt.time().strftime("%H:%M")
    return open_time, close_time, open_shift, close_shift


def load_active_stores() -> list[dict]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Tổng", header=1)
    df = df[df["PLANT"].notna()].copy()
    stores: list[dict] = []
    for _, row in df.iterrows():
        code = norm_code(row["PLANT"])
        if not code:
            continue
        name = str(row["STORE NAME"]).strip() if pd.notna(row.get("STORE NAME")) else code
        city = str(row["City"]).strip() if pd.notna(row.get("City")) else None
        concept = str(row["Concept"]).strip() if pd.notna(row.get("Concept")) else None
        email = str(row["Email"]).strip() if pd.notna(row.get("Email")) else None
        open_date = parse_cell_date(row.get("Open Date (mm/dd/yyyy)"))
        stores.append(
            {
                "code": code,
                "name": name,
                "city": city,
                "concept": concept,
                "email": email,
                "open_date": open_date,
                "close_date": None,
                "is_active": 1,
            }
        )
    return stores


def load_closed_stores() -> list[dict]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Đóng cửa", header=0)
    stores: list[dict] = []
    warnings: list[str] = []

    for i in range(len(df)):
        row = df.iloc[i]
        code = norm_code(row.get("Store Code"))
        if not code:
            continue
        name_col = "Store Name_2" if "Store Name_2" in df.columns else df.columns[3]
        name = str(row[name_col]).strip() if pd.notna(row.get(name_col)) else code
        city = str(row["City"]).strip() if pd.notna(row.get("City")) else None
        concept = str(row["Concept"]).strip() if pd.notna(row.get("Concept")) else None
        email = str(row["Email"]).strip() if pd.notna(row.get("Email")) else None

        open_raw = row.get("Open Date")
        extra = None
        if i + 1 < len(df):
            next_row = df.iloc[i + 1]
            if not norm_code(next_row.get("Store Code")):
                extra_val = next_row.get("Open Date")
                if pd.notna(extra_val):
                    extra = str(extra_val)

        open_date = parse_cell_date(open_raw)
        close_date = parse_close_date_from_e(open_raw, extra)
        if close_date is None and extra:
            close_date = parse_close_date_from_e(extra)
        if close_date is None and open_raw is not None:
            close_date = parse_close_date_from_e(open_raw)

        if close_date is None:
            warnings.append(f"CloseDate missing for closed store {code} ({name})")

        stores.append(
            {
                "code": code,
                "name": name,
                "city": city,
                "concept": concept,
                "email": email,
                "open_date": open_date,
                "close_date": close_date,
                "is_active": 0,
            }
        )

    return stores, warnings


def load_dim_store_detail() -> tuple[list[dict], list[str]]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Tổng", header=1)
    df = df[df["PLANT"].notna()].copy()
    rows: list[dict] = []
    unparsed: list[str] = []

    for _, row in df.iterrows():
        code = norm_code(row["PLANT"])
        if not code:
            continue
        name = str(row["STORE NAME"]).strip() if pd.notna(row.get("STORE NAME")) else code
        city = str(row["City"]).strip() if pd.notna(row.get("City")) else None
        concept = str(row["Concept"]).strip() if pd.notna(row.get("Concept")) else None
        op_hour = row.get("Operation Hour")
        open_time, close_time, open_shift, close_shift = parse_open_close_from_operation_hour(op_hour)
        if op_hour is not None and not (isinstance(op_hour, float) and pd.isna(op_hour)) and open_time is None:
            unparsed.append(f"{code}: {op_hour}")

        rows.append(
            {
                "store_code": code,
                "store_name": name,
                "concept": concept,
                "city": city,
                "area_manager": "",
                "operation_manager": "",
                "region": "",
                "open_time": open_time,
                "close_time": close_time,
                "open_shift": open_shift,
                "close_shift": close_shift,
                "sm": None,
            }
        )
    return rows, unparsed


def write_dim_store_seed(stores: list[dict]) -> None:
    lines = [
        "-- 007_dim_store_seed.sql",
        "-- Encoding: UTF-8 (run sqlcmd with -f 65001)",
        "-- Generated from Danh sách CH PLH - 2026 (6).xlsx",
        "USE WorkforcePlanning;",
        "GO",
        "SET NOCOUNT ON;",
        "",
        "MERGE dbo.dim_store AS t",
        "USING (",
        "VALUES",
    ]
    values = []
    for s in stores:
        values.append(
            f"    ({esc(s['code'])}, {esc(s['name'])}, {esc(s['city'])}, {esc(s['concept'])}, "
            f"{esc_date(s['open_date'])}, {esc_date(s['close_date'])}, {esc(s['email'])}, NULL, {s['is_active']})"
        )
    lines.append(",\n".join(values))
    lines.extend(
        [
            ") AS s (Code, Name, City, Concept, OpenDate, CloseDate, Email, AreaManagerId, IsActive)",
            "ON t.Code = s.Code",
            "WHEN MATCHED THEN UPDATE SET",
            "    Name = s.Name,",
            "    City = s.City,",
            "    Concept = s.Concept,",
            "    OpenDate = s.OpenDate,",
            "    CloseDate = s.CloseDate,",
            "    Email = s.Email,",
            "    IsActive = s.IsActive",
            "WHEN NOT MATCHED THEN INSERT (Code, Name, City, Concept, OpenDate, CloseDate, Email, AreaManagerId, IsActive)",
            "VALUES (s.Code, s.Name, s.City, s.Concept, s.OpenDate, s.CloseDate, s.Email, s.AreaManagerId, s.IsActive);",
            "GO",
            "",
            "SELECT IsActive, COUNT(*) AS Cnt FROM dbo.dim_store GROUP BY IsActive ORDER BY IsActive;",
            "GO",
        ]
    )
    OUT_DIM_STORE.write_text("\n".join(lines), encoding="utf-8-sig")


def write_dim_detail_seed(details: list[dict]) -> None:
    lines = [
        "-- 007_dim_store_detail_seed.sql",
        "-- Encoding: UTF-8 (run sqlcmd with -f 65001)",
        "-- Generated from sheet Tổng (Operation Hour -> Open/Close Time & Shifts)",
        "USE WorkforcePlanning;",
        "GO",
        "SET NOCOUNT ON;",
        "",
        "MERGE dbo.dim_store_detail AS t",
        "USING (",
        "VALUES",
    ]
    values = []
    for d in details:
        values.append(
            f"    ({esc(d['store_code'])}, {esc(d['store_name'])}, {esc(d['concept'])}, {esc(d['city'])}, "
            f"{esc_required(d['area_manager'])}, {esc_required(d['operation_manager'])}, {esc_required(d['region'])}, "
            f"{esc(d['open_time'])}, {esc(d['close_time'])}, {esc(d['open_shift'])}, {esc(d['close_shift'])}, {esc(d['sm'])})"
        )
    lines.append(",\n".join(values))
    lines.extend(
        [
            ") AS s (StoreCode, StoreName, Concept, City, AreaManager, OperationManager, Region, "
            "OpenTime, CloseTime, OpenShift, CloseShift, SM)",
            "ON t.StoreCode = s.StoreCode",
            "WHEN MATCHED THEN UPDATE SET",
            "    StoreName = s.StoreName,",
            "    Concept = s.Concept,",
            "    City = s.City,",
            "    OpenTime = s.OpenTime,",
            "    CloseTime = s.CloseTime,",
            "    OpenShift = s.OpenShift,",
            "    CloseShift = s.CloseShift,",
            "    SM = s.SM",
            "WHEN NOT MATCHED THEN INSERT (",
            "    StoreCode, StoreName, Concept, City, AreaManager, OperationManager, Region,",
            "    OpenTime, CloseTime, OpenShift, CloseShift, SM)",
            "VALUES (",
            "    s.StoreCode, s.StoreName, s.Concept, s.City, s.AreaManager, s.OperationManager, s.Region,",
            "    s.OpenTime, s.CloseTime, s.OpenShift, s.CloseShift, s.SM);",
            "GO",
            "",
            "SELECT COUNT(*) AS TotalDetail,",
            "       SUM(CASE WHEN OpenTime IS NULL THEN 1 ELSE 0 END) AS MissingOpenTime",
            "FROM dbo.dim_store_detail;",
            "GO",
        ]
    )
    OUT_DIM_DETAIL.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    if not EXCEL_PATH.exists():
        print(f"Excel not found: {EXCEL_PATH}", file=sys.stderr)
        sys.exit(1)

    active = load_active_stores()
    closed, close_warnings = load_closed_stores()
    all_codes = {s["code"] for s in active}
    closed_only = [s for s in closed if s["code"] not in all_codes]
    all_stores = active + closed_only

    details, unparsed_hours = load_dim_store_detail()
    write_dim_store_seed(all_stores)
    write_dim_detail_seed(details)

    active_n = len(active)
    closed_n = len(closed_only)
    parsed_shifts = sum(1 for d in details if d["open_time"])
    report_lines = [
        f"Excel: {EXCEL_PATH}",
        f"dim_store rows: {len(all_stores)} (active {active_n}, closed {closed_n})",
        f"dim_store_detail rows: {len(details)}",
        f"Operation Hour parsed: {parsed_shifts}/{len(details)}",
        f"Unparsed Operation Hour: {len(unparsed_hours)}",
        f"Closed stores missing CloseDate: {len(close_warnings)}",
        "",
        "CloseDate warnings:",
        *close_warnings[:50],
        "",
        "Unparsed Operation Hour samples:",
        *unparsed_hours[:30],
    ]
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote {OUT_DIM_STORE} ({len(all_stores)} stores)")
    print(f"Wrote {OUT_DIM_DETAIL} ({len(details)} detail rows)")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()