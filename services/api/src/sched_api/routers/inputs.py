"""Engine inputs: view + edit (UI or Excel upload) [DECISION 19-Nov-2026: input editing moves from the .NET app to the platform].

Reads go through sched.vw_input_*; writes go to the dbo tables via `input_edit` / `excel_io`. Permissions are the .NET codes
(see auth.py); every call is limited to the user's stores.
"""
from __future__ import annotations

from datetime import date

from auto_scheduling.settings import get_settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import Connection

from .. import excel_io as xl
from .. import input_edit as ed
from ..auth import AVAILABILITY_EDIT, CONFIG_EDIT, EMPLOYEE_EDIT, HOURS_EDIT, INPUT_VIEW, User, ensure_store, require
from ..deps import get_conn, meta, parse_week, rows
from ..schemas import (
    AvailabilityCopyIn,
    AvailabilityItem,
    AvailabilityWeekIn,
    EmployeeIn,
    EmployeeItem,
    EmployeeUpdate,
    Envelope,
    ImportResult,
    InputOptions,
    Saved,
    SecondmentIn,
    SecondmentItem,
    SecondmentUpdate,
    ShiftCodeItem,
    StoreConfig,
    StoreConfigIn,
)

router = APIRouter(prefix="/inputs", tags=["inputs"])
MAX_UPLOAD = 5 * 1024 * 1024
EMP_ORDER = ("CASE WHEN Status = N'Active' THEN 0 ELSE 1 END, CASE WHEN Position LIKE '%Store Manager%' THEN 1 WHEN Position LIKE '%Assistant%' "
             "THEN 2 WHEN Position LIKE '%Supervisor%' THEN 3 WHEN Position LIKE '%Trainer%' THEN 4 ELSE 5 END, EmploymentType, EmployeeName")


def _date(s: str, label: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise HTTPException(422, f"{label}: ngày không hợp lệ ({s})") from exc


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content, media_type=xl.XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "File quá lớn (tối đa 5 MB)")
    if not content.startswith(b"PK"):
        raise HTTPException(422, "File phải là Excel .xlsx")
    return content


# ------------------------------------------------------------------ options
@router.get("/options", response_model=InputOptions)
def options(store: str | None = Query(None, max_length=10), conn: Connection = Depends(get_conn),
            user: User = Depends(require(*INPUT_VIEW))) -> dict:
    weeks: list[str] = []
    if store:
        ensure_store(user, store)
        weeks = [r["week_start"] for r in rows(conn, "SELECT DISTINCT WeekStart FROM sched.vw_input_availability WHERE StoreCode = :s "
                                                     "ORDER BY WeekStart DESC", s=store)]
    default = get_settings().default_availability_week
    if default and default not in weeks:
        weeks.insert(0, default)
    return {"positions": list(ed.POSITIONS), "employment_types": list(ed.EMPLOYMENT_TYPES), "labor_groups": list(ed.LABOR_GROUPS),
            "statuses": list(ed.STATUSES), "availability_weeks": weeks}


# ------------------------------------------------------------------ shift codes (dbo.dim_shift_code)
@router.get("/shift-codes", response_model=Envelope[list[ShiftCodeItem]])
def shift_codes(active_only: bool = Query(True), conn: Connection = Depends(get_conn), _: User = Depends(require(*INPUT_VIEW))) -> dict:
    """Attendance shift codes (HR). The engine matches a shift to a code by exact (start, end); when several codes share the
    same times the lowest sortOrder wins. isOvernight = the shift ends the next day."""
    sql = "SELECT * FROM sched.vw_input_shift_code" + (" WHERE IsActive = 1" if active_only else "") + " ORDER BY StartTime, EndTime, SortOrder"
    return {"data": rows(conn, sql), "meta": meta(conn)}


# ------------------------------------------------------------------ store config
@router.get("/store-config", response_model=Envelope[list[StoreConfig]])
def store_config(store: str | None = Query(None, max_length=10), all_stores: bool = Query(False, description="also stores without a target"),
                 conn: Connection = Depends(get_conn), user: User = Depends(require(*INPUT_VIEW))) -> dict:
    where = " WHERE StoreCode = :s" if store else ("" if all_stores else " WHERE TcphTarget IS NOT NULL")
    data = [r for r in rows(conn, "SELECT * FROM sched.vw_input_store_config" + where + " ORDER BY StoreCode", s=store)
            if user.can_store(r["store_code"])]
    return {"data": data, "meta": meta(conn)}


