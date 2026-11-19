"""Engine inputs from SQL Server (views sched.vw_engine_*, which map the dbo tables of the ASP.NET app).

Returns the same DataFrames as the file loaders (SPEC Section 2 contracts) so validation and the optimizer
do not change. Two extras:

* availability_week (back-test): busy rows of that week are reused for the schedule week by weekday
  (forecast only covers past weeks; busy data is entered for the coming week).
* secondments: employee lent from home store to receiving store on given dates; dates are shifted the
  same way as the busy data when availability_week != week_start.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import Engine, text

from ..timeutil import WEEKDAYS

INACTIVE_SECONDMENT = {"cancelled", "canceled", "inactive", "rejected", "deleted", "huy", "huỷ", "hủy"}


@dataclass
class Secondment:
    employee_id: str
    name: str
    position: str
    employment_type: str
    labor_group: str
    home_store: str
    receiving_store: str
    dates: list[date]                     # dates inside the schedule week (already shifted for back-test)


@dataclass
class SqlInputs:
    dim_store: pd.DataFrame
    ops: pd.DataFrame
    employees: pd.DataFrame
    busy: pd.DataFrame
    forecast: pd.DataFrame
    availability_week: date
    secondments_out: list[Secondment] = field(default_factory=list)   # this store's employees lent elsewhere
    secondments_in: list[Secondment] = field(default_factory=list)    # employees borrowed by this store


def _df(conn, sql: str, **params) -> pd.DataFrame:
    res = conn.execute(text(sql), params)
    return pd.DataFrame(res.fetchall(), columns=list(res.keys()))


def _hhmm(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    s = str(v)[:5]
    return "24:00" if s in ("23:59",) else s


def load_sql_inputs(engine: Engine, store_id: str, week_start: date, availability_week: date | None = None) -> SqlInputs:
    aw = availability_week or week_start
    shift = (week_start - aw).days
    week_dates = {week_start + timedelta(days=i) for i in range(7)}
    with engine.connect() as conn:
        st = _df(conn, "SELECT * FROM sched.vw_engine_store WHERE store_id = :s", s=store_id)
        dim_store = st[["store_id", "short_name", "opening_time", "closing_time", "is_24h", "closed_sat", "closed_sun"]].astype(str) \
            if len(st) else pd.DataFrame(columns=["store_id"])
        if len(dim_store):
            dim_store["is_24h"] = st["is_24h"].map(lambda b: "1" if b else "0")
            dim_store["closed_sat"] = st["closed_sat"].map(lambda b: "1" if b else "0")
            dim_store["closed_sun"] = st["closed_sun"].map(lambda b: "1" if b else "0")
            for c in ("opening_time", "closing_time"):
                dim_store[c] = st[c].map(lambda v: "" if v is None else str(v))
        ops = st[["store_id", "tcph_target", "tcph_ceiling_mult", "open_staff", "close_staff", "min_staff_per_slot"]].copy() \
            if len(st) else pd.DataFrame(columns=["store_id", "tcph_target"])
        ops = ops.map(lambda v: "" if v is None or (isinstance(v, float) and v != v) else str(v))

        employees = _df(conn, "SELECT employee_id, store_id, name, position, employment_type, labor_group, status "
                              "FROM sched.vw_engine_employee WHERE store_id = :s", s=store_id)

        raw = _df(conn, "SELECT employee_id, work_date, busy_from, busy_to, is_paid_leave FROM sched.vw_engine_busy "
                        "WHERE store_id = :s AND week_start = :w", s=store_id, w=aw)
        rows = []
        for r in raw.itertuples(index=False):
            wd = WEEKDAYS[pd.Timestamp(r.work_date).weekday()]
            if bool(r.is_paid_leave):
                rows.append({"employee_id": r.employee_id, "store_id": store_id, "weekday": wd, "busy_from": "AL", "busy_to": "AL"})
            elif r.busy_from is not None and r.busy_to is not None:
                rows.append({"employee_id": r.employee_id, "store_id": store_id, "weekday": wd,
                             "busy_from": _hhmm(r.busy_from), "busy_to": _hhmm(r.busy_to)})
        busy = pd.DataFrame(rows, columns=["employee_id", "store_id", "weekday", "busy_from", "busy_to"])

        forecast = _df(conn, "SELECT * FROM sched.vw_engine_forecast WHERE store_id = :s AND week_start = :w", s=store_id, w=week_start)

        sec = _df(conn, "SELECT * FROM sched.vw_engine_secondment WHERE (home_store = :s OR receiving_store = :s) "
                        "AND end_date >= :d0 AND start_date <= :d1", s=store_id, d0=aw, d1=aw + timedelta(days=6))
    out_, in_ = [], []
    for r in sec.itertuples(index=False):
        if str(r.status or "").strip().lower() in INACTIVE_SECONDMENT or str(r.employee_status or "").strip().lower() != "active":
            continue
        d0, d1 = pd.Timestamp(r.start_date).date(), pd.Timestamp(r.end_date).date()
        dates = sorted({d + timedelta(days=shift) for d in (d0 + timedelta(days=i) for i in range((d1 - d0).days + 1))} & week_dates)
        if not dates:
            continue
        s = Secondment(str(r.employee_id), r.name, r.position, r.employment_type, r.labor_group, str(r.home_store), str(r.receiving_store), dates)
        (out_ if s.home_store == store_id else in_).append(s)
    return SqlInputs(dim_store, ops, employees, busy, forecast, aw, out_, in_)


def load_sql_shift_codes(engine: Engine) -> pd.DataFrame:
    """dbo.dim_shift_code (active codes) in the old CSV layout: shift_code, start, end, duration_hours; ordered by sort_order
    so that, for duplicated (start, end) pairs, the first code wins as before."""
    with engine.connect() as conn:
        df = _df(conn, "SELECT shift_code, start, [end], duration_hours FROM sched.vw_engine_shift_code ORDER BY sort_order, shift_code")
    return df.reset_index(drop=True)
