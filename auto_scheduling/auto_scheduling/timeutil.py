"""Time helpers. Internally every clock time is an int of minutes from 00:00 of
the shift's start date (a shift crossing midnight has end > 1440)."""
from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta

DAY_MINUTES = 1440
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

_HHMM = re.compile(r"^\s*(\d{1,2})\s*[:hH.]\s*(\d{2})(?::\d{2})?\s*$")   # '7:00', '07:00', '15:00:00' (Excel)


def parse_hhmm(value, *, allow_24: bool = True) -> int | None:
    """'7:00' / '07:00' / time / Excel day-fraction -> minutes. None when blank/invalid.

    '24:00' is accepted (= 1440) when allow_24, so a store can close at midnight.
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (datetime, time)):
        return value.hour * 60 + value.minute
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 0 <= value < 1:  # Excel time fraction
            return int(round(value * DAY_MINUTES))
        return None
    s = str(value).strip()
    if not s:
        return None
    m = _HHMM.match(s)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if mi > 59:
        return None
    if h == 24 and mi == 0 and allow_24:
        return DAY_MINUTES
    if h > 23:
        return None
    return h * 60 + mi


def fmt_hhmm(minutes: int) -> str:
    """Minutes -> 'HH:mm' wall-clock (wraps past midnight: 1800 -> '06:00')."""
    m = int(minutes) % DAY_MINUTES
    return f"{m // 60:02d}:{m % 60:02d}"


def floor_hour(minutes: int) -> int:
    return minutes // 60


def ceil_hour(minutes: int) -> int:
    return -(-minutes // 60)


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_dates(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]


def to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


_WEEKDAY_ALIASES = {
    0: ("mon", "monday", "t2", "thu2", "thuhai", "2"),
    1: ("tue", "tuesday", "t3", "thu3", "thuba", "3"),
    2: ("wed", "wednesday", "t4", "thu4", "thutu", "4"),
    3: ("thu", "thursday", "t5", "thu5", "thunam", "5"),
    4: ("fri", "friday", "t6", "thu6", "thusau", "6"),
    5: ("sat", "saturday", "t7", "thu7", "thubay", "7"),
    6: ("sun", "sunday", "cn", "chunhat", "8"),
}
_WEEKDAY_LOOKUP = {alias: idx for idx, aliases in _WEEKDAY_ALIASES.items() for alias in aliases}


def norm_text(s) -> str:
    """Lower-case, strip Vietnamese accents and non-alphanumerics (demo `U.norm`)."""
    import unicodedata

    raw = str(s if s is not None else "").strip().lower().replace("đ", "d")
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9%]+", "", raw)


def parse_weekday(value) -> int | None:
    """'Mon' / 'Monday' / 'T2' / 'Thứ Hai' / 'CN' -> 0..6."""
    return _WEEKDAY_LOOKUP.get(norm_text(value))
