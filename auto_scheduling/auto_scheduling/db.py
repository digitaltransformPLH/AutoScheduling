"""SQL Server access shared by the engine (sql source / writer), the ETL loaders and the API."""
from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine

from .settings import get_settings

ODBC_DRIVERS = ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server")


def _pick_driver() -> str:
    try:
        import pyodbc
        installed = set(pyodbc.drivers())
    except Exception:  # pragma: no cover - pyodbc missing
        installed = set()
    return next((d for d in ODBC_DRIVERS if d in installed), ODBC_DRIVERS[0])


def ado_to_odbc(cs: str, driver: str | None = None) -> str:
    """ADO.NET connection string (appsettings / SSMS / VS Code) -> ODBC. ODBC strings (with Driver=) pass through."""
    parts: dict[str, str] = {}
    for item in cs.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            key = k.strip().lower()
            parts[key] = v.strip()
            parts.setdefault(key.replace(" ", ""), v.strip())     # 'Trust Server Certificate' == 'TrustServerCertificate'
    if "driver" in parts:
        return cs
    out = [f"Driver={{{driver or _pick_driver()}}}"]
    server = parts.get("server") or parts.get("data source") or parts.get("address")
    if server:
        out.append(f"Server={server}")
    db = parts.get("database") or parts.get("initial catalog")
    if db:
        out.append(f"Database={db}")
    uid = parts.get("user id") or parts.get("userid") or parts.get("uid") or parts.get("user")
    pwd = parts.get("password") or parts.get("pwd")
    trusted = (parts.get("trusted_connection") or parts.get("integrated security") or "").lower() in ("true", "yes", "sspi")
    if uid and not trusted:
        out.append(f"UID={uid}")
        if pwd is not None:
            out.append("PWD={" + pwd.replace("}", "}}") + "}")
    else:
        out.append("Trusted_Connection=yes")
    if (parts.get("trustservercertificate") or "").lower() in ("true", "yes"):
        out.append("TrustServerCertificate=yes")
    enc = parts.get("encrypt")
    if enc:
        out.append(f"Encrypt={'yes' if enc.lower() in ('true', 'yes', 'mandatory', 'strict') else 'no'}")
    return ";".join(out) + ";"


def describe_connection(odbc: str) -> str:
    """Connection string without the password (for logs)."""
    return re.sub(r"PWD=\{.*?\}(?=;|$)|PWD=[^;]*", "PWD=***", odbc, flags=re.I)


def sqlalchemy_url(conn: str) -> str:
    if conn.startswith("mssql+"):
        return conn
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(ado_to_odbc(conn))


def resolve_conn(conn: str | None = None) -> str:
    cs = conn or get_settings().sql_conn
    if not cs:
        raise RuntimeError("No DB connection: set SCHED_SQL_CONN in <repo>/.env (ADO.NET or ODBC string)")
    return cs


@lru_cache(maxsize=4)
def _engine_for(url: str) -> Engine:
    return create_engine(url, fast_executemany=True, pool_pre_ping=True)


def get_engine(conn: str | None = None) -> Engine:
    return _engine_for(sqlalchemy_url(resolve_conn(conn)))
