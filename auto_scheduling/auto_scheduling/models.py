"""Core domain objects shared by demand, optimizer, validation and output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .timeutil import DAY_MINUTES, fmt_hhmm

MANAGER_RANK = {"Store Manager": 1, "Assistant Store Manager": 2, "Shift Supervisor": 3}


@dataclass(frozen=True)
class StoreParams:
    """One store's resolved parameters (dim_store + ops_input + Config defaults)."""

    store_id: str
    short_name: str
    opening_min: int            # minutes from 00:00; 0 for 24h stores
    closing_min: int            # minutes from 00:00 (1440 = midnight); 1440 for 24h stores
    is_24h: bool
    closed_weekdays: frozenset[int]  # 5 = Sat, 6 = Sun
    setup_minutes: int
    clean_minutes: int
    tcph_target: float
    tcph_ceiling_mult: float
    open_staff: int
    close_staff: int
    min_staff_per_slot: int

    @property
    def tcph_ceiling(self) -> float:
        return self.tcph_target * self.tcph_ceiling_mult

    @property
    def hours_label(self) -> str:
        return "24h" if self.is_24h else f"{fmt_hhmm(self.opening_min)}-{fmt_hhmm(self.closing_min) if self.closing_min < DAY_MINUTES else '24:00'}"


@dataclass(frozen=True)
class Employee:
    employee_id: str
    store_id: str
    name: str
    position: str               # raw position text
    position_display: str       # Store Manager / Assistant Store Manager / Shift Supervisor / Barista Trainer / Crew Member
    employment_type: str        # FT / PT
    labor_group: str            # Regular / Training / NSO
    is_manager: bool
    manager_rank: int | None    # SM=1, ASM=2, SS=3
    can_act_as_manager: bool    # Barista Trainer (fallback MOD only)
    is_fixed: bool              # FT or manager -> 8h shifts + weekly OFF rule
    is_special_pt: bool         # PT in Training / NSO
    # secondment: employee borrowed from another store; only works here on these weekdays and the
    # weekly OFF / 6-day / 48h rules belong to the home store (None = own employee)
    home_store: str | None = None
    borrowed_weekdays: frozenset[int] | None = None

    @property
    def counts_as_mod(self) -> bool:
        """Manager-group, not Training (SPEC 4.1)."""
        return self.is_manager and self.labor_group != "Training"

    @property
    def is_borrowed(self) -> bool:
        return self.home_store is not None


@dataclass(frozen=True)
class BusyBlock:
    employee_id: str
    weekday: int                # 0 = Mon .. 6 = Sun
    start_min: int | None       # None when is_al / away
    end_min: int | None
    is_al: bool = False
    away_to: str | None = None  # secondment: working at this other store the whole day


@dataclass
class Shift:
    """One employee on one start date. start/end are minutes from 00:00 of `date`;
    end > 1440 means the shift crosses midnight (24h stores only)."""

    employee_id: str
    store_id: str
    date: date
    start_min: int
    end_min: int
    labor_group: str = "Regular"
    position_display: str = "Crew Member"
    is_manager: bool = False
    can_act_as_manager: bool = False
    is_paid_leave: bool = False
    tags: set[str] = field(default_factory=set)   # OPEN / CLOSE / LOCKED / AL / MOD_FILL ...

    @property
    def hours(self) -> float:
        return (self.end_min - self.start_min) / 60

    @property
    def crosses_midnight(self) -> bool:
        return self.end_min > DAY_MINUTES

    @property
    def start_hhmm(self) -> str:
        return fmt_hhmm(self.start_min)

    @property
    def end_hhmm(self) -> str:
        return fmt_hhmm(self.end_min)

    def __repr__(self) -> str:
        return f"Shift({self.employee_id} {self.date} {self.start_hhmm}-{self.end_hhmm} {sorted(self.tags)})"
