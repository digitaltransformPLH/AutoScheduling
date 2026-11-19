"""Excel round-trip for the input screens: download the current data, edit, upload to replace [DECISION 19-Nov-2026].

* Availability File (same layout the stores already use): sheet "Employee Master" + sheet "Availability" (7 rows / employee).
  Replace = employees of the store missing from the file become Inactive (history kept); the busy rows of the chosen week are
  replaced. Either part can be replaced on its own (different permissions).
* Secondments: sheet "Cho mượn"; replace = all secondments whose home store is the chosen store.
* Store config: sheet "Cấu hình store"; updates only the stores listed (blank target = no change).

Every import is planned first (`apply=False` -> preview of changes and errors); `apply=True` writes the same plan. Any error
blocks the whole import, so a skipped row can never turn an employee Inactive by mistake.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import pandas as pd
from auto_scheduling.etl.load_inputs import read_workbook
from auto_scheduling.inputs.loaders import norm_id, parse_employment_type, parse_labor_group
from auto_scheduling.timeutil import norm_text, parse_hhmm
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import Connection, text

from . import input_edit as ed

WEEKDAYS_VI = ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật")
EMP_HEADERS = ["Employee Name", "Employee ID", "Position", "Employment Type", "Labor group", "Status"]
AV_HEADERS = ["Employee Name", "Employee ID", "Position", "Employment Type", "Ngày", "Bận từ", "Bận đến"]
SEC_SHEET = "Cho mượn"
SEC_HEADERS = ["Mã NV", "Họ tên", "Store gốc", "Store nhận", "Từ ngày", "Đến ngày"]
CFG_SHEET = "Cấu hình store"
CFG_HEADERS = ["Mã store", "Tên store", "Giờ mở cửa", "Giờ đóng cửa", "TCPH target", "Hệ số trần", "Số người mở ca", "Số người đóng ca",
               "Tối thiểu mỗi giờ"]
HEADER_FILL = PatternFill("solid", fgColor="035F1D")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class Change:
    action: str                 # Thêm / Cập nhật / Ngừng làm / Chuyển store / Thay lịch bận / Xóa / Giữ nguyên
    key: str
    name: str = ""
    detail: str = ""


@dataclass
class Plan:
    summary: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ops: list = field(default_factory=list)          # callables(conn) run in order on apply

    def result(self, applied: bool) -> dict:
        return {"applied": applied, "can_apply": not self.errors, "summary": self.summary, "errors": self.errors[:50],
                "warnings": self.warnings[:50], "changes": [c.__dict__ for c in self.changes if c.action != "Giữ nguyên"][:500]}


# ------------------------------------------------------------------ helpers
def _sheet(wb: Workbook, title: str, headers: list[str], widths: list[int]):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
        c = ws.cell(1, i)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), HEADER_FILL
    ws.freeze_panes = "A2"
    return ws


def _list_validation(ws, values: tuple[str, ...], col: str, rows: int = 2000) -> None:
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col}2:{col}{rows}")


def _save(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip().lower() in ("", "nan", "none", "nat")


def _date(v) -> date | None:
    if _blank(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _num(v) -> float | None:
    if _blank(v):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _t(minutes: int | None) -> time | None:
    if minutes is None:
        return None
    m = min(int(minutes), 1439)
    return time(m // 60, m % 60)


def _position(v: str) -> str | None:
    r = norm_text(v)
    for p in ed.POSITIONS:
        if r == norm_text(p) or (p == "Crew member" and r in ("crew", "crewmember")):
            return p
    return None


def _status(v: str) -> str | None:
    r = norm_text(v)
    return "Active" if r in ("active", "") else "Inactive" if r in ("inactive", "nghiviec", "terminated", "resigned") else None


# ------------------------------------------------------------------ availability file (employees + busy of one week)
def export_availability_file(conn: Connection, store: str, week: date) -> bytes:
    emps = conn.execute(text("SELECT EmployeeId, EmployeeName, Position, EmploymentType, LaborGroup, Status FROM sched.vw_input_employees "
                             "WHERE StoreCode = :s ORDER BY CASE WHEN Status = N'Active' THEN 0 ELSE 1 END, EmployeeName"), {"s": store}).fetchall()
    busy = {(r.EmployeeId, r.WorkDate): r for r in conn.execute(text(
        "SELECT CAST(EmployeeNumber AS NVARCHAR(20)) AS EmployeeId, WorkDate, BusyFrom, BusyTo, IsPaidLeave FROM dbo.employee_availability_slot "
        "WHERE PlantCode = :s AND WeekStartMonday = :w"), {"s": store, "w": week})}
    wb = Workbook()
    wb.remove(wb.active)
    ws = _sheet(wb, "Employee Master", EMP_HEADERS, [30, 14, 22, 16, 14, 12])
    for e in emps:
        ws.append([e.EmployeeName, int(e.EmployeeId), e.Position, e.EmploymentType, e.LaborGroup, e.Status])
    _list_validation(ws, ed.POSITIONS, "C")
    _list_validation(ws, ed.EMPLOYMENT_TYPES, "D")
    _list_validation(ws, ed.LABOR_GROUPS, "E")
    _list_validation(ws, ed.STATUSES, "F")
    av = _sheet(wb, "Availability", AV_HEADERS, [30, 14, 22, 16, 12, 12, 12])
    for e in emps:
        if e.Status != "Active":
            continue
        for i, wd in enumerate(WEEKDAYS_VI):
            b = busy.get((e.EmployeeId, week + timedelta(days=i)))
            f, t = (("AL", "AL") if b is not None and b.IsPaidLeave else (b.BusyFrom, b.BusyTo) if b is not None else (None, None))
            av.append([e.EmployeeName, int(e.EmployeeId), e.Position, e.EmploymentType, wd, f, t])
            for col in (6, 7):
                if isinstance(av.cell(av.max_row, col).value, time):
                    av.cell(av.max_row, col).number_format = "HH:mm"
    note = wb.create_sheet("Hướng dẫn")
    for line in (f"Store {store} · tuần lịch bận bắt đầu {week:%d/%m/%Y}",
                 "Employee Master: danh sách nhân viên. Nhân viên đang có trên hệ thống mà không có trong file sẽ chuyển Inactive (không xóa).",
                 "Availability: 7 dòng / nhân viên. 'Bận từ' / 'Bận đến' là GIỜ BẬN (HH:mm). Để trống = rảnh cả ngày. Bận cả ngày = không xếp ca.",
                 "Nghỉ phép: ghi AL vào 'Bận từ' và 'Bận đến'.",
                 "Giá trị hợp lệ — Position: " + ", ".join(ed.POSITIONS) + " · Employment Type: FT, PT · Labor group: Regular, Training, NSO "
                 "· Status: Active, Inactive"):
        note.append([line])
    note.column_dimensions["A"].width = 140
    return _save(wb)


def plan_availability_file(conn: Connection, store: str, week: date, content: bytes, replace_employees: bool, replace_busy: bool) -> Plan:
    plan = Plan()
    try:
        emp, avail = read_workbook(io.BytesIO(content), store)
    except Exception as exc:                                    # noqa: BLE001 - any parse error -> message for the user
        plan.errors.append(f"Không đọc được file: {exc.__class__.__name__}: {exc}")
        return plan
    if not replace_employees and not replace_busy:
        plan.errors.append("Chọn ít nhất 1 phần để thay: nhân viên hoặc lịch bận")
        return plan
    existing = {str(r.EmployeeNumber): r for r in conn.execute(text(
        "SELECT Id, EmployeeNumber, PlantCode, FullName, Position, EmploymentType, LaborGroup, Status FROM dbo.dim_employee WHERE PlantCode = :s"),
        {"s": store})}
    file_ids: list[str] = []
    rows: list[dict] = []
    for r in emp.to_dict("records"):
        eid = r["employee_id"]
        if not eid.isdigit():
            plan.errors.append(f"Employee Master: mã nhân viên {eid!r} không phải số")
            continue
        vals = {"name": r["name"], "position": _position(r["position"]), "et": parse_employment_type(r["employment_type"]),
                "lg": parse_labor_group(r["labor_group"]), "status": _status(r["status"])}
        bad = [f"{lbl} {r[src]!r}" for k, lbl, src in (("position", "Position", "position"), ("et", "Employment Type", "employment_type"),
                                                        ("lg", "Labor group", "labor_group"), ("status", "Status", "status")) if vals[k] is None]
        if not vals["name"]:
            bad.append("thiếu tên")
        if bad:
            plan.errors.append(f"Employee Master {eid} {r['name']}: không hợp lệ — {', '.join(bad)}")
            continue
        file_ids.append(eid)
        rows.append({"eid": eid, **vals})

    # ---- employees
    if replace_employees:
        others = {str(r.EmployeeNumber): r for r in conn.execute(text(
            "SELECT EmployeeNumber, PlantCode, FullName FROM dbo.dim_employee WHERE PlantCode <> :s AND EmployeeNumber IN :ids").bindparams(
            _expanding("ids")), {"s": store, "ids": [int(x) for x in file_ids] or [-1]})}
        n_add = n_upd = n_same = n_move = 0
        for r in rows:
            eid, old = r["eid"], existing.get(r["eid"])
            new = (r["name"], r["position"], r["et"], r["lg"], r["status"])
            if old is None and eid in others:
                o = others[eid]
                plan.changes.append(Change("Chuyển store", eid, r["name"], f"từ store {o.PlantCode} sang {store}"))
                plan.ops.append(_op_update_emp(eid, store, *new))
                n_move += 1
            elif old is None:
                plan.changes.append(Change("Thêm", eid, r["name"], f"{r['position']} · {r['et']} · {r['lg']}"))
                plan.ops.append(_op_insert_emp(eid, store, *new))
                n_add += 1
            elif (old.FullName, old.Position, old.EmploymentType, old.LaborGroup, old.Status) != new:
                diff = [f"{lbl}: {a} → {b}" for lbl, a, b in zip(("Tên", "Vị trí", "FT/PT", "Nhóm", "Trạng thái"),
                        (old.FullName, old.Position, old.EmploymentType, old.LaborGroup, old.Status), new, strict=True) if a != b]
                plan.changes.append(Change("Cập nhật", eid, r["name"], "; ".join(diff)))
                plan.ops.append(_op_update_emp(eid, store, *new))
                n_upd += 1
            else:
                n_same += 1
        gone = [o for k, o in existing.items() if k not in set(file_ids) and o.Status == "Active"]
        for o in gone:
            plan.changes.append(Change("Ngừng làm", str(o.EmployeeNumber), o.FullName, "không có trong file → Inactive"))
            plan.ops.append(_op_deactivate(str(o.EmployeeNumber)))
        plan.summary.append(f"Nhân viên: thêm {n_add}, cập nhật {n_upd}, chuyển store {n_move}, ngừng làm {len(gone)}, giữ nguyên {n_same}")
        if gone and len(gone) >= max(3, len(existing) // 2):
            plan.warnings.append(f"{len(gone)} nhân viên sẽ chuyển Inactive — kiểm tra lại có đúng file của store {store} không")

    # ---- busy of the week
    if replace_busy:
        if replace_employees:                                   # who is active once the employee part is applied
            active_after = {r["eid"] for r in rows if r["status"] == "Active"}
        else:
            active_after = {k for k, o in existing.items() if o.Status == "Active"}
        by_key: dict[tuple[str, int], dict] = {}
        for a in avail.to_dict("records"):
            if a["employee_id"] not in active_after:
                continue
            by_key[(a["employee_id"], int(a["weekday"]))] = a
        unknown = sorted({a["employee_id"] for a in avail.to_dict("records")} - active_after - set(existing))
        if unknown:
            plan.warnings.append(f"Availability có {len(unknown)} mã không có trong danh sách nhân viên — bỏ qua: {', '.join(unknown[:10])}")
        slot_rows, n_busy, n_al = [], 0, 0
        for eid in sorted(active_after):
            for wd in range(7):
                a = by_key.get((eid, wd))
                is_al = bool(a and a["is_al"])
                s = None if a is None or pd.isna(a["busy_from"]) else int(a["busy_from"])
                e = None if a is None or pd.isna(a["busy_to"]) else int(a["busy_to"])
                if (s is None) != (e is None) or (s is not None and e <= s):
                    plan.errors.append(f"Availability {eid} {WEEKDAYS_VI[wd]}: giờ bận không hợp lệ (Bận từ phải trước Bận đến)")
                    continue
                n_busy += s is not None
                n_al += is_al
                slot_rows.append({"eid": eid, "d": week + timedelta(days=wd), "f": _t(s), "t": _t(e), "al": is_al})
        old_n = conn.execute(text("SELECT COUNT(*) FROM dbo.employee_availability_slot WHERE PlantCode = :s AND WeekStartMonday = :w"),
                             {"s": store, "w": week}).scalar()
        plan.changes.append(Change("Thay lịch bận", f"tuần {week:%d/%m/%Y}", "", f"xóa {old_n} dòng cũ, ghi {len(slot_rows)} dòng "
                                   f"({n_busy} ngày có giờ bận, {n_al} ngày nghỉ phép)"))
        plan.summary.append(f"Lịch bận tuần {week:%d/%m/%Y}: {len(active_after)} nhân viên, {n_busy} ngày có giờ bận, {n_al} ngày nghỉ phép "
                            f"(thay {old_n} dòng cũ)")
        plan.ops.append(_op_replace_busy(store, week, slot_rows))
    return plan


def _expanding(name: str):
    from sqlalchemy import bindparam
    return bindparam(name, expanding=True)


def _op_insert_emp(eid, store, name, pos, et, lg, st):
    return lambda conn: conn.execute(text(
        f"INSERT INTO dbo.dim_employee (FullName, EmployeeNumber, PlantCode, Position, EmploymentType, LaborGroup, Status, CreatedAt, UpdatedAt) "
        f"VALUES (:name, :n, :store, :pos, :et, :lg, :st, {ed.NOW}, {ed.NOW})"),
        {"name": name, "n": int(eid), "store": store, "pos": pos, "et": et, "lg": lg, "st": st})


def _op_update_emp(eid, store, name, pos, et, lg, st):
    return lambda conn: conn.execute(text(
        f"UPDATE dbo.dim_employee SET FullName = :name, PlantCode = :store, Position = :pos, EmploymentType = :et, LaborGroup = :lg, "
        f"Status = :st, UpdatedAt = {ed.NOW} WHERE EmployeeNumber = :n"),
        {"name": name, "n": int(eid), "store": store, "pos": pos, "et": et, "lg": lg, "st": st})


def _op_deactivate(eid):
    return lambda conn: conn.execute(text(f"UPDATE dbo.dim_employee SET Status = N'Inactive', UpdatedAt = {ed.NOW} WHERE EmployeeNumber = :n"),
                                     {"n": int(eid)})


def _op_replace_busy(store, week, slot_rows):
    def op(conn):
        conn.execute(text("DELETE FROM dbo.employee_availability_slot WHERE PlantCode = :s AND WeekStartMonday = :w"), {"s": store, "w": week})
        ids = {str(r.EmployeeNumber): r.Id for r in conn.execute(text("SELECT Id, EmployeeNumber FROM dbo.dim_employee WHERE PlantCode = :s"),
                                                                 {"s": store})}
        params = [{"p": store, "n": int(r["eid"]), "i": ids.get(r["eid"]), "w": week, "d": r["d"], "f": r["f"], "t": r["t"], "al": r["al"]}
                  for r in slot_rows]
        if params:
            conn.execute(text(f"INSERT INTO dbo.employee_availability_slot (PlantCode, EmployeeNumber, EmployeeId, WeekStartMonday, WorkDate, "
                              f"BusyFrom, BusyTo, IsPaidLeave, CreatedAt, UpdatedAt) VALUES (:p, :n, :i, :w, :d, :f, :t, :al, {ed.NOW}, {ed.NOW})"),
                         params)
    return op


# ------------------------------------------------------------------ secondments of one home store
def export_secondments(conn: Connection, store: str) -> bytes:
    data = conn.execute(text("SELECT EmployeeId, EmployeeName, HomeStore, ReceivingStore, StartDate, EndDate FROM sched.vw_input_secondment "
                             "WHERE HomeStore = :s AND Status = N'Active' ORDER BY StartDate, EmployeeName"), {"s": store}).fetchall()
    wb = Workbook()
    wb.remove(wb.active)
    ws = _sheet(wb, SEC_SHEET, SEC_HEADERS, [14, 30, 11, 11, 13, 13])
    for r in data:
        ws.append([int(r.EmployeeId), r.EmployeeName, r.HomeStore, r.ReceivingStore, r.StartDate, r.EndDate])
        for col in (5, 6):
            ws.cell(ws.max_row, col).number_format = "DD/MM/YYYY"
    note = wb.create_sheet("Hướng dẫn")
    note.append([f"Danh sách nhân viên store {store} cho store khác mượn. Upload file này sẽ THAY toàn bộ danh sách cho mượn của store {store}."])
    note.append(["Mã NV phải là nhân viên của store gốc; 'Từ ngày' / 'Đến ngày' dạng dd/mm/yyyy. Họ tên chỉ để dễ đọc."])
    note.column_dimensions["A"].width = 120
    return _save(wb)


def plan_secondments(conn: Connection, store: str, content: bytes, user_email: str) -> Plan:
    plan = Plan()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, dtype=object)
    except Exception as exc:                                    # noqa: BLE001
        plan.errors.append(f"Không đọc được file: {exc.__class__.__name__}: {exc}")
        return plan
    cols = {norm_text(c): c for c in df.columns}
    need = {k: cols.get(norm_text(k)) for k in ("Mã NV", "Store nhận", "Từ ngày", "Đến ngày")}
    if any(v is None for v in need.values()):
        plan.errors.append(f"Thiếu cột: {', '.join(k for k, v in need.items() if v is None)} (cần {', '.join(SEC_HEADERS)})")
        return plan
    home_col = cols.get(norm_text("Store gốc"))
    emps = {str(r.EmployeeNumber): r for r in conn.execute(text("SELECT Id, EmployeeNumber, FullName FROM dbo.dim_employee WHERE PlantCode = :s"),
                                                           {"s": store})}
    stores = {r[0] for r in conn.execute(text("SELECT Code FROM dbo.dim_store"))}
    new_rows: list[dict] = []
    for i, r in enumerate(df.to_dict("records"), start=2):
        eid = norm_id(r[need["Mã NV"]])
        if not eid:
            continue
        rec, s, e = norm_id(r[need["Store nhận"]]), _date(r[need["Từ ngày"]]), _date(r[need["Đến ngày"]])
        home = norm_id(r[home_col]) if home_col else store
        problems = []
        if home and home != store:
            problems.append(f"store gốc {home} khác {store}")
        if eid not in emps:
            problems.append(f"nhân viên {eid} không thuộc store {store}")
        if rec not in stores or rec == store:
            problems.append(f"store nhận {rec!r} không hợp lệ")
        if s is None or e is None or e < s:
            problems.append("ngày không hợp lệ (dd/mm/yyyy, 'Đến ngày' ≥ 'Từ ngày')")
        if problems:
            plan.errors.append(f"Dòng {i}: " + "; ".join(problems))
            continue
        for o in new_rows:
            if o["eid"] == eid and o["s"] <= e and o["e"] >= s:
                plan.errors.append(f"Dòng {i}: {emps[eid].FullName} trùng thời gian với dòng khác")
        new_rows.append({"eid": eid, "id": emps[eid].Id, "rec": rec, "s": s, "e": e})
        plan.changes.append(Change("Thêm", eid, emps[eid].FullName, f"→ store {rec} · {s:%d/%m/%Y}–{e:%d/%m/%Y}"))
    old = conn.execute(text("SELECT COUNT(*) FROM dbo.employee_secondment WHERE HomePlantCode = :s"), {"s": store}).scalar()
    plan.summary.append(f"Cho mượn store {store}: xóa {old} dòng cũ, ghi {len(new_rows)} dòng")

    def op(conn):
        conn.execute(text("DELETE FROM dbo.employee_secondment WHERE HomePlantCode = :s"), {"s": store})
        if new_rows:
            conn.execute(text(f"INSERT INTO dbo.employee_secondment (EmployeeId, HomePlantCode, ReceivingStoreCode, StartDate, EndDate, Status, "
                              f"CreatedAt, UpdatedAt, UpdatedBy) VALUES (:id, :h, :rec, :s, :e, N'Active', {ed.NOW}, {ed.NOW}, :u)"),
                         [{**r, "h": store, "u": user_email} for r in new_rows])
    plan.ops.append(op)
    return plan


# ------------------------------------------------------------------ store config (several stores)
def export_store_config(conn: Connection, stores: list[str] | None) -> bytes:
    data = conn.execute(text("SELECT * FROM sched.vw_input_store_config ORDER BY StoreCode")).fetchall()
    wb = Workbook()
    wb.remove(wb.active)
    ws = _sheet(wb, CFG_SHEET, CFG_HEADERS, [10, 40, 12, 12, 12, 11, 15, 15, 16])
    for r in data:
        if stores is not None and r.StoreCode not in stores:
            continue
        ws.append([r.StoreCode, r.StoreName, r.OpeningTime, r.ClosingTime, _f(r.TcphTarget), _f(r.TcphCeilingMult), r.OpenStaff, r.CloseStaff,
                   r.MinStaffPerSlot])
    note = wb.create_sheet("Hướng dẫn")
    note.append(["Chỉ các store có trong file được cập nhật. Để trống TCPH target = giữ nguyên store đó."])
    note.append(["Giờ mở / đóng cửa dạng HH:mm (sửa giờ cần quyền quản lý store). Hệ số trần mặc định 1.05; số người mặc định 2."])
    note.column_dimensions["A"].width = 120
    return _save(wb)


def _f(v):
    return float(v) if v is not None else None


def plan_store_config(conn: Connection, content: bytes, allowed, can_hours: bool, user_email: str) -> Plan:
    plan = Plan()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, dtype=object)
    except Exception as exc:                                    # noqa: BLE001
        plan.errors.append(f"Không đọc được file: {exc.__class__.__name__}: {exc}")
        return plan
    cols = {norm_text(c): c for c in df.columns}
    col = {h: cols.get(norm_text(h)) for h in CFG_HEADERS}
    if col["Mã store"] is None or col["TCPH target"] is None:
        plan.errors.append(f"Thiếu cột 'Mã store' / 'TCPH target' (cần {', '.join(CFG_HEADERS)})")
        return plan
    current = {r.StoreCode: r for r in conn.execute(text("SELECT * FROM sched.vw_input_store_config"))}
    n_same = 0
    for i, r in enumerate(df.to_dict("records"), start=2):
        store = norm_id(r[col["Mã store"]])
        if not store:
            continue
        target = _num(r[col["TCPH target"]])
        if target is None:
            continue
        if store not in current:
            plan.errors.append(f"Dòng {i}: store {store} không có hoặc không hoạt động")
            continue
        if not allowed(store):
            plan.errors.append(f"Dòng {i}: bạn không được phân quyền store {store}")
            continue
        cur = current[store]
        get = lambda h, default, r=r: default if col[h] is None or _blank(r[col[h]]) else r[col[h]]   # noqa: E731
        try:
            mult, o, c, m = float(_num(get("Hệ số trần", 1.05))), int(_num(get("Số người mở ca", 2))), int(_num(get("Số người đóng ca", 2))), \
                int(_num(get("Tối thiểu mỗi giờ", 2)))
            ed.check_config(target, mult, o, c, m)
        except (TypeError, ValueError):
            plan.errors.append(f"Dòng {i} store {store}: số không hợp lệ")
            continue
        except Exception as exc:                                # HTTPException from check_config
            plan.errors.append(f"Dòng {i} store {store}: {getattr(exc, 'detail', exc)}")
            continue
        open_new, close_new = _hhmm_txt(get("Giờ mở cửa", cur.OpeningTime)), _hhmm_txt(get("Giờ đóng cửa", cur.ClosingTime))
        hours_changed = (open_new, close_new) != (cur.OpeningTime, cur.ClosingTime)
        if hours_changed and not can_hours:
            plan.errors.append(f"Dòng {i} store {store}: đổi giờ mở/đóng cửa cần quyền quản lý store")
            continue
        old_cfg = (_f(cur.TcphTarget), _f(cur.TcphCeilingMult), cur.OpenStaff, cur.CloseStaff, cur.MinStaffPerSlot)
        new_cfg = (round(target, 2), round(mult, 2), o, c, m)
        if old_cfg == new_cfg and not hours_changed:
            n_same += 1
            continue
        diff = [f"{lbl}: {a if a is not None else '—'} → {b}" for lbl, a, b in zip(
            ("TCPH target", "Hệ số trần", "Mở ca", "Đóng ca", "Tối thiểu"), old_cfg, new_cfg, strict=True) if a != b]
        if hours_changed:
            diff.insert(0, f"Giờ: {cur.OpeningTime}–{cur.ClosingTime} → {open_new}–{close_new}")
        plan.changes.append(Change("Cập nhật" if cur.TcphTarget is not None else "Thêm", store, cur.StoreName, "; ".join(diff)))
        plan.ops.append(_op_config(store, new_cfg, (open_new, close_new) if hours_changed else None, user_email))
    plan.summary.append(f"Cấu hình store: thay đổi {len(plan.ops)}, giữ nguyên {n_same}")
    return plan


def _hhmm_txt(v) -> str | None:
    if _blank(v):
        return None
    if isinstance(v, (time, datetime)):
        return f"{v:%H:%M}"
    s = str(v).strip()
    if s in ("24:00", "24:00:00"):
        return "24:00"
    m = parse_hhmm(s)
    return None if m is None else f"{m // 60:02d}:{m % 60:02d}"


def _op_config(store, cfg, hours, user_email):
    def op(conn):
        if hours:
            ed.set_hours(conn, store, *hours)
        ed.upsert_config(conn, store, *cfg, user_email)
    return op


# ------------------------------------------------------------------ apply
def apply_plan(conn: Connection, plan: Plan, user_email: str, detail: str) -> None:
    for op in plan.ops:
        op(conn)
    ed.bump(conn, user_email, f"upload Excel — {detail}")
