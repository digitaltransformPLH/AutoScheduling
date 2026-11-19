"""Shared FastAPI dependencies and row helpers."""
from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime, time
from decimal import Decimal

from auto_scheduling.db import get_engine
from auto_scheduling.settings import get_settings
from fastapi import HTTPException
from sqlalchemy import Connection, text

_SNAKE_1 = re.compile(r"(.)([A-Z][a-z]+)")
_SNAKE_2 = re.compile(r"([a-z0-9])([A-Z])")


def get_conn() -> Iterator[Connection]:
    with get_engine().connect() as conn:
        yield conn


def snake(name: str) -> str:
    """'WeekStart' -> 'week_start', 'ADTC' -> 'adtc', 'Is24h' -> 'is24h'."""
    return _SNAKE_2.sub(r"\1_\2", _SNAKE_1.sub(r"\1_\2", name)).lower()


def clean(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, time):
        return v.strftime("%H:%M")
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="minutes")
    if isinstance(v, date):
        return v.isoformat()
    return v


def rows(conn: Connection, sql: str, **params) -> list[dict]:
    """Run a SELECT on a sched.vw_* view; keys become snake_case (Pydantic models expose camelCase)."""
    res = conn.execute(text(sql), params)
    keys = [snake(k) for k in res.keys()]  # noqa: SIM118 - SQLAlchemy Result.keys()
    return [{k: clean(v) for k, v in zip(keys, r, strict=True)} for r in res.fetchall()]


def meta(conn: Connection) -> dict:
    r = conn.execute(text("SELECT DataVersion, BuiltAt FROM sched.vw_meta")).first()
    s = get_settings()
    return {"data_version": int(r[0]) if r else 0, "built_at": clean(r[1]) if r and r[1] else None, "source": "sched",
            "back_test": s.back_test, "availability_week": s.default_availability_week}


def parse_week(week: str) -> date:
    try:
        d = date.fromisoformat(week)
    except ValueError as exc:
        raise HTTPException(422, "week must be YYYY-MM-DD") from exc
    if d.weekday() != 0:
        raise HTTPException(422, "week must be a Monday")
    return d
