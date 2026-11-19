"""sched_core: runs db/sql/0001_sched_core.sql"""
import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # db/migrations (sqlfile helper)
from sqlfile import run_sql_file  # noqa: E402

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file('0001_sched_core.sql')


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sched.vw_meta")
    op.execute("DROP TABLE IF EXISTS sched.ScheduleIssues")
    op.execute("DROP TABLE IF EXISTS sched.ScheduleHourlyCoverage")
    op.execute("DROP TABLE IF EXISTS sched.ScheduleDailySummary")
    op.execute("DROP TABLE IF EXISTS sched.ScheduleRoster")
    op.execute("DROP TABLE IF EXISTS sched.ScheduleWeeks")
    op.execute("DROP TABLE IF EXISTS sched.engine_run")
    op.execute("DROP TABLE IF EXISTS sched.meta_build")
