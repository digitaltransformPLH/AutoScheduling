"""FastAPI app: /api/v1/sched/* (read views in schema `sched`, engine runs in a background thread).

Run:  .venv/Scripts/python -m uvicorn sched_api.main:app --reload --port 8010   ->  http://127.0.0.1:8010/docs
When services/web/dist exists (npm run build) the SPA is served from / as well, so one process is enough for a demo.
"""
from __future__ import annotations

from pathlib import Path

from auto_scheduling.settings import get_settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .routers import auth, inputs, runs, schedule

API_PREFIX = "/api/v1/sched"
WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"

_docs = get_settings().api_docs                 # SCHED_API_DOCS=false on production
app = FastAPI(title="PLH Auto Scheduling API", version="0.1.0", docs_url="/docs" if _docs else None, redoc_url=None,
              openapi_url="/openapi.json" if _docs else None,
              description="Lịch gợi ý theo store-week (engine greedy v0, SPEC v0.3). Đăng nhập bằng tài khoản app .NET (cookie sched_session); "
                          "sửa dữ liệu đầu vào (bảng dbo) và ghi lịch vào schema `sched`.")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, schedule.router, runs.router, inputs.router):
    app.include_router(r, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", tags=["health"], include_in_schema=False)
def health() -> JSONResponse:
    """For monitoring, no login: 200 when the API and the DB answer, 503 otherwise."""
    from auto_scheduling.db import get_engine
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
    except Exception as exc:                           # noqa: BLE001 - report any DB failure as unhealthy
        return JSONResponse(status_code=503, content={"status": "db_error", "detail": exc.__class__.__name__})
    return JSONResponse({"status": "ok", "backTest": get_settings().back_test})


@app.exception_handler(DBAPIError)
def db_error(_: Request, exc: DBAPIError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": f"Không kết nối được SQL Server: {exc.orig.__class__.__name__}"})


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        f = WEB_DIST / path
        return FileResponse(f if path and f.is_file() else WEB_DIST / "index.html")
