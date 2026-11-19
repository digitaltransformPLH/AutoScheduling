"""Planning window guard (SPEC 8.4) [DECISION 11-Nov-2026 / 12-Nov-2026].

week_start must be a Monday strictly later than the Monday of the current week
(server time, Asia/Ho_Chi_Minh). ALLOW_PAST_WEEKS skips the date check for
dev / back-test; publish and File 2 export stay blocked in that mode.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import Config
from .issues import IssueLog
from .timeutil import monday_of


def server_today(cfg: Config, now: datetime | None = None) -> date:
    tz = ZoneInfo(cfg.timezone)
    if now is None:
        return datetime.now(tz).date()
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    return now.astimezone(tz).date()


def check_planning_window(week_start: date, cfg: Config, issues: IssueLog, now: datetime | None = None) -> bool:
    if week_start.weekday() != 0:
        issues.critical("WEEK_START_NOT_MONDAY", f"week_start {week_start} is not a Monday")
        return False
    if cfg.allow_past_weeks:
        return True
    current_monday = monday_of(server_today(cfg, now))
    if week_start <= current_monday:
        issues.critical("WEEK_NOT_IN_PLANNING_WINDOW",
                        f"week_start {week_start} must be after the current week (Monday {current_monday}); "
                        "set allow_past_weeks only for dev / back-test")
        return False
    return True


def can_publish(cfg: Config) -> bool:
    """Publish / File 2 export is never allowed in back-test mode."""
    return not cfg.allow_past_weeks
