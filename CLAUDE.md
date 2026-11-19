# PLH Auto Scheduling — Phúc Long

Repo có 2 phần chạy song song trên cùng DB SQL Server `AutoScheduling`:
- `src/` — app ASP.NET (Workforce Planning, EF): sở hữu các bảng `dbo.*` (dim_store, dim_store_detail, dim_employee,
  employee_availability_slot, employee_secondment, ops_store_config, forecast_tc_hourly, Users/Roles). Người khác đang phát triển;
  code mới nhất của họ có thể chưa có trên GitHub.
- Platform xếp lịch (Python + React, theo `auto_scheduling/auto_scheduling/web_platform_blueprint.md`): sở hữu schema `sched`.
  - `auto_scheduling/` — engine + ETL (package `auto_scheduling`, SPEC: `auto_scheduling/PLH_Auto_Scheduling_SPEC.md`)
  - `db/` — Alembic + DDL đóng băng `db/sql/000N_*.sql` (schema `sched`: bảng lịch, engine_run, meta_build, view `vw_*`)
  - `services/api` — FastAPI `/api/v1/sched` (package `sched_api`)
  - `services/web` — Vite + React + TS + AntD + TanStack Query + ECharts

User: Thanh (OPS, Phúc Long). Trả lời bằng tiếng Việt, giữ thuật ngữ kỹ thuật tiếng Anh.

## Rules
- Đăng nhập + phân quyền dùng tài khoản .NET (`dbo.Users/Roles/Permissions/UserStores`, chỉ đọc qua `sched.vw_auth_*`); quản lý user/role vẫn ở .NET.
  Mọi API (trừ `/auth/login`) cần đăng nhập và chỉ trả store của user. Quyền theo mã .NET: xem `services/api/src/sched_api/auth.py`.
- Sửa input đã chuyển sang platform (19/11, màn hình sửa bên .NET ngưng dùng): chỉ ghi `dbo` qua `sched_api/input_edit.py`, `excel_io.py`
  và lệnh `load-inputs` — bảng dim_employee, employee_availability_slot, employee_secondment, ops_store_config, dim_store_detail (Open/CloseTime).
  Không xóa nhân viên (chuyển Inactive). Mỗi lần ghi tăng `sched.meta_build` (BuiltBy = email). Không sửa migration / code .NET.
- Engine chỉ đọc input qua view `sched.vw_engine_*`; API đọc qua `sched.vw_*`. Sửa view/bảng = migration mới.
- Mỗi store-week chỉ có 1 lịch: chạy lại thì thay lịch cũ (DELETE ScheduleWeeks → cascade). Giá trị hiển thị cho user bằng tiếng Việt.
- "Bận từ / Bận đến" là giờ bận; bận cả ngày = không xếp ca. Forecast ngoài giờ mở cửa bị bỏ qua (INFO).
- Secondment: store gốc coi ngày đi hỗ trợ là ngày làm (không xếp ca, không phải OFF; vẫn ghi giờ công 07:00–15:00 · 1180 trong roster + File 2); store nhận chỉ xếp ca ngày được mượn.
- Back-test (demo): forecast chỉ có đến tuần 09/11/2026; lịch bận tuần `SCHED_DEFAULT_AVAILABILITY_WEEK` được dùng lại theo thứ.
- Type web sinh từ OpenAPI (`npm run gen:api`), không viết tay. Màu/font chỉ ở `services/web/src/theme/tokens.ts` (template deck).
- Không commit `.env`, `data/*.xlsx`, `reports/`, `dist`, `openapi.json`. Không để lại `__pycache__`.
- Xong mỗi thay đổi: `pytest -q`, `ruff check` file đã sửa, `npm run typecheck` + `npm run build` (build từ PowerShell).

## Commands (từ gốc repo, PowerShell)
- Python: `.venv\Scripts\python` (3.13). Cài: `.venv\Scripts\python -m pip install -e auto_scheduling -e services/api`
- DB migrate: `.venv\Scripts\python -m alembic -c db/alembic.ini upgrade head`
- Nạp input: `cd auto_scheduling; ..\.venv\Scripts\python -m auto_scheduling load-inputs --stores 2189,2030 --week 2026-11-16 --tcph 2189=5.75,2184=6.08,2030=5.64`
- Chạy engine → DB: `..\.venv\Scripts\python -m auto_scheduling run --stores 2189,2184,2030 --week 2026-11-09`
- API: `.venv\Scripts\python -m uvicorn sched_api.main:app --port 8010` → http://127.0.0.1:8010 (web build) · /docs (cổng 8000 đang bị app khác dùng)
- Web dev: `cd services/web; npm run dev` (5173, proxy /api → 8010). Build: `npm run build` (API tự phục vụ `dist`).
- Types: `.venv\Scripts\python -c "import json; from sched_api.main import app; json.dump(app.openapi(), open('services/web/openapi.json','w', encoding='utf-8'))"` rồi `cd services/web; npm run gen:api`
- Test: `.venv\Scripts\python -m pytest -q` · DB thật: `-m integration` (đăng nhập giả bằng dependency override, không ghi dữ liệu)
- `.env` cần `SCHED_SQL_CONN`, `SCHED_SESSION_SECRET` (ký cookie đăng nhập); back-test: `SCHED_ALLOW_PAST_WEEKS=true` +
  `SCHED_DEFAULT_AVAILABILITY_WEEK`; production: `SCHED_ALLOW_PAST_WEEKS=false`, `SCHED_API_DOCS=false`, `SCHED_COOKIE_SECURE=true`
- Mã ca chấm công ở bảng `dbo.dim_shift_code` (platform tạo, migration 0005; engine đọc `sched.vw_engine_shift_code`, API
  `GET /inputs/shift-codes`). Không còn file CSV; test dùng `auto_scheduling/tests/fixtures/shift_codes.csv`. Health: `GET /api/v1/sched/health`
