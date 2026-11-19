"""Run the engine for one store-week and store the result (used by the API and the CLI).

Flow: sched.engine_run row (queued) -> running -> engine (SQL source) -> sched.Schedule* replaced -> done / failed.
A run that is blocked by input errors still writes ScheduleWeeks (status "Không xếp được") + issues so the UI
can show why.
"""
from __future__ import annotations

import getpass
import traceback
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text

from .config import DEFAULT_CONFIG, Config
from .db import get_engine
from .output.db_writer import ASSESSMENT_VI, write_run
from .pipeline import SqlSource, run_store_week
from .settings import get_settings

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def create_run(engine: Engine, store: str, week: date, availability_week: date | None, user: str) -> int:
    with engine.begin() as conn:
        return int(conn.execute(text(
            "INSERT INTO sched.engine_run (StoreCode, WeekStart, AvailabilityWeek, Status, RequestedBy, RequestedAt) "
            "OUTPUT INSERTED.RunId VALUES (:s, :w, :a, 'queued', :u, :t)"),
            {"s": store, "w": week, "a": availability_week, "u": user, "t": _now()}).scalar())


def _update(engine: Engine, run_id: int, **cols) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in cols)
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE sched.engine_run SET {sets} WHERE RunId = :run_id"), {**cols, "run_id": run_id})


def execute_run(run_id: int, store: str, week: date, availability_week: date | None, user: str,
                cfg: Config | None = None, engine: Engine | None = None) -> dict:
    """Run + store; never raises (failures are written to engine_run)."""
    engine = engine or get_engine()
    cfg = cfg or DEFAULT_CONFIG.with_overrides(allow_past_weeks=get_settings().allow_past_weeks)   # SCHED_ALLOW_PAST_WEEKS
    _update(engine, run_id, Status="running", StartedAt=_now())
    try:
        res = run_store_week(store, week, cfg, SqlSource(availability_week=availability_week), write_outputs=False)
        replaced, counts = write_run(res, cfg, engine=engine, created_by=user, run_id=run_id)
        assessment = ASSESSMENT_VI.get(res.kpi.planning_status) if res.kpi else ASSESSMENT_VI["CRITICAL"]
        crit = sum(i.severity == "CRITICAL" for i in res.issues)
        msg = ("Không xếp được lịch: " + "; ".join(i.message for i in res.issues if i.severity == "CRITICAL")[:1500]) if res.blocked \
            else f"{counts['ScheduleRoster']} dòng roster, {crit} lỗi" + (" (thay lịch cũ)" if replaced else "")
        _update(engine, run_id, Status="done", FinishedAt=_now(), Assessment=assessment, Message=msg[:2000])
        return {"run_id": run_id, "status": "done", "assessment": assessment, "blocked": res.blocked, "counts": counts}
    except Exception as exc:  # noqa: BLE001 - reported to the UI through engine_run
        _update(engine, run_id, Status="failed", FinishedAt=_now(), Message=f"{type(exc).__name__}: {exc}"[:2000])
        traceback.print_exc()
        return {"run_id": run_id, "status": "failed", "error": str(exc)}


def run_and_store(store: str, week: date, availability_week: date | None = None, user: str | None = None,
                  cfg: Config | None = None) -> dict:
    engine = get_engine()
    user = user or getpass.getuser()
    run_id = create_run(engine, store, week, availability_week, user)
    return execute_run(run_id, store, week, availability_week, user, cfg, engine)
