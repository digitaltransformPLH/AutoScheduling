"""Per-store time model (SPEC 4.2, 4.3, 4.5).

* Window: setup_start = opening - setup, clean_end = closing + clean. Every shift
  lies inside [setup_start, clean_end] (24h stores: no window, shifts may cross midnight).
* Operating slots: 60-min slots `h` with h*60 >= opening and (h+1)*60 <= closing.
* Slot mapping [DECISION 11-Nov-2026, demo-compatible]: a shift covers every
  operating slot with slot_start >= floor_hour(start) and slot_end <= ceil_hour(end).
  06:30-14:30 covers 07..14 (07:00-15:00). Hand-over hour coverage is overstated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .models import Shift, StoreParams
from .timeutil import DAY_MINUTES, ceil_hour, floor_hour, week_dates


@dataclass(frozen=True)
class StoreCalendar:
    store: StoreParams

    # ----------------------------------------------------------- window
    @property
    def setup_start(self) -> int:
        return self.store.opening_min - self.store.setup_minutes

    @property
    def clean_end(self) -> int:
        return self.store.closing_min + self.store.clean_minutes

    @property
    def window_hours(self) -> float:
        return (self.clean_end - self.setup_start) / 60

    @property
    def operating_hours(self) -> list[int]:
        """Slot start hours of one day (07:00-22:00 -> 7..21)."""
        first = ceil_hour(self.store.opening_min)
        last = floor_hour(self.store.closing_min)  # exclusive
        return list(range(first, last))

    @property
    def first_slot(self) -> int:
        return self.operating_hours[0]

    @property
    def last_slot(self) -> int:
        return self.operating_hours[-1]

    # ----------------------------------------------------------- days
    def is_open(self, d: date) -> bool:
        return d.weekday() not in self.store.closed_weekdays

    def open_dates(self, week_start: date) -> list[date]:
        return [d for d in week_dates(week_start) if self.is_open(d)]

    # ----------------------------------------------------------- slot mapping
    def covered_slots(self, start_min: int, end_min: int) -> list[tuple[int, int]]:
        """Slots covered by a shift starting on day D -> [(day_offset, hour)].
        day_offset is 1 for slots after midnight (24h stores only)."""
        lo, hi = floor_hour(start_min), ceil_hour(end_min)   # slot h covered iff lo <= h and h+1 <= hi
        ops = set(self.operating_hours)
        out = []
        for h in range(lo, hi):
            off, hod = divmod(h, 24)
            if hod in ops:
                out.append((off, hod))
        return out

    def shift_slots(self, shift: Shift) -> list[tuple[date, int]]:
        return [(shift.date + timedelta(days=off), h) for off, h in self.covered_slots(shift.start_min, shift.end_min)]

    # ----------------------------------------------------------- open / close
    def is_opener(self, start_min: int) -> bool:
        return not self.store.is_24h and start_min == self.setup_start

    def is_closer(self, start_min: int, end_min: int) -> bool:
        if self.store.is_24h or end_min != self.clean_end:
            return False
        return (0, self.last_slot) in self.covered_slots(start_min, end_min)

    def inside_window(self, start_min: int, end_min: int) -> bool:
        if self.store.is_24h:
            return 0 <= start_min < DAY_MINUTES and end_min > start_min
        return self.setup_start <= start_min < end_min <= self.clean_end

    def ft_open_shift(self, hours: int = 8) -> tuple[int, int]:
        return self.setup_start, self.setup_start + hours * 60

    def ft_close_shift(self, hours: int = 8) -> tuple[int, int]:
        return self.clean_end - hours * 60, self.clean_end
