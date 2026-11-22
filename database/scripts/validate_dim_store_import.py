#!/usr/bin/env python3
"""Validate expected counts from PLH Excel against optional SQL Server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Reuse generators for offline checks
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_dim_store_from_plh import (  # noqa: E402
    EXCEL_PATH,
    load_active_stores,
    load_closed_stores,
    load_dim_store_detail,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", action="store_true", help="Query local WorkforcePlanning DB")
    args = parser.parse_args()

    if not EXCEL_PATH.exists():
        print(f"FAIL: Excel not found: {EXCEL_PATH}", file=sys.stderr)
        sys.exit(1)

    active = load_active_stores()
    closed, _ = load_closed_stores()
    details, unparsed = load_dim_store_detail()
    parsed = sum(1 for d in details if d["open_time"])

    print(f"Excel active stores: {len(active)}")
    print(f"Excel closed stores: {len(closed)}")
    print(f"Excel detail rows: {len(details)}")
    print(f"Operation hour parsed: {parsed}/{len(details)} (unparsed {len(unparsed)})")

    if args.sql:
        try:
            import pyodbc  # type: ignore
        except ImportError:
            print("pyodbc not installed; skip SQL validation")
            return

        cs = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=localhost\\SQLEXPRESS;"
            "Database=WorkforcePlanning;"
            "Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(cs, timeout=10)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN IsActive=0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN IsActive=0 AND CloseDate IS NULL THEN 1 ELSE 0 END) FROM dbo.dim_store"
        )
        total, closed_db, missing_close = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN OpenTime IS NULL THEN 1 ELSE 0 END) FROM dbo.dim_store_detail"
        )
        detail_total, missing_open = cur.fetchone()
        conn.close()
        print(f"DB dim_store: {total} rows, closed={closed_db}, closed w/o CloseDate={missing_close}")
        print(f"DB dim_store_detail: {detail_total} rows, missing OpenTime={missing_open}")

    print("Validation completed.")


if __name__ == "__main__":
    main()