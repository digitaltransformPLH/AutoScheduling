"""Helpers for revisions that run a frozen .sql file (batches separated by a line `GO`)."""
import re
from pathlib import Path

from alembic import op

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def run_sql_file(name: str) -> None:
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    for batch in re.split(r"^\s*GO\s*$", text, flags=re.M | re.I):
        if batch.strip() and not all(ln.strip().startswith("--") or not ln.strip() for ln in batch.splitlines()):
            op.execute(batch)
