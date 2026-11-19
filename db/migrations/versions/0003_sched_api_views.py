"""sched_api_views: runs db/sql/0003_sched_api_views.sql"""
import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # db/migrations (sqlfile helper)
from sqlfile import run_sql_file  # noqa: E402

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file('0003_sched_api_views.sql')


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sched.vw_input_store_config")
    op.execute("DROP VIEW IF EXISTS sched.vw_input_secondment")
    op.execute("DROP VIEW IF EXISTS sched.vw_input_availability")
    op.execute("DROP VIEW IF EXISTS sched.vw_input_employees")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_runs")
    op.execute("DROP VIEW IF EXISTS sched.vw_schedule_issues")
    op.execute("DROP VIEW IF EXISTS sched.vw_schedule_hourly")
    op.execute("DROP VIEW IF EXISTS sched.vw_schedule_daily")
    op.execute("DROP VIEW IF EXISTS sched.vw_schedule_roster")
    op.execute("DROP VIEW IF EXISTS sched.vw_schedule_week")
    op.execute("DROP VIEW IF EXISTS sched.vw_forecast_weeks")
    op.execute("DROP VIEW IF EXISTS sched.vw_store_list")
