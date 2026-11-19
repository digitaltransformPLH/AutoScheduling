"""`forecast_tc_hourly` loader (SPEC 2.1, 5.1).

Forecast is used as-is [DECISION 12-Nov-2026]: no uplift, no day-type logic,
no re-normalisation. Output = one row per open date x operating slot.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..calendar import StoreCalendar
from ..config import VALID_QUANTILES, Config
from ..issues import IssueLog
from ..timeutil import WEEKDAYS, week_dates
from .loaders import norm_id

LINEAGE_COLS = ["plan_run_id", "forecast_run_id", "method_version", "forecast_origin", "bill_cutoff_date"]
OUTPUT_COLS = ["store_id", "date", "hour", "forecast_tc", "is_peak_forecast", "day_type", "event_key",
               "tc_dine_in", "tc_delivery", "actual_tc", "is_missing_hour", *LINEAGE_COLS]


@lru_cache(maxsize=4)
def _read_cached(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return normalise_forecast(df)


def read_forecast(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    """Read + normalise types (store_id str, forecast_date / week_start date). Cached per file."""
    if isinstance(source, pd.DataFrame):
        return normalise_forecast(source)
    p = Path(source)
    return _read_cached(str(p), p.stat().st_mtime)


def normalise_forecast(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["store_id"] = df["store_id"].map(norm_id)
    df["forecast_date"] = pd.to_datetime(df["forecast_date"]).dt.date
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.date
    df["hour"] = df["hour"].astype(int)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def load_store_week_forecast(
    forecast: pd.DataFrame,
    calendar: StoreCalendar,
    week_start: date,
    cfg: Config,
    issues: IssueLog,
) -> pd.DataFrame:
    """Forecast TC per (open date, operating slot) for one store-week.

    CRITICAL: no rows for the week, duplicate key, negative TC, missing open day,
    unknown quantile. WARNING: hours outside opening hours dropped (with TC share),
    operating hour without a row (TC = 0).
    """
    store = calendar.store
    sid = store.store_id
    q = cfg.forecast_quantile
    empty = pd.DataFrame(columns=OUTPUT_COLS)
    if q not in VALID_QUANTILES or q not in forecast.columns:
        issues.critical("FORECAST_QUANTILE_UNKNOWN", f"forecast quantile column {q!r} not available", store_id=sid)
        return empty

    fc = forecast[(forecast["store_id"] == sid) & (forecast["week_start"] == week_start)]
    if fc.empty:
        issues.critical("FORECAST_MISSING_WEEK", f"no forecast rows for store {sid}, week_start {week_start}", store_id=sid)
        return empty
    if "created_at" in fc.columns and fc["created_at"].nunique() > 1:
        latest = fc["created_at"].max()
        issues.info("FORECAST_MULTIPLE_RUNS", f"{fc['created_at'].nunique()} forecast runs for the week; using latest created_at={latest}",
                    store_id=sid)
        fc = fc[fc["created_at"] == latest]

    dup = fc.duplicated(["store_id", "forecast_date", "hour"], keep=False)
    if dup.any():
        sample = fc.loc[dup, ["forecast_date", "hour"]].drop_duplicates().head(5).to_records(index=False).tolist()
        issues.critical("FORECAST_DUPLICATE_KEY", f"{int(dup.sum())} duplicate (store, date, hour) rows, e.g. {sample}", store_id=sid)
        return empty
    neg = fc[q] < 0
    if neg.any():
        issues.critical("FORECAST_NEGATIVE_TC", f"{int(neg.sum())} rows with negative {q}", store_id=sid)
        return empty

    open_dates = calendar.open_dates(week_start)
    have_dates = set(fc["forecast_date"])
    missing_days = [d for d in open_dates if d not in have_dates]
    if missing_days:
        issues.critical("FORECAST_MISSING_DAY", f"no forecast for open day(s) {[str(d) for d in missing_days]}", store_id=sid)
        return empty

    fc = fc[fc["forecast_date"].isin(open_dates)]
    ops = calendar.operating_hours
    outside = fc[~fc["hour"].isin(ops)]
    total_tc = float(fc[q].sum())
    if not outside.empty:
        dropped = float(outside[q].sum())
        share = dropped / total_tc if total_tc else 0.0
        hours = sorted(outside["hour"].unique().tolist())
        # [DECISION 13-Nov-2026] only opening hours are used; TC outside them is ignored silently
        # (INFO for audit in validation_issues.csv, not shown to users / not written to the DB).
        issues.info(
            "FORECAST_OUTSIDE_OPENING_HOURS",
            f"dropped {len(outside)} rows (hours {hours}) outside {store.hours_label}: TC {dropped:.1f} = {share:.1%} of the week",
            store_id=sid,
        )

    # Full grid of operating slots; missing hours -> TC 0 + warning.
    grid = pd.DataFrame([(d, h) for d in open_dates for h in ops], columns=["forecast_date", "hour"])
    inside = fc[fc["hour"].isin(ops)]
    keep = ["forecast_date", "hour", q, "is_peak", "day_type", "event_key", "tc_dine_in", "tc_delivery", "actual_tc",
            *[c for c in LINEAGE_COLS if c in fc.columns]]
    keep = [c for c in keep if c in inside.columns]
    out = grid.merge(inside[keep], on=["forecast_date", "hour"], how="left")
    out["is_missing_hour"] = out[q].isna()
    for d, g in out[out["is_missing_hour"]].groupby("forecast_date"):
        issues.warning("FORECAST_MISSING_HOUR", f"{d} ({WEEKDAYS[d.weekday()]}): no forecast for hour(s) {g['hour'].tolist()}; TC = 0",
                       store_id=sid, date=d, slot=int(g["hour"].iloc[0]))
    out[q] = out[q].fillna(0.0)
    out["is_peak"] = out["is_peak"].eq(True) if "is_peak" in out else False
    # day-level passthrough columns for the filled rows
    for col in ["day_type", "event_key", *LINEAGE_COLS]:
        if col in out.columns:
            out[col] = out.groupby("forecast_date")[col].transform(lambda s: s.ffill().bfill())

    out = out.rename(columns={"forecast_date": "date", q: "forecast_tc", "is_peak": "is_peak_forecast"})
    out.insert(0, "store_id", sid)
    for c in OUTPUT_COLS:
        if c not in out.columns:
            out[c] = None
    return out[OUTPUT_COLS].sort_values(["date", "hour"]).reset_index(drop=True)


__all__ = ["read_forecast", "load_store_week_forecast", "week_dates"]
