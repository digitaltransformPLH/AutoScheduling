"""Edit engine inputs in the dbo tables of the ASP.NET app [DECISION 19-Nov-2026: input editing moves to the platform].

Tables written: dim_employee, employee_availability_slot, employee_secondment, ops_store_config, dim_store_detail (OpenTime /
CloseTime only). Every change bumps sched.meta_build (data_version, BuiltBy = user email) so the web refreshes and the change
is traceable. Callers commit; functions raise HTTPException with a Vietnamese message on bad input.
"""
from __future__ import annotations

from datetime import date, time, timedelta

from auto_scheduling.config import VALID_LABOR_GROUPS
from auto_scheduling.etl.load_inputs import _bump_version
from auto_scheduling.timeutil import parse_hhmm
from fastapi import HTTPException
from sqlalchemy import Connection, text

POSITIONS = ("Store Manager", "Assistant Store Manager", "Shift Supervisor", "Barista Trainer", "Crew member")
EMPLOYMENT_TYPES = ("FT", "PT")
LABOR_GROUPS = VALID_LABOR_GROUPS
STATUSES = ("Active", "Inactive")
NOW = "SYSDATETIMEOFFSET()"


def bump(conn: Connection, user_email: str, detail: str) -> int:
    return _bump_version(conn, "inputs", f"{user_email}: {detail}", user_email)


# ------------------------------------------------------------------ lookups
def store_db_id(conn: Connection, store: str) -> int:
    sid = conn.execute(text("SELECT Id FROM dbo.dim_store WHERE Code = :c"), {"c": store}).scalar()
    if sid is None:
        raise HTTPException(404, f"Không có store {store}")
    return int(sid)


def employee_row(conn: Connection, employee_id: str):
    if not str(employee_id).isdigit():
        raise HTTPException(422, f"Mã nhân viên phải là số: {employee_id}")
    return conn.execute(text("SELECT Id, EmployeeNumber, PlantCode, FullName, Position, EmploymentType, LaborGroup, Status "
                             "FROM dbo.dim_employee WHERE EmployeeNumber = :n"), {"n": int(employee_id)}).first()


