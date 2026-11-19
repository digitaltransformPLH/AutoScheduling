"""Validation issues shared by every module (SPEC 7.1 `validation_issues`).

Severity follows SPEC 7.1: CRITICAL (the spec's "error": the store-week cannot be
scheduled / the file cannot be written), WARNING, INFO.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable, Iterator

import pandas as pd

CRITICAL = "CRITICAL"
WARNING = "WARNING"
INFO = "INFO"
SEVERITIES = (CRITICAL, WARNING, INFO)


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    store_id: str | None = None
    week_start: date | None = None
    employee_id: str | None = None
    date: date | None = None
    slot: int | None = None


class IssueLog:
    """Append-only list of issues with a few helpers."""

    def __init__(self, store_id: str | None = None, week_start: date | None = None):
        self.store_id = store_id
        self.week_start = week_start
        self._items: list[Issue] = []

    def add(self, code: str, severity: str, message: str, **ctx) -> Issue:
        if severity not in SEVERITIES:
            raise ValueError(f"unknown severity {severity!r}")
        ctx.setdefault("store_id", self.store_id)
        ctx.setdefault("week_start", self.week_start)
        issue = Issue(code=code, severity=severity, message=message, **ctx)
        self._items.append(issue)
        return issue

    def critical(self, code: str, message: str, **ctx) -> Issue:
        return self.add(code, CRITICAL, message, **ctx)

    def warning(self, code: str, message: str, **ctx) -> Issue:
        return self.add(code, WARNING, message, **ctx)

    def info(self, code: str, message: str, **ctx) -> Issue:
        return self.add(code, INFO, message, **ctx)

    def extend(self, issues: Iterable[Issue]) -> None:
        self._items.extend(issues)

    def has_critical(self, store_id: str | None = None) -> bool:
        return any(
            i.severity == CRITICAL and (store_id is None or i.store_id in (None, store_id))
            for i in self._items
        )

    def codes(self, severity: str | None = None) -> list[str]:
        return [i.code for i in self._items if severity is None or i.severity == severity]

    def by_code(self, code: str) -> list[Issue]:
        return [i for i in self._items if i.code == code]

    def to_frame(self) -> pd.DataFrame:
        cols = [f for f in Issue.__dataclass_fields__]
        return pd.DataFrame([asdict(i) for i in self._items], columns=cols)

    def __iter__(self) -> Iterator[Issue]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        counts = {s: sum(i.severity == s for i in self._items) for s in SEVERITIES}
        return f"IssueLog({counts})"
