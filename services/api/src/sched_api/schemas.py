"""Response models (camelCase JSON). Generated into services/web/src/api/schema.d.ts via OpenAPI."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Meta(Model):
    data_version: int
    built_at: str | None = None
    source: str = "sched"
    back_test: bool = False                      # demo / back-test mode (SCHED_ALLOW_PAST_WEEKS or SCHED_DEFAULT_AVAILABILITY_WEEK)
    availability_week: str | None = None         # busy-data week reused in back-test


class Envelope(Model, Generic[T]):  # noqa: UP046 - keep Generic for the OpenAPI schema names
    data: T
    meta: Meta


# ------------------------------------------------------------------ stores / weeks
class StoreItem(Model):
    store_code: str
    store_name: str
    opening_time: str | None = None
    closing_time: str | None = None
    tcph_target: float | None = None
    employee_count: int
    has_forecast: bool
    ready_to_schedule: bool
    scheduled_weeks: int


class ForecastWeek(Model):
    week_start: str
    store_count: int
    created_at: str | None = None
    method_version: str | None = None


# ------------------------------------------------------------------ schedule
class ScheduleWeek(Model):
    store_code: str
    week_start: str
    week_end: str
    store_name: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    status: str
    assessment: str | None = None
    tcph_target: float | None = None
    weekly_tcph: float | None = None
    tcph_in_target: bool | None = None
    forecast_tc: float | None = None
    labor_hours: float | None = None
    nso_hours: float | None = None
    staff_coverage_pct: float | None = None
    manager_coverage_pct: float | None = None
    employee_count: int
    error_count: int
    warning_count: int
    availability_week: str | None = None
    run_id: int | None = None
    note: str | None = None
    created_at: str
    created_by: str
    run_status: str | None = None
    run_finished_at: str | None = None


class DaySummary(Model):
    work_date: str
    weekday: str
    day_status: str
    forecast_tc: float | None = None
    regular_hours: float | None = None
    training_hours: float | None = None
    nso_hours: float | None = None
    tcph: float | None = None
    tcph_incl_nso: float | None = None
    tcph_in_target: bool | None = None
    target_hours_min: float | None = None
    target_hours_max: float | None = None
    needed_staff_hours: int | None = None
    scheduled_staff_hours: int | None = None
    missing_staff_hours: int | None = None
    hours_without_manager: int | None = None
    openers: int | None = None
    closers: int | None = None


class HourCoverage(Model):
    work_date: str
    weekday: str
    slot: int
    time_slot: str
    forecast_tc: float
    is_peak_hour: bool
    needed_staff: int
    scheduled_staff: int
    managers_on_duty: int
    missing_staff: int
    status: str


class RosterDay(Model):
    work_date: str
    weekday: str
    employee_id: str
    employee_name: str
    position: str
    employment_type: str
    labor_group: str
    home_store: str | None = None
    day_type: str
    start_time: str | None = None
    end_time: str | None = None
    hours: float
    shift_code: str | None = None
    shift_role: str | None = None
    note: str | None = None
    sort_order: int


class Issue(Model):
    severity: str
    work_date: str | None = None
    employee_id: str | None = None
    employee_name: str | None = None
    message: str
    issue_code: str | None = None


class Overview(Model):
    week: ScheduleWeek
    days: list[DaySummary]
    hourly: list[HourCoverage]
    roster: list[RosterDay]
    issues: list[Issue]


# ------------------------------------------------------------------ runs
class RunRequest(Model):
    store_code: str = Field(min_length=1, max_length=10)
    week_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    availability_week: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    requested_by: str | None = Field(default=None, max_length=256)


class Run(Model):
    run_id: int
    store_code: str
    week_start: str
    availability_week: str | None = None
    status: str
    assessment: str | None = None
    message: str | None = None
    requested_by: str
    requested_at: str
    started_at: str | None = None
    finished_at: str | None = None


# ------------------------------------------------------------------ auth (accounts of the .NET app)
class LoginRequest(Model):
    email: str = Field(min_length=3, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class Me(Model):
    user_id: int
    email: str
    display_name: str
    role: str
    permissions: list[str]
    all_stores: bool
    stores: list[str]
    can: dict[str, bool]


# ------------------------------------------------------------------ inputs
class StoreConfig(Model):
    store_code: str
    store_name: str
    opening_time: str | None = None
    closing_time: str | None = None
    is24h: bool
    tcph_target: float | None = None
    tcph_ceiling_mult: float | None = None
    open_staff: int | None = None
    close_staff: int | None = None
    min_staff_per_slot: int | None = None
    updated_by: str | None = None
    updated_at: str | None = None


class EmployeeItem(Model):
    store_code: str
    employee_id: str
    employee_name: str
    position: str
    employment_type: str
    labor_group: str
    status: str
    updated_at: str | None = None


class AvailabilityItem(Model):
    store_code: str
    employee_id: str
    employee_name: str | None = None
    week_start: str
    work_date: str
    busy_from: str | None = None
    busy_to: str | None = None
    is_paid_leave: bool


class SecondmentItem(Model):
    id: int
    employee_id: str
    employee_name: str
    position: str
    home_store: str
    receiving_store: str
    start_date: str
    end_date: str
    status: str
    updated_by: str | None = None
    updated_at: str | None = None


class ShiftCodeItem(Model):
    shift_code: str
    start_time: str
    end_time: str
    duration_hours: float
    is_overnight: bool
    sort_order: int
    is_active: bool
    note: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None


class InputOptions(Model):
    positions: list[str]
    employment_types: list[str]
    labor_groups: list[str]
    statuses: list[str]
    availability_weeks: list[str]


_TIME = r"^([01]\d|2[0-4]):[0-5]\d$"
_DATE = r"^\d{4}-\d{2}-\d{2}$"


class EmployeeIn(Model):
    store_code: str = Field(min_length=1, max_length=10)
    employee_id: str = Field(pattern=r"^\d{1,15}$")
    employee_name: str = Field(min_length=1, max_length=200)
    position: str
    employment_type: str
    labor_group: str
    status: str = "Active"


class EmployeeUpdate(Model):
    employee_name: str = Field(min_length=1, max_length=200)
    position: str
    employment_type: str
    labor_group: str
    status: str


class AvailabilityDayIn(Model):
    employee_id: str = Field(pattern=r"^\d{1,15}$")
    work_date: str = Field(pattern=_DATE)
    busy_from: str | None = Field(default=None, pattern=_TIME)
    busy_to: str | None = Field(default=None, pattern=_TIME)
    is_paid_leave: bool = False


class AvailabilityWeekIn(Model):
    items: list[AvailabilityDayIn] = Field(min_length=1, max_length=2000)


class AvailabilityCopyIn(Model):
    source_week: str = Field(pattern=_DATE)


class SecondmentIn(Model):
    employee_id: str = Field(pattern=r"^\d{1,15}$")
    home_store: str = Field(min_length=1, max_length=10)
    receiving_store: str = Field(min_length=1, max_length=10)
    start_date: str = Field(pattern=_DATE)
    end_date: str = Field(pattern=_DATE)


class SecondmentUpdate(Model):
    receiving_store: str = Field(min_length=1, max_length=10)
    start_date: str = Field(pattern=_DATE)
    end_date: str = Field(pattern=_DATE)


class StoreConfigIn(Model):
    opening_time: str | None = Field(default=None, pattern=_TIME)
    closing_time: str | None = Field(default=None, pattern=_TIME)
    tcph_target: float = Field(gt=0, le=50)
    tcph_ceiling_mult: float = Field(default=1.05, ge=1, le=2)
    open_staff: int = Field(default=2, ge=1, le=20)
    close_staff: int = Field(default=2, ge=1, le=20)
    min_staff_per_slot: int = Field(default=2, ge=1, le=20)


class ImportChange(Model):
    action: str
    key: str
    name: str = ""
    detail: str = ""


class ImportResult(Model):
    applied: bool
    can_apply: bool
    summary: list[str]
    errors: list[str]
    warnings: list[str]
    changes: list[ImportChange]


class Saved(Model):
    ok: bool = True
    message: str = ""
