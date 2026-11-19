"""dim_shift_code: runs db/sql/0005_dim_shift_code.sql (table dbo.dim_shift_code + seed 210 HR codes + views).

Downgrade drops the views only; the table keeps its data (it may have been edited by HR) — drop it by hand if needed.
"""
import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # db/migrations (sqlfile helper)
from sqlfile import run_sql_file  # noqa: E402

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_sql_file('0005_dim_shift_code.sql')


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sched.vw_input_shift_code")
    op.execute("DROP VIEW IF EXISTS sched.vw_engine_shift_code")
