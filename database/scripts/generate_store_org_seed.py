#!/usr/bin/env python3
"""Generate SQL seed script from Danh sách CH PLH Excel file."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

EXCEL_PATH = Path(r"c:\Users\tienlta\Downloads\Danh sách CH PLH - 2026 (1).xlsx")
OUT_SQL = Path(__file__).resolve().parent.parent / "006_store_org_seed.sql"

NAME_ALIASES = {
    "Anna Nguyen": "Nguyễn Thị Yến Tuyết (Anna Nguyễn)",
    "Nguyễn Thị Yến Tuyết (Anna Nguyễn)": "Anna Nguyen",
}


def esc(value: str | None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NULL"
    s = str(value).strip()
    if not s or s.lower() == "nan" or s == "x":
        return "NULL"
    return "N'" + s.replace("'", "''") + "'"


def canonical(name: str | None) -> str | None:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    s = str(name).strip()
    if not s or s == "x":
        return None
    return NAME_ALIASES.get(s, s)


def parse_date(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return pd.to_datetime(s).date().isoformat()
    except Exception:
        return None


def load_persons() -> list[dict]:
    dm = pd.read_excel(EXCEL_PATH, sheet_name="District Manager", header=2)
    persons: dict[str, dict] = {}

    for _, row in dm.iterrows():
        role_raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        name = canonical(str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else None)
        if not name:
            continue
        role = "ROM" if role_raw.upper() == "ROM" else "AM"
        email = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else None
        phone = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else None
        key = (name, role)
        persons[key] = {
            "full_name": name,
            "email": email,
            "phone": phone,
            "role": role,
        }

    df = pd.read_excel(EXCEL_PATH, sheet_name="Tổng", header=1)
    df = df[df["PLANT"].notna()].copy()
    am_col = "AM 01/06/26"
    rom_col = "ROM 05/04/26"

    for am in df[am_col].dropna().unique():
        name = canonical(str(am))
        if name:
            persons.setdefault((name, "AM"), {"full_name": name, "email": None, "phone": None, "role": "AM"})

    for rom in df[rom_col].dropna().unique():
        name = canonical(str(rom))
        if name:
            persons.setdefault((name, "ROM"), {"full_name": name, "email": None, "phone": None, "role": "ROM"})

    return list(persons.values())


def load_am_om_pairs(person_index: dict[tuple[str, str], int]) -> list[tuple[int, int]]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Tổng", header=1)
    df = df[df["PLANT"].notna()].copy()
    am_col = "AM 01/06/26"
    rom_col = "ROM 05/04/26"
    pairs: dict[tuple[str, str], int] = {}

    for _, row in df[[am_col, rom_col]].dropna().iterrows():
        am = canonical(str(row[am_col]))
        rom = canonical(str(row[rom_col]))
        if not am or not rom:
            continue
        pairs[(am, rom)] = pairs.get((am, rom), 0) + 1

    result: list[tuple[int, int]] = []
    am_best: dict[str, str] = {}
    for (am, rom), count in sorted(pairs.items(), key=lambda x: -x[1]):
        if am not in am_best:
            am_best[am] = rom

    for am, rom in sorted(am_best.items()):
        am_id = person_index.get((am, "AM"))
        rom_id = person_index.get((rom, "ROM"))
        if am_id and rom_id:
            result.append((am_id, rom_id))
    return result


def load_stores(person_index: dict[tuple[str, str], int]) -> list[dict]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Tổng", header=1)
    df = df[df["PLANT"].notna()].copy()
    am_col = "AM 01/06/26"

    stores = []
    for _, row in df.iterrows():
        code = str(row["PLANT"]).strip().replace(".0", "")
        if not code or code.lower() == "nan":
            continue
        am_name = canonical(str(row[am_col]) if pd.notna(row.get(am_col)) else None)
        am_id = person_index.get((am_name, "AM")) if am_name else None
        city = str(row["City"]).strip() if pd.notna(row.get("City")) else None
        email = str(row["Email"]).strip() if pd.notna(row.get("Email")) else None
        name = str(row["STORE NAME"]).strip() if pd.notna(row.get("STORE NAME")) else code
        open_date = parse_date(row.get("Open Date (mm/dd/yyyy)"))
        stores.append({
            "code": code,
            "name": name,
            "city": city,
            "concept": None,
            "email": email,
            "open_date": open_date,
            "area_manager_id": am_id,
        })
    return stores


def main() -> None:
    if not EXCEL_PATH.exists():
        print(f"Excel not found: {EXCEL_PATH}", file=sys.stderr)
        sys.exit(1)

    persons = load_persons()
    lines = [
        "-- 006_store_org_seed.sql",
        "-- Person, AmOmAssignment, Store org data from Danh sách CH PLH - 2026",
        "SET NOCOUNT ON;",
        "",
        "-- Persons",
    ]

    person_index: dict[tuple[str, str], int] = {}
    for i, p in enumerate(sorted(persons, key=lambda x: (x["role"], x["full_name"])), start=1):
        person_index[(p["full_name"], p["role"])] = i
        lines.append(
            f"IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = {i}) "
            f"INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) "
            f"VALUES ({i}, {esc(p['full_name'])}, {esc(p['email'])}, {esc(p['phone'])}, {esc(p['role'])}, 1);"
        )

    lines.append("")
    lines.append("-- AmOmAssignments (current)")
    for idx, (am_id, rom_id) in enumerate(load_am_om_pairs(person_index), start=1):
        lines.append(
            f"IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = {idx}) "
            f"INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) "
            f"VALUES ({idx}, {am_id}, {rom_id}, '2026-06-01', NULL);"
        )

    lines.append("")
    lines.append("-- Stores MERGE")
    lines.append("MERGE dbo.Stores AS t")
    lines.append("USING (")
    store_values = []
    for s in load_stores(person_index):
        am = "NULL" if s["area_manager_id"] is None else str(s["area_manager_id"])
        od = "NULL" if not s["open_date"] else f"'{s['open_date']}'"
        store_values.append(
            f"    ({esc(s['code'])}, {esc(s['name'])}, {esc(s['city'])}, {esc(s['concept'])}, {od}, {esc(s['email'])}, {am}, 1)"
        )
    lines.append("VALUES\n" + ",\n".join(store_values))
    lines.append(") AS s (Code, Name, City, Concept, OpenDate, Email, AreaManagerId, IsActive)")
    lines.append("ON t.Code = s.Code")
    lines.append("WHEN MATCHED THEN UPDATE SET")
    lines.append("    Name = s.Name, City = s.City, Concept = s.Concept, OpenDate = s.OpenDate,")
    lines.append("    Email = s.Email, AreaManagerId = s.AreaManagerId, IsActive = s.IsActive")
    lines.append("WHEN NOT MATCHED THEN INSERT (Code, Name, City, Concept, OpenDate, Email, AreaManagerId, IsActive)")
    lines.append("VALUES (s.Code, s.Name, s.City, s.Concept, s.OpenDate, s.Email, s.AreaManagerId, s.IsActive);")
    lines.append("")
    lines.append("PRINT 'Store org seed completed.';")

    OUT_SQL.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"Wrote {OUT_SQL} ({len(persons)} persons, {len(store_values)} stores)")


if __name__ == "__main__":
    main()