def hhmm(value: str | None, field: str) -> time | None:
    if value in (None, ""):
        return None
    m = parse_hhmm(value)
    if m is None or not 0 <= m <= 1440:
        raise HTTPException(422, f"{field}: giờ không hợp lệ ({value}), dùng dạng HH:mm")
    m = min(m, 1439)                                    # SQL time has no 24:00
    return time(m // 60, m % 60)


# ------------------------------------------------------------------ employees
def check_employee_fields(name: str, position: str, employment_type: str, labor_group: str, status: str) -> None:
    if not name.strip():
        raise HTTPException(422, "Thiếu họ tên")
    for value, allowed, label in ((position, POSITIONS, "Vị trí"), (employment_type, EMPLOYMENT_TYPES, "FT/PT"),
                                  (labor_group, LABOR_GROUPS, "Nhóm"), (status, STATUSES, "Trạng thái")):
        if value not in allowed:
            raise HTTPException(422, f"{label} phải là một trong: {', '.join(allowed)} (đang là {value!r})")


def create_employee(conn: Connection, store: str, employee_id: str, name: str, position: str, employment_type: str,
                    labor_group: str, status: str, user_email: str) -> None:
    store_db_id(conn, store)
    check_employee_fields(name, position, employment_type, labor_group, status)
    old = employee_row(conn, employee_id)
    if old is not None:
        raise HTTPException(409, f"Mã nhân viên {employee_id} đã có ({old.FullName}, store {old.PlantCode})")
    conn.execute(text(f"INSERT INTO dbo.dim_employee (FullName, EmployeeNumber, PlantCode, Position, EmploymentType, LaborGroup, Status, "
                      f"CreatedAt, UpdatedAt) VALUES (:name, :n, :store, :pos, :et, :lg, :st, {NOW}, {NOW})"),
                 {"name": name.strip(), "n": int(employee_id), "store": store, "pos": position, "et": employment_type, "lg": labor_group,
                  "st": status})
    bump(conn, user_email, f"thêm nhân viên {employee_id} store {store}")


def update_employee(conn: Connection, employee_id: str, name: str, position: str, employment_type: str, labor_group: str, status: str,
                    user_email: str) -> None:
    check_employee_fields(name, position, employment_type, labor_group, status)
    conn.execute(text(f"UPDATE dbo.dim_employee SET FullName = :name, Position = :pos, EmploymentType = :et, LaborGroup = :lg, Status = :st, "
                      f"UpdatedAt = {NOW} WHERE EmployeeNumber = :n"),
                 {"name": name.strip(), "pos": position, "et": employment_type, "lg": labor_group, "st": status, "n": int(employee_id)})
    bump(conn, user_email, f"sửa nhân viên {employee_id}")


# ------------------------------------------------------------------ availability (1 row / employee / day; NULL = free)
def upsert_availability_day(conn: Connection, store: str, week: date, employee_id: str, work_date: date, busy_from: str | None,
                            busy_to: str | None, is_paid_leave: bool) -> None:
    if not week <= work_date <= week + timedelta(days=6):
        raise HTTPException(422, f"Ngày {work_date} không thuộc tuần {week}")
    emp = employee_row(conn, employee_id)
    if emp is None or emp.PlantCode != store:
        raise HTTPException(404, f"Nhân viên {employee_id} không thuộc store {store}")
    f, t = (None, None) if is_paid_leave else (hhmm(busy_from, "Bận từ"), hhmm(busy_to, "Bận đến"))
    if (f is None) != (t is None) or (f is not None and t <= f):
        raise HTTPException(422, f"{emp.FullName} {work_date:%d/%m}: 'Bận từ' phải trước 'Bận đến' (hoặc để trống cả hai = rảnh)")
    p = {"s": store, "n": int(employee_id), "i": emp.Id, "w": week, "d": work_date, "f": f, "t": t, "al": bool(is_paid_leave)}
    n = conn.execute(text(f"UPDATE dbo.employee_availability_slot SET BusyFrom = :f, BusyTo = :t, IsPaidLeave = :al, EmployeeId = :i, "
                          f"WeekStartMonday = :w, UpdatedAt = {NOW} WHERE PlantCode = :s AND EmployeeNumber = :n AND WorkDate = :d"), p).rowcount
    if n == 0:
        conn.execute(text(f"INSERT INTO dbo.employee_availability_slot (PlantCode, EmployeeNumber, EmployeeId, WeekStartMonday, WorkDate, "
                          f"BusyFrom, BusyTo, IsPaidLeave, CreatedAt, UpdatedAt) VALUES (:s, :n, :i, :w, :d, :f, :t, :al, {NOW}, {NOW})"), p)


def copy_availability_week(conn: Connection, store: str, source: date, target: date, user_email: str) -> int:
    """Replace the target week with the source week, day by day (Mon -> Mon ...), active employees only."""
    if source == target:
        raise HTTPException(422, "Tuần nguồn và tuần đích trùng nhau")
    conn.execute(text("DELETE FROM dbo.employee_availability_slot WHERE PlantCode = :s AND WeekStartMonday = :w"), {"s": store, "w": target})
    n = conn.execute(text(
        f"INSERT INTO dbo.employee_availability_slot (PlantCode, EmployeeNumber, EmployeeId, WeekStartMonday, WorkDate, BusyFrom, BusyTo, "
        f"IsPaidLeave, CreatedAt, UpdatedAt) "
        f"SELECT a.PlantCode, a.EmployeeNumber, e.Id, :t, DATEADD(DAY, DATEDIFF(DAY, :src, :t), a.WorkDate), a.BusyFrom, a.BusyTo, a.IsPaidLeave, "
        f"{NOW}, {NOW} FROM dbo.employee_availability_slot a JOIN dbo.dim_employee e ON e.EmployeeNumber = a.EmployeeNumber "
        f"WHERE a.PlantCode = :s AND a.WeekStartMonday = :src AND e.PlantCode = :s AND e.Status = N'Active'"),
        {"s": store, "src": source, "t": target}).rowcount
    bump(conn, user_email, f"chép lịch bận store {store} tuần {source} → {target} ({n} dòng)")
    return n


# ------------------------------------------------------------------ secondments
def _check_secondment(conn: Connection, employee_id: str, home: str, receiving: str, start: date, end: date, skip_id: int | None = None):
    emp = employee_row(conn, employee_id)
    if emp is None or emp.PlantCode != home:
        raise HTTPException(404, f"Nhân viên {employee_id} không thuộc store {home}")
    if receiving == home:
        raise HTTPException(422, "Store nhận phải khác store gốc")
    store_db_id(conn, receiving)
    if end < start:
        raise HTTPException(422, "'Đến ngày' phải sau hoặc bằng 'Từ ngày'")
    clash = conn.execute(text("SELECT TOP 1 ReceivingStoreCode, StartDate, EndDate FROM dbo.employee_secondment WHERE EmployeeId = :e "
                              "AND Status = N'Active' AND StartDate <= :end AND EndDate >= :start AND (:skip IS NULL OR Id <> :skip)"),
                         {"e": emp.Id, "start": start, "end": end, "skip": skip_id}).first()
    if clash:
        raise HTTPException(409, f"{emp.FullName} đã được cho store {clash[0]} mượn {clash[1]:%d/%m}–{clash[2]:%d/%m}")
    return emp


def create_secondment(conn: Connection, employee_id: str, home: str, receiving: str, start: date, end: date, user_email: str) -> None:
    emp = _check_secondment(conn, employee_id, home, receiving, start, end)
    conn.execute(text(f"INSERT INTO dbo.employee_secondment (EmployeeId, HomePlantCode, ReceivingStoreCode, StartDate, EndDate, Status, "
                      f"CreatedAt, UpdatedAt, UpdatedBy) VALUES (:e, :h, :r, :s, :t, N'Active', {NOW}, {NOW}, :u)"),
                 {"e": emp.Id, "h": home, "r": receiving, "s": start, "t": end, "u": user_email})
    bump(conn, user_email, f"cho mượn {employee_id}: {home} → {receiving} {start}..{end}")


def secondment_row(conn: Connection, sec_id: int):
    r = conn.execute(text("SELECT s.Id, s.HomePlantCode, s.ReceivingStoreCode, CAST(e.EmployeeNumber AS NVARCHAR(20)) AS EmployeeNumber "
                          "FROM dbo.employee_secondment s JOIN dbo.dim_employee e ON e.Id = s.EmployeeId WHERE s.Id = :i"), {"i": sec_id}).first()
    if r is None:
        raise HTTPException(404, f"Không có dòng cho mượn {sec_id}")
    return r


def update_secondment(conn: Connection, sec_id: int, receiving: str, start: date, end: date, user_email: str) -> None:
    old = secondment_row(conn, sec_id)
    _check_secondment(conn, old.EmployeeNumber, old.HomePlantCode, receiving, start, end, skip_id=sec_id)
    conn.execute(text(f"UPDATE dbo.employee_secondment SET ReceivingStoreCode = :r, StartDate = :s, EndDate = :t, UpdatedAt = {NOW}, "
                      f"UpdatedBy = :u WHERE Id = :i"), {"r": receiving, "s": start, "t": end, "u": user_email, "i": sec_id})
    bump(conn, user_email, f"sửa cho mượn #{sec_id}")


def delete_secondment(conn: Connection, sec_id: int, user_email: str) -> None:
    conn.execute(text("DELETE FROM dbo.employee_secondment WHERE Id = :i"), {"i": sec_id})
    bump(conn, user_email, f"xóa cho mượn #{sec_id}")


# ------------------------------------------------------------------ store config (ops_store_config) + hours (dim_store_detail)
def check_config(tcph_target: float, tcph_ceiling_mult: float, open_staff: int, close_staff: int, min_staff: int) -> None:
    if not 0 < tcph_target <= 50:
        raise HTTPException(422, "TCPH target phải > 0")
    if not 1 <= tcph_ceiling_mult <= 2:
        raise HTTPException(422, "Hệ số trần phải trong khoảng 1–2")
    if min(open_staff, close_staff, min_staff) < 1 or max(open_staff, close_staff, min_staff) > 20:
        raise HTTPException(422, "Số người mở ca / đóng ca / tối thiểu phải từ 1 đến 20")


def current_hours(conn: Connection, store: str) -> tuple[str | None, str | None] | None:
    r = conn.execute(text("SELECT OpenTime, CloseTime FROM dbo.dim_store_detail WHERE StoreCode = :c"), {"c": store}).first()
    return None if r is None else (r[0], r[1])


def set_hours(conn: Connection, store: str, opening: str, closing: str) -> None:
    o, c = hhmm(opening, "Giờ mở cửa"), hhmm(closing, "Giờ đóng cửa")
    if o is None or c is None:
        raise HTTPException(422, "Thiếu giờ mở / đóng cửa")
    if current_hours(conn, store) is None:
        raise HTTPException(404, f"Store {store} chưa có dòng dim_store_detail (tạo trên app .NET)")
    close_txt = "24:00" if closing.strip() in ("24:00", "00:00") and o.hour == 0 else f"{c:%H:%M}"
    if close_txt != "24:00" and c <= o:
        raise HTTPException(422, "Giờ đóng cửa phải sau giờ mở cửa")
    conn.execute(text("UPDATE dbo.dim_store_detail SET OpenTime = :o, CloseTime = :c WHERE StoreCode = :s"),
                 {"o": f"{o:%H:%M}", "c": close_txt, "s": store})


def upsert_config(conn: Connection, store: str, tcph_target: float, tcph_ceiling_mult: float, open_staff: int, close_staff: int,
                  min_staff: int, user_email: str) -> None:
    check_config(tcph_target, tcph_ceiling_mult, open_staff, close_staff, min_staff)
    sid = store_db_id(conn, store)
    p = {"s": sid, "t": tcph_target, "m": tcph_ceiling_mult, "o": open_staff, "c": close_staff, "n": min_staff, "u": user_email}
    n = conn.execute(text(f"UPDATE dbo.ops_store_config SET tcph_target = :t, tcph_ceiling_mult = :m, open_staff = :o, close_staff = :c, "
                          f"min_staff_per_slot = :n, updated_at = {NOW}, updated_by = :u WHERE store_id = :s"), p).rowcount
    if n == 0:
        conn.execute(text(f"INSERT INTO dbo.ops_store_config (store_id, tcph_target, tcph_ceiling_mult, open_staff, close_staff, "
                          f"min_staff_per_slot, created_at, updated_at, updated_by) VALUES (:s, :t, :m, :o, :c, :n, {NOW}, {NOW}, :u)"), p)
