"""sched_engine_views: runs db/sql/0002_sched_engine_views.sql"""
import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # db/migrations (sqlfile helper)
from sqlfile import run_sql_file  # noqa: E402

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file('0002_sched_engine_views.sql')


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_forecast")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_secondment")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_busy")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_employee")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_store")
