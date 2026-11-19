"""Global constants (SPEC Section 3).

All constants live here. Store-level values (tcph_target, open/close staff, ...)
come from `ops_input` / `dim_store` and are resolved into `StoreParams`
(see `auto_scheduling.models`). `Config.with_overrides` gives a per-run copy.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SERVICE_DIR = PACKAGE_DIR.parent
DATA_DIR = SERVICE_DIR / "data"
REPORTS_DIR = SERVICE_DIR / "reports"

VALID_LABOR_GROUPS = ("Regular", "Training", "NSO")
VALID_QUANTILES = ("tc_p50", "tc_p25", "tc_p75", "tc_p80", "tc_p90")


@dataclass(frozen=True)
class Config:
    # --- time model ---
    slot_minutes: int = 60                      # [DECISION 11-Nov-2026] keep demo 60-min slots
    timezone: str = "Asia/Ho_Chi_Minh"
    setup_minutes: int = 30                     # [DECISION 05-Nov-2026] fixed for every store, not in dim_store
    clean_minutes: int = 30                     # 24h stores: 0 (SPEC 4.5)

    # --- shift rules ---
    ft_shift_hours: int = 8                     # 8 working hours, no break [DECISION 05-Nov-2026]
    ft_max_weekly_hours: int = 48
    ft_work_days_per_week: int = 6
    pt_min_hours: int = 4
    pt_max_hours: int = 8
    pt_regular_weekly_cap: float | None = None  # [DECISION 05-Nov-2026] HR/Legal to recheck
    special_pt_hours: int = 4
    special_pt_days_target: int = 5
    special_pt_weekly_max: int = 20
    min_rest_between_shifts: float | None = None  # [DECISION 05-Nov-2026] HR/Legal to recheck
    morning_shift_cutoff: str = "12:00"         # [PROPOSED] H17
    al_shift_start: str = "07:00"               # AL uploaded as 07:00-15:00 (code 1180), SPEC 7.2
    al_shift_end: str = "15:00"
    al_paid_hours: int = 8
    # Secondment day at the home store: still paid hours, never OFF [DECISION 19-Nov-2026]; recorded as ft_shift_hours
    # on this shift (no times in employee_secondment), same 07:00-15:00 / code 1180 as AL
    away_shift_start: str = "07:00"
    away_shift_end: str = "15:00"

    # --- coverage / ops_input defaults (chain-wide) ---
    min_staff_per_slot: int = 2                 # [DECISION 05-Nov-2026]
    required_manager_per_slot: int = 1          # [DECISION 05-Nov-2026]
    open_staff: int = 2
    close_staff: int = 2
    tcph_ceiling_mult: float = 1.05
    max_manager_gap_fill_shifts: int = 2        # SPEC 4.4

    # --- optimizer ---
    tcph_priority: str = "band_first"           # [DECISION 12-Nov-2026]
    forecast_quantile: str = "tc_p50"

    # --- planning window ---
    allow_past_weeks: bool = False              # True only for dev / back-test [DECISION 12-Nov-2026]

    def with_overrides(self, **kwargs) -> Config:
        """Copy with the given fields replaced; None values and unknown keys are ignored."""
        known = {f.name for f in fields(self)}
        clean = {k: v for k, v in kwargs.items() if k in known and v is not None}
        return replace(self, **clean)


DEFAULT_CONFIG = Config()
