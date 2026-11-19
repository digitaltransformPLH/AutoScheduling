import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from auto_scheduling.calendar import StoreCalendar  # noqa: E402
from auto_scheduling.config import DATA_DIR, Config  # noqa: E402
from auto_scheduling.issues import IssueLog  # noqa: E402
from auto_scheduling.models import StoreParams  # noqa: E402

FORECAST_PATH = DATA_DIR / "forecast_tc_hourly.parquet"
# raw HR file (with the 7 Excel-corrupted codes) kept as a test fixture; the platform reads dbo.dim_shift_code
SHIFT_CODES_PATH = Path(__file__).parent / "fixtures" / "shift_codes.csv"
WEEK = date(2026, 11, 9)


def make_store(store_id="T001", opening=7 * 60, closing=22 * 60, is_24h=False, tcph=8.0, **kw) -> StoreParams:
    base = dict(store_id=store_id, short_name="Test", opening_min=0 if is_24h else opening,
                closing_min=1440 if is_24h else closing, is_24h=is_24h, closed_weekdays=frozenset(),
                setup_minutes=0 if is_24h else 30, clean_minutes=0 if is_24h else 30, tcph_target=tcph,
                tcph_ceiling_mult=1.05, open_staff=2, close_staff=2, min_staff_per_slot=2)
    base.update(kw)
    return StoreParams(**base)


def make_forecast(store_id="T001", week_start=WEEK, hours=range(7, 22), tc=10.0, created_at="2026-11-11 08:00") -> pd.DataFrame:
    rows = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        for h in hours:
            rows.append({"store_id": store_id, "week_start": week_start, "forecast_date": pd.Timestamp(d), "hour": h,
                         "tc_p50": tc, "is_peak": False, "day_type": "NORMAL", "event_key": None,
                         "created_at": pd.Timestamp(created_at), "plan_run_id": "RUN", "forecast_run_id": "F1",
                         "method_version": "M9_v1"})
    return pd.DataFrame(rows)


@pytest.fixture
def cfg():
    return Config(allow_past_weeks=True)


@pytest.fixture
def issues():
    return IssueLog(store_id="T001", week_start=WEEK)


@pytest.fixture
def store_07_22():
    return make_store()


@pytest.fixture
def cal_07_22(store_07_22):
    return StoreCalendar(store_07_22)


requires_forecast = pytest.mark.skipif(not FORECAST_PATH.exists(), reason="forecast parquet not available")