@router.put("/store-config/{store}", response_model=Saved)
def save_store_config(store: str, body: StoreConfigIn, conn: Connection = Depends(get_conn), user: User = Depends(require(*CONFIG_EDIT))) -> dict:
    ensure_store(user, store)
    cur = ed.current_hours(conn, store)
    hours_changed = body.opening_time is not None and body.closing_time is not None and cur is not None and \
        (body.opening_time, body.closing_time) != cur
    if hours_changed:
        if not user.can(HOURS_EDIT):
            raise HTTPException(403, "Đổi giờ mở / đóng cửa cần quyền quản lý store")
        ed.set_hours(conn, store, body.opening_time, body.closing_time)
    ed.upsert_config(conn, store, body.tcph_target, body.tcph_ceiling_mult, body.open_staff, body.close_staff, body.min_staff_per_slot,
                     user.email)
    ed.bump(conn, user.email, f"cấu hình store {store}" + (" + giờ mở/đóng" if hours_changed else ""))
    conn.commit()
    return {"message": f"Đã lưu cấu hình store {store}"}


# ------------------------------------------------------------------ employees
@router.get("/employees", response_model=Envelope[list[EmployeeItem]])
def employees(store: str = Query(..., max_length=10), conn: Connection = Depends(get_conn), user: User = Depends(require(*INPUT_VIEW))) -> dict:
    ensure_store(user, store)
    return {"data": rows(conn, f"SELECT * FROM sched.vw_input_employees WHERE StoreCode = :s ORDER BY {EMP_ORDER}", s=store), "meta": meta(conn)}


