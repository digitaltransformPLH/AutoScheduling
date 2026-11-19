"""Alembic env: version table lives in schema `sched` (created first if missing)."""
from alembic import context
from auto_scheduling.db import get_engine
from sqlalchemy import text

SCHEMA = "sched"


def run_migrations_online() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"IF SCHEMA_ID(N'{SCHEMA}') IS NULL EXEC(N'CREATE SCHEMA {SCHEMA}')"))
    with engine.connect() as conn:
        context.configure(connection=conn, version_table="alembic_version", version_table_schema=SCHEMA,
                          transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("offline mode is not supported; run `alembic upgrade head` against the DB")
run_migrations_online()
