"""Engine runs: POST queues a run (background thread, one at a time), GET polls its status."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from auto_scheduling.db import get_engine
from auto_scheduling.service import create_run, execute_run
from auto_scheduling.settings import get_settings
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection

from ..auth import RUN_ENGINE, SCHEDULE_VIEW, User, ensure_store, require
from ..deps import get_conn, meta, parse_week, rows
from ..schemas import Envelope, Run, RunRequest

router = APIRouter(tags=["runs"])
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="engine-run")   # the engine is CPU-bound: serialise runs


@router.get("/runs", response_model=Envelope[list[Run]])
def list_runs(store: str | None = Query(None, max_length=10), limit: int = Query(30, ge=1, le=200),
              conn: Connection = Depends(get_conn), user: User = Depends(require(*SCHEDULE_VIEW))) -> dict:
    sql = f"SELECT TOP ({int(limit)}) * FROM sched.vw_engine_runs" + (" WHERE StoreCode = :s" if store else "") + " ORDER BY RunId DESC"
    return {"data": [r for r in rows(conn, sql, s=store) if user.can_store(r["store_code"])], "meta": meta(conn)}


@router.get("/runs/{run_id}", response_model=Envelope[Run])
def get_run(run_id: int, conn: Connection = Depends(get_conn), user: User = Depends(require(*SCHEDULE_VIEW))) -> dict:
    r = rows(conn, "SELECT * FROM sched.vw_engine_runs WHERE RunId = :r", r=run_id)
    if not r or not user.can_store(r[0]["store_code"]):
        raise HTTPException(404, f"run {run_id} not found")
    return {"data": r[0], "meta": meta(conn)}


@router.post("/runs", response_model=Envelope[Run], status_code=202)
def start_run(req: RunRequest, conn: Connection = Depends(get_conn), user: User = Depends(require(*RUN_ENGINE))) -> dict:
    ensure_store(user, req.store_code)
    week = parse_week(req.week_start)
    aw_raw = req.availability_week or get_settings().default_availability_week
    aw = parse_week(aw_raw) if aw_raw else None
    busy = rows(conn, "SELECT TOP 1 RunId FROM sched.vw_engine_runs WHERE StoreCode = :s AND WeekStart = :w AND Status IN ('queued','running')",
                s=req.store_code, w=week)
    if busy:
        raise HTTPException(409, f"store {req.store_code} tuần {week} đang được xếp lịch (run {busy[0]['run_id']})")
    who = user.email                                    # logged-in user, not the client-supplied requestedBy
    engine = get_engine()
    run_id = create_run(engine, req.store_code, week, aw, who)
    _EXECUTOR.submit(execute_run, run_id, req.store_code, week, aw, who, None, engine)
    return get_run(run_id, conn, user)


def _parse_optional(d: str | None) -> date | None:
    return parse_week(d) if d else None
