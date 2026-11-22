#!/usr/bin/env python3
"""Apply dim_store MERGE scripts via pyodbc (UTF-8 safe, no sqlcmd encoding issues)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_DIR = ROOT / "database"
DEFAULT_FILES = [
    DB_DIR / "007_dim_store_seed.sql",
    DB_DIR / "007_dim_store_detail_seed.sql",
]


def split_batches(sql: str) -> list[str]:
    parts = re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)
    return [p.strip() for p in parts if p.strip() and not p.strip().startswith("--")]


def strip_use_statement(batch: str) -> str:
    lines = []
    for line in batch.splitlines():
        if re.match(r"^\s*USE\s+", line, re.IGNORECASE):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default=r"localhost\SQLEXPRESS")
    parser.add_argument("--database", default="WorkforcePlanning")
    args = parser.parse_args()

    try:
        import pyodbc
    except ImportError:
        print("Install pyodbc: pip install pyodbc", file=sys.stderr)
        sys.exit(1)

    cs = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={args.server};Database={args.database};Trusted_Connection=yes;"
    )
    conn = pyodbc.connect(cs, autocommit=True, timeout=120)

    for path in DEFAULT_FILES:
        if not path.exists():
            print(f"Missing {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8-sig")
        print(f"Applying {path.name}...")
        for batch in split_batches(text):
            batch = strip_use_statement(batch)
            if not batch:
                continue
            conn.cursor().execute(batch)

    cur = conn.cursor()
    cur.execute("SELECT TOP 1 Name, City FROM dbo.dim_store WHERE Code = '2005'")
    row = cur.fetchone()
    conn.close()
    if row:
        print(f"Sample 2005: Name={row[0]!r}, City={row[1]!r}")
    print("Apply completed.")


if __name__ == "__main__":
    main()