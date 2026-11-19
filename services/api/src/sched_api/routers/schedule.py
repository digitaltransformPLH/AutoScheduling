"""Stores, forecast weeks and suggested rosters (read-only, views sched.vw_*). Only the stores assigned to the user (dbo.UserStores)."""
from __future__ import annotations

import io
import re
from datetime import datetime, timedelta

from auto_scheduling.output.attendance import COL_WIDTHS, HEADERS, TEMPLATE, attendance_store_code
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import Connection

from ..auth import SCHEDULE_VIEW, User, current_user, ensure_store, require
from ..deps import get_conn, meta, parse_week, rows
from ..schemas import Envelope, ForecastWeek, Meta, Overview, RosterDay, ScheduleWeek, StoreItem

router = APIRouter(tags=["schedule"])

WORK = "Làm"
AL = "Nghỉ phép"
AWAY = "Đi hỗ trợ"                 # paid hours at the home store, never OFF [DECISION 19-Nov-2026]
PAID = (WORK, AL, AWAY)


@router.get("/meta", response_model=Meta)
def get_meta(conn: Connection = Depends(get_conn), _: User = Depends(current_user)) -> dict:
    return meta(conn)


@router.get("/stores", response_model=Envelope[list[StoreItem]])
def list_stores(ready_only: bool = Query(False, description="only stores with hours, tcph target and employees"),
                conn: Connection = Depends(get_conn), user: User = Depends(current_user)) -> dict:
    sql = "SELECT * FROM sched.vw_store_list" + (" WHERE ReadyToSchedule = 1" if ready_only else "") + \
          " ORDER BY ReadyToSchedule DESC, ScheduledWeeks DESC, StoreCode"
    return {"data": [r for r in rows(conn, sql) if user.can_store(r["store_code"])], "meta": meta(conn)}


@router.get("/forecast-weeks", response_model=Envelope[list[ForecastWeek]])
def forecast_weeks(conn: Connection = Depends(get_conn), _: User = Depends(current_user)) -> dict:
    return {"data": rows(conn, "SELECT * FROM sched.vw_forecast_weeks ORDER BY WeekStart DESC"), "meta": meta(conn)}


@router.get("/schedules", response_model=Envelope[list[ScheduleWeek]])
def list_schedules(store: str | None = Query(None, max_length=10), conn: Connection = Depends(get_conn),
                   user: User = Depends(require(*SCHEDULE_VIEW))) -> dict:
    sql = "SELECT * FROM sched.vw_schedule_week" + (" WHERE StoreCode = :s" if store else "") + " ORDER BY WeekStart DESC, StoreCode"
    return {"data": [r for r in rows(conn, sql, s=store) if user.can_store(r["store_code"])], "meta": meta(conn)}


def _week_or_404(conn: Connection, store: str, week) -> dict:
    w = rows(conn, "SELECT * FROM sched.vw_schedule_week WHERE StoreCode = :s AND WeekStart = :w", s=store, w=week)
    if not w:
        raise HTTPException(404, f"chưa có lịch cho store {store} tuần {week}")
    return w[0]


@router.get("/schedules/{store}/{week}/overview", response_model=Envelope[Overview])
def schedule_overview(store: str, week: str, conn: Connection = Depends(get_conn), user: User = Depends(require(*SCHEDULE_VIEW))) -> dict:
    ensure_store(user, store)
    wk = parse_week(week)
    data = {
        "week": _week_or_404(conn, store, wk),
        "days": rows(conn, "SELECT * FROM sched.vw_schedule_daily WHERE StoreCode = :s AND WeekStart = :w ORDER BY WorkDate", s=store, w=wk),
        "hourly": rows(conn, "SELECT * FROM sched.vw_schedule_hourly WHERE StoreCode = :s AND WeekStart = :w ORDER BY WorkDate, Slot",
                       s=store, w=wk),
        "roster": rows(conn, "SELECT * FROM sched.vw_schedule_roster WHERE StoreCode = :s AND WeekStart = :w ORDER BY SortOrder, WorkDate",
                       s=store, w=wk),
        "issues": rows(conn, "SELECT * FROM sched.vw_schedule_issues WHERE StoreCode = :s AND WeekStart = :w ORDER BY Id", s=store, w=wk),
    }
    return {"data": data, "meta": meta(conn)}


@router.get("/schedules/{store}/{week}/roster", response_model=Envelope[list[RosterDay]])
def schedule_roster(store: str, week: str, conn: Connection = Depends(get_conn), user: User = Depends(require(*SCHEDULE_VIEW))) -> dict:
    ensure_store(user, store)
    wk = parse_week(week)
    _week_or_404(conn, store, wk)
    data = rows(conn, "SELECT * FROM sched.vw_schedule_roster WHERE StoreCode = :s AND WeekStart = :w ORDER BY SortOrder, WorkDate",
                s=store, w=wk)
    return {"data": data, "meta": meta(conn)}


@router.get("/schedules/{store}/{week}/file2", response_class=StreamingResponse,
            responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}})
def export_file2(store: str, week: str, conn: Connection = Depends(get_conn), user: User = Depends(require(*SCHEDULE_VIEW))):
    """File 2 'Upload Phân Công' (SPEC 7.2) built from sched.ScheduleRoster. Secondment days keep their paid hours; not scheduled = OFF."""
    ensure_store(user, store)
    wk = parse_week(week)
    w = _week_or_404(conn, store, wk)
    data = rows(conn, "SELECT * FROM sched.vw_schedule_roster WHERE StoreCode = :s AND WeekStart = :w AND HomeStore IS NULL "
                      "ORDER BY SortOrder, WorkDate", s=store, w=wk)
    missing = [r for r in data if r["day_type"] in PAID and not r["shift_code"]]
    if missing:
        msg = "; ".join(f"{r['employee_id']} - {r['employee_name']} - {r['work_date']}: {r['start_time']}-{r['end_time']}" for r in missing[:20])
        raise HTTPException(409, f"ca không có mã chấm công: {msg}")
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS)
    code_cell = attendance_store_code(store)
    for r in data:
        ds = datetime.fromisoformat(r["work_date"]).strftime("%d.%m.%Y")
        base = [code_cell, r["employee_id"], r["employee_name"], TEMPLATE, ds, ds]
        if r["day_type"] in PAID:
            code = r["shift_code"]
            st = datetime.strptime(r["start_time"], "%H:%M").time()
            en = datetime.strptime(r["end_time"], "%H:%M").time()
            ws.append(base + [int(code) if code.isdigit() else code, st, en])
            ws.cell(ws.max_row, 8).number_format = ws.cell(ws.max_row, 9).number_format = "HH:mm"
        else:
            ws.append(base + ["OFF", None, None])
    for i, width in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    short = re.sub(r"[^A-Za-z0-9]+", "_", _ascii(w["store_name"] or store)).strip("_")
    name = f"{store}_{short}_Upload_Phan_Cong_{wk:%Y%m%d}-{wk + timedelta(days=6):%Y%m%d}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _ascii(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode()
