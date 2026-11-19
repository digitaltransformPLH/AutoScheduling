"""`dim_shift_code` loader (SPEC 7.3).

* Exact match on (start, end); overnight codes (end <= start) are stored with
  end + 1440 so they match shifts crossing midnight.
* Duplicated (start, end) pairs: first code in file order wins, others logged.
* Repairs codes corrupted by Excel scientific notation ("11E3" saved as 11000).
  Verified 12-Nov-2026 against PLH_SHIFT_CODE_MAP in the demo HTML: the 7 codes
  11E1..11E7 were stored as 110, 1100, ..., 110000000.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..issues import IssueLog
from ..timeutil import DAY_MINUTES, fmt_hhmm, parse_hhmm

_SCI_CORRUPTED = re.compile(r"^11(0+)$")


def repair_code(code: str) -> str:
    """'110' -> '11E1', '11000' -> '11E3' (Excel read 11E<n> as 11 x 10^n)."""
    m = _SCI_CORRUPTED.match(code)
    return f"11E{len(m.group(1))}" if m else code


@dataclass
class ShiftCodeTable:
    frame: pd.DataFrame                                   # one row per code, cleaned
    by_pair: dict[tuple[int, int], str] = field(default_factory=dict)
    duplicates: dict[tuple[int, int], list[str]] = field(default_factory=dict)

    def lookup(self, start_min: int, end_min: int) -> str | None:
        return self.by_pair.get((int(start_min), int(end_min)))

    def has(self, start_min: int, end_min: int) -> bool:
        return (int(start_min), int(end_min)) in self.by_pair

    def __len__(self) -> int:
        return len(self.frame)


def load_shift_codes(source: str | Path | pd.DataFrame, issues: IssueLog | None = None) -> ShiftCodeTable:
    issues = issues if issues is not None else IssueLog()
    if isinstance(source, pd.DataFrame):
        raw = source.astype(str)
    else:
        raw = pd.read_csv(source, dtype=str, encoding="utf-8-sig")
    raw.columns = [c.strip().lower() for c in raw.columns]
    missing = {"shift_code", "start", "end"} - set(raw.columns)
    if missing:
        raise ValueError(f"dim_shift_code missing columns: {sorted(missing)}")

    rows = []
    for idx, r in raw.iterrows():
        code_raw = str(r["shift_code"]).strip()
        code = repair_code(code_raw)
        if code != code_raw:
            issues.warning(
                "SHIFT_CODE_SCI_NOTATION_REPAIRED",
                f"shift code {code_raw!r} ({r['start']}-{r['end']}) looks Excel-corrupted; using {code!r}. Fix the source CSV.",
            )
        s, e = parse_hhmm(r["start"], allow_24=False), parse_hhmm(r["end"], allow_24=True)
        if s is None or e is None:
            issues.warning("SHIFT_CODE_BAD_TIME", f"shift code {code}: bad time {r['start']!r}-{r['end']!r}; skipped")
            continue
        if e <= s:
            e += DAY_MINUTES  # overnight
        hours = (e - s) / 60
        try:
            declared = float(r.get("duration_hours", "nan"))
        except ValueError:
            declared = float("nan")
        if declared == declared and abs(declared - hours) > 0.05:
            issues.warning(
                "SHIFT_CODE_DURATION_MISMATCH",
                f"shift code {code} {fmt_hhmm(s)}-{fmt_hhmm(e)}: duration_hours={declared} but clock span={hours:.2f}h",
            )
        rows.append({"shift_code": code, "start_min": s, "end_min": e, "hours": hours,
                     "start": fmt_hhmm(s), "end": fmt_hhmm(e), "overnight": e > DAY_MINUTES, "file_order": idx})

    frame = pd.DataFrame(rows)
    table = ShiftCodeTable(frame=frame)
    for r in frame.itertuples(index=False):
        key = (r.start_min, r.end_min)
        if key in table.by_pair:
            table.duplicates.setdefault(key, [table.by_pair[key]]).append(r.shift_code)
        else:
            table.by_pair[key] = r.shift_code
    for (s, e), codes in table.duplicates.items():
        issues.info(
            "SHIFT_CODE_DUPLICATE_PAIR",
            f"{fmt_hhmm(s)}-{fmt_hhmm(e)} has codes {codes}; using first {codes[0]!r} (HR to confirm)",
        )
    return table
