"""Platform settings (env prefix SCHED_, read from <repo>/.env).

SCHED_SQL_CONN accepts the ADO.NET string people copy from SSMS / VS Code
("Data Source=...;Initial Catalog=...;User ID=...;Password=...") or an ODBC string; it is converted
to a SQLAlchemy `mssql+pyodbc` URL by `auto_scheduling.db`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
SERVICE_DIR = PACKAGE_DIR.parent
REPO_ROOT = SERVICE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHED_", env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    sql_conn: str | None = None                  # ADO.NET or ODBC connection string
    db_schema: str = "sched"                     # schema owned by this platform
    data_dir: Path = SERVICE_DIR / "data"
    config_dir: Path = REPO_ROOT / "config"
    allow_past_weeks: bool = False               # True = back-test / demo: past weeks can be scheduled, File 2 marked back-test
    default_availability_week: str | None = None  # YYYY-MM-DD; busy data of this week is reused (back-test)

    @property
    def back_test(self) -> bool:
        return self.allow_past_weeks or bool(self.default_availability_week)
    session_secret: str | None = None            # signs the web login cookie; empty = random per process (logins lost on restart)
    session_hours: int = 10                      # same lifetime as the .NET cookie (Auth:SessionHours)
    cookie_secure: bool = False                  # True behind HTTPS
    api_docs: bool = True                        # Swagger /docs + /openapi.json; False on production


@lru_cache
def get_settings() -> Settings:
    return Settings()
