"""sched_auth_edit_views: runs db/sql/0004_sched_auth_edit_views.sql (login views + input views with last change).

Downgrade drops the auth views only; the altered input views keep their extra columns (harmless for 0003 callers).
"""
import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # db/migrations (sqlfile helper)
from sqlfile import run_sql_file  # noqa: E402

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file('0004_sched_auth_edit_views.sql')


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sched.vw_auth_user_store")
    op.execute("DROP VIEW IF EXISTS sched.vw_auth_user_permission")
    op.execute("DROP VIEW IF EXISTS sched.vw_auth_user")