@router.post("/employees", response_model=Saved, status_code=201)
def add_employee(body: EmployeeIn, conn: Connection = Depends(get_conn), user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    ensure_store(user, body.store_code)
    ed.create_employee(conn, body.store_code, body.employee_id, body.employee_name, body.position, body.employment_type, body.labor_group,
                       body.status, user.email)
    conn.commit()
    return {"message": f"Đã thêm {body.employee_name}"}


@router.put("/employees/{employee_id}", response_model=Saved)
def edit_employee(employee_id: str, body: EmployeeUpdate, conn: Connection = Depends(get_conn),
                  user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    old = ed.employee_row(conn, employee_id)
    if old is None:
        raise HTTPException(404, f"Không có nhân viên {employee_id}")
    ensure_store(user, old.PlantCode)
    ed.update_employee(conn, employee_id, body.employee_name, body.position, body.employment_type, body.labor_group, body.status, user.email)
    conn.commit()
    return {"message": f"Đã lưu {body.employee_name}"}


# ------------------------------------------------------------------ availability
@router.get("/availability", response_model=Envelope[list[AvailabilityItem]])
def availability(store: str = Query(..., max_length=10), week: str | None = Query(None), conn: Connection = Depends(get_conn),
                 user: User = Depends(require(*INPUT_VIEW))) -> dict:
    ensure_store(user, store)
    if week:
        data = rows(conn, "SELECT * FROM sched.vw_input_availability WHERE StoreCode = :s AND WeekStart = :w ORDER BY EmployeeName, WorkDate",
                    s=store, w=parse_week(week))
    else:
        data = rows(conn, "SELECT * FROM sched.vw_input_availability WHERE StoreCode = :s ORDER BY WeekStart DESC, EmployeeName, WorkDate", s=store)
    return {"data": data, "meta": meta(conn)}


@router.put("/availability/{store}/{week}", response_model=Saved)
def save_availability(store: str, week: str, body: AvailabilityWeekIn, conn: Connection = Depends(get_conn),
                      user: User = Depends(require(*AVAILABILITY_EDIT))) -> dict:
    ensure_store(user, store)
    wk = parse_week(week)
    for it in body.items:
        ed.upsert_availability_day(conn, store, wk, it.employee_id, _date(it.work_date, "Ngày"), it.busy_from, it.busy_to, it.is_paid_leave)
    ed.bump(conn, user.email, f"lịch bận store {store} tuần {wk} ({len(body.items)} ô)")
    conn.commit()
    return {"message": f"Đã lưu {len(body.items)} ô lịch bận"}


@router.post("/availability/{store}/{week}/copy", response_model=Saved)
def copy_availability(store: str, week: str, body: AvailabilityCopyIn, conn: Connection = Depends(get_conn),
                      user: User = Depends(require(*AVAILABILITY_EDIT))) -> dict:
    ensure_store(user, store)
    n = ed.copy_availability_week(conn, store, parse_week(body.source_week), parse_week(week), user.email)
    conn.commit()
    return {"message": f"Đã chép {n} dòng lịch bận sang tuần {week}"}


# ------------------------------------------------------------------ secondments
@router.get("/secondments", response_model=Envelope[list[SecondmentItem]])
def secondments(store: str | None = Query(None, max_length=10), conn: Connection = Depends(get_conn),
                user: User = Depends(require(*INPUT_VIEW))) -> dict:
    sql = "SELECT * FROM sched.vw_input_secondment" + (" WHERE HomeStore = :s OR ReceivingStore = :s" if store else "") + \
          " ORDER BY StartDate DESC"
    data = [r for r in rows(conn, sql, s=store) if user.can_store(r["home_store"]) or user.can_store(r["receiving_store"])]
    return {"data": data, "meta": meta(conn)}


@router.post("/secondments", response_model=Saved, status_code=201)
def add_secondment(body: SecondmentIn, conn: Connection = Depends(get_conn), user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    ensure_store(user, body.home_store)
    ed.create_secondment(conn, body.employee_id, body.home_store, body.receiving_store, _date(body.start_date, "Từ ngày"),
                         _date(body.end_date, "Đến ngày"), user.email)
    conn.commit()
    return {"message": "Đã thêm dòng cho mượn"}


@router.put("/secondments/{sec_id}", response_model=Saved)
def edit_secondment(sec_id: int, body: SecondmentUpdate, conn: Connection = Depends(get_conn),
                    user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    ensure_store(user, ed.secondment_row(conn, sec_id).HomePlantCode)
    ed.update_secondment(conn, sec_id, body.receiving_store, _date(body.start_date, "Từ ngày"), _date(body.end_date, "Đến ngày"), user.email)
    conn.commit()
    return {"message": "Đã lưu"}


@router.delete("/secondments/{sec_id}", response_model=Saved)
def remove_secondment(sec_id: int, conn: Connection = Depends(get_conn), user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    ensure_store(user, ed.secondment_row(conn, sec_id).HomePlantCode)
    ed.delete_secondment(conn, sec_id, user.email)
    conn.commit()
    return {"message": "Đã xóa"}


# ------------------------------------------------------------------ Excel: download current data / upload to replace
@router.get("/excel/availability-file", response_class=Response, responses={200: {"content": {xl.XLSX: {}}}})
def download_availability_file(store: str = Query(..., max_length=10), week: str = Query(...), conn: Connection = Depends(get_conn),
                               user: User = Depends(require(*INPUT_VIEW))) -> Response:
    ensure_store(user, store)
    wk = parse_week(week)
    return _xlsx(xl.export_availability_file(conn, store, wk), f"Availability File {store} {wk:%Y%m%d}.xlsx")


@router.post("/excel/availability-file", response_model=ImportResult)
async def upload_availability_file(store: str = Form(..., max_length=10), week: str = Form(...), replace_employees: bool = Form(False),
                                   replace_busy: bool = Form(False), apply: bool = Form(False), file: UploadFile = File(...),
                                   conn: Connection = Depends(get_conn), user: User = Depends(require(*INPUT_VIEW))) -> dict:
    """apply=false: preview only. Employees missing from the file become Inactive; the busy rows of `week` are replaced."""
    ensure_store(user, store)
    if replace_employees and not user.can(EMPLOYEE_EDIT):
        raise HTTPException(403, "Thay danh sách nhân viên cần quyền quản lý nhân viên")
    if replace_busy and not user.can(AVAILABILITY_EDIT):
        raise HTTPException(403, "Thay lịch bận cần quyền quản lý lịch bận")
    wk = parse_week(week)
    plan = xl.plan_availability_file(conn, store, wk, await _read_upload(file), replace_employees, replace_busy)
    return _finish(conn, plan, apply, user, f"Availability File store {store} tuần {wk} ({file.filename})")


@router.get("/excel/secondments", response_class=Response, responses={200: {"content": {xl.XLSX: {}}}})
def download_secondments(store: str = Query(..., max_length=10), conn: Connection = Depends(get_conn),
                         user: User = Depends(require(*INPUT_VIEW))) -> Response:
    ensure_store(user, store)
    return _xlsx(xl.export_secondments(conn, store), f"Cho muon nhan su {store}.xlsx")


@router.post("/excel/secondments", response_model=ImportResult)
async def upload_secondments(store: str = Form(..., max_length=10), apply: bool = Form(False), file: UploadFile = File(...),
                             conn: Connection = Depends(get_conn), user: User = Depends(require(*EMPLOYEE_EDIT))) -> dict:
    ensure_store(user, store)
    plan = xl.plan_secondments(conn, store, await _read_upload(file), user.email)
    return _finish(conn, plan, apply, user, f"cho mượn store {store} ({file.filename})")


@router.get("/excel/store-config", response_class=Response, responses={200: {"content": {xl.XLSX: {}}}})
def download_store_config(conn: Connection = Depends(get_conn), user: User = Depends(require(*INPUT_VIEW))) -> Response:
    return _xlsx(xl.export_store_config(conn, None if user.all_stores else sorted(user.stores)), "Cau hinh store.xlsx")


@router.post("/excel/store-config", response_model=ImportResult)
async def upload_store_config(apply: bool = Form(False), file: UploadFile = File(...), conn: Connection = Depends(get_conn),
                              user: User = Depends(require(*CONFIG_EDIT))) -> dict:
    plan = xl.plan_store_config(conn, await _read_upload(file), user.can_store, user.can(HOURS_EDIT), user.email)
    return _finish(conn, plan, apply, user, f"cấu hình store ({file.filename})")


def _finish(conn: Connection, plan: xl.Plan, apply: bool, user: User, detail: str) -> dict:
    if apply:
        if plan.errors:
            raise HTTPException(422, "File còn lỗi, chưa ghi gì: " + "; ".join(plan.errors[:5]))
        xl.apply_plan(conn, plan, user.email, detail)
        conn.commit()
    return plan.result(applied=apply)
