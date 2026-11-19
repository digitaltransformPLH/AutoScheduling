# PLH Auto Scheduling

Engine xếp lịch tuần tự động cho từng store-week của Phúc Long Heritage, kèm platform web bản demo (SQL Server → engine → FastAPI → React).
- Đặc tả engine: [PLH_Auto_Scheduling_SPEC.md](PLH_Auto_Scheduling_SPEC.md) (SPEC v0.3, 12-Nov-2026).
- Kiến trúc platform: [auto_scheduling/web_platform_blueprint.md](auto_scheduling/web_platform_blueprint.md).
- Quy tắc + lệnh tắt của cả repo: [CLAUDE.md](../CLAUDE.md) ở gốc repo.
- Logic gốc port từ file demo HTML `PLH Weekly Workforce Planning` (class `WeeklySchedulingEngine`, `ExportModule`; file không còn trong thư mục này).

## Trạng thái (19-Nov-2026)

| Phase | Nội dung | Trạng thái |
|---|---|---|
| P0 Setup | Config, input loaders + validation, shift codes, mock data | ✅ Xong (12-Nov-2026) |
| P1 Demand | Forecast loader, time model, required headcount, peak window, TCPH feasibility, coverage evaluator | ✅ Xong (12-Nov-2026) |
| P2 Optimizer v0 | Pre-flight 6.0 + greedy 6.4 (band-first) | ✅ Xong (13-Nov-2026) |
| P3 Validation & KPI | Hard rules H01–H17, KPI, planning status, recommendations (§8) | ✅ Xong (13-Nov-2026) |
| P4 Output | schedule / slot_coverage / daily_kpi / validation_issues, File 2, workbook review | ✅ Xong (13-Nov-2026) |
| Platform demo | Schema `sched` + view, engine đọc SQL, secondment, FastAPI, web 4 trang | ✅ Xong (18-Nov-2026) |
| Đăng nhập + sửa input | Tài khoản / quyền của app .NET; sửa nhân viên, lịch bận, cho mượn, cấu hình trên web + upload Excel | ✅ Xong (19-Nov-2026), chưa deploy |
| P5 Pilot review | 3 store pilot W46 (2189, 2184, 2030) với data thật, back-test; Thịnh review trên web | 🔄 Chờ review |
| P6 CP-SAT | ortools, so sánh với v0 | — |

Lịch hiện có trong DB (tuần 09/11/2026, back-test với lịch bận tuần 16/11):

| Store | Đánh giá | TCPH tuần / target | % đủ người | % có quản lý | Lỗi / cảnh báo |
|---|---|---|---|---|---|
| 2189 HCM - 457A Trần Hưng Đạo | Tốt | 5,87 / 5,75 ✅ | 100% | 100% | 0 / 0 |
| 2184 HCM - Celadon | Rủi ro cao | 6,02 / 6,08 | 85,7% | 98,1% | 7 / 9 |
| 2030 HCM-CH 26 Huỳnh Thúc Kháng | Rủi ro cao | 5,62 / 5,64 | 91,4% | 100% | 0 / 13 |

## Hướng dẫn chạy

Tất cả lệnh chạy trong **PowerShell**, mở tại gốc repo `D:\1. PLH Github\AutoScheduling` (trừ khi ghi `cd`).

### Lần đầu trên máy mới

1. Cài Python 3.13, Node.js 20+, [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server); máy phải vào được DB `10.235.64.125`.
2. Tạo môi trường Python và cài package:
   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\python -m pip install -e auto_scheduling -e services/api
   ```
3. Copy `.env.example` thành `.env`, điền chuỗi kết nối (hỏi Thanh, **không commit file này**):
   ```
   SCHED_SQL_CONN="Data Source=10.235.64.125,1433;Initial Catalog=AutoScheduling;User ID=...;Password=...;Encrypt=True;Trust Server Certificate=True"
   SCHED_DEFAULT_AVAILABILITY_WEEK=2026-11-16
   SCHED_SESSION_SECRET=<chuỗi ngẫu nhiên dài>
   ```
   - `SCHED_DEFAULT_AVAILABILITY_WEEK` = tuần lấy lịch bận khi back-test; để trống khi đã có forecast của đúng tuần cần xếp.
   - `SCHED_SESSION_SECRET` ký cookie đăng nhập; tạo bằng `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"`.
     Đổi giá trị này = mọi người phải đăng nhập lại. Để trống thì mỗi lần khởi động lại API mọi người cũng phải đăng nhập lại.
4. Tạo / cập nhật schema `sched` (bảng lịch + view). An toàn khi chạy lại:
   ```powershell
   .venv\Scripts\python -m alembic -c db/alembic.ini upgrade head
   ```
5. Build web (1 lần, hoặc sau mỗi lần sửa web):
   ```powershell
   cd services/web; npm install; npm run build; cd ../..
   ```

### Dùng hằng ngày

1. **Mở platform**:
   ```powershell
   .venv\Scripts\python -m uvicorn sched_api.main:app --port 8010
   ```
   Mở trình duyệt http://127.0.0.1:8010 (giữ cửa sổ PowerShell này mở; `Ctrl+C` để tắt). API docs: http://127.0.0.1:8010/docs.
   Cổng 8000 trên máy dev đang bị app khác dùng nên dùng 8010.
2. **Đăng nhập** bằng tài khoản Workforce Planning (.NET) — cùng email / mật khẩu. Chỉ thấy các store được phân cho tài khoản đó
   (Admin: tất cả). Quên mật khẩu / thêm quyền / thêm store: làm trên app .NET (mục Quản lý người dùng). Phiên đăng nhập 10 giờ.
3. **Trên web**: chọn store + tuần ở góc trên →
   - **Tổng quan**: KPI, chart ngày, heatmap độ phủ, timeline "Ai làm lúc nào" kèm TC dự báo, lỗi / gợi ý.
   - **Roster tuần**: lưới nhân viên × ngày.
   - **Dữ liệu đầu vào**: nhân viên, lịch bận, cho mượn, cấu hình store — sửa trực tiếp hoặc tải Excel / upload Excel (xem bên dưới).
   - **Lịch sử chạy**: các lần chạy engine.
   - Nút **Tạo lịch / Tạo lại lịch**: chạy engine cho store-week đang chọn (vài giây), lịch cũ được thay; trang tự làm mới.
   - Nút **File upload chấm công**: tải File 2 (xlsx) của lịch đang xem.
4. **Xếp lịch bằng dòng lệnh** (thay cho nút Tạo lịch, chạy nhiều store một lúc):
   ```powershell
   cd auto_scheduling
   ..\.venv\Scripts\python -m auto_scheduling run --stores 2189,2184,2030 --week 2026-11-09
   cd ..
   ```
   `--week` = thứ Hai của tuần. `--availability-week 2026-11-16` để chọn tuần lịch bận khác mặc định.

### Sửa dữ liệu đầu vào (trang "Dữ liệu đầu vào")

Từ 19-Nov-2026 dữ liệu đầu vào sửa trên platform; màn hình sửa tương ứng bên app .NET ngưng dùng (hai bên dùng chung bảng `dbo`).
Sau khi sửa, bấm **Tạo lại lịch** ở trang Tổng quan để lịch dùng dữ liệu mới.

| Tab | Sửa trên web | Excel (Tải Excel → sửa → Upload Excel) | Quyền .NET cần có |
|---|---|---|---|
| Nhân viên | Thêm, Sửa, Cho nghỉ / Đi làm lại (không xóa) | **Availability File** của store (sheet `Employee Master` + `Availability`). Nhân viên không có trong file → **Ngừng làm**; lịch bận tuần đang chọn bị thay | `Action.Employee.Manage` (nhân viên), `Action.EmployeeAvailability.Manage` (lịch bận) |
| Lịch bận | Bấm vào ô: Rảnh / Bận theo giờ / Bận cả ngày / Nghỉ phép; **Chép từ tuần khác**; chọn tuần khác bằng ô "Tuần khác…" | Cùng file Availability, chỉ thay lịch bận của tuần đang chọn | `Action.EmployeeAvailability.Manage` |
| Cho mượn nhân sự | Thêm, Sửa, Xóa (chặn trùng thời gian) | Sheet `Cho mượn`: thay **toàn bộ** danh sách cho mượn của store | `Action.Employee.Manage` |
| Cấu hình store | Sửa TCPH target, hệ số trần, số người mở / đóng ca / tối thiểu; giờ mở / đóng cửa | Sheet `Cấu hình store`: chỉ cập nhật các store có trong file | `Action.StoreConfig.Manage`; đổi giờ cần `Action.Store.Manage` |

- Upload luôn qua 2 bước: **Kiểm tra file** (xem trước: thêm / cập nhật / ngừng làm / lỗi, chưa ghi gì) → **Xác nhận thay**.
  File còn lỗi thì không ghi gì cả.
- Xem quyền: tài khoản thiếu quyền vẫn xem được nhưng không thấy nút sửa. Hiện role **Manager** trên DB chưa có `Action.Employee.Manage`
  (chỉ Admin sửa được nhân viên / cho mượn) — muốn quản lý store tự sửa thì cấp quyền này cho role Manager trên app .NET.
- Mỗi lần sửa ghi vết vào `sched.meta_build` (ai sửa, sửa gì); bảng `dbo` có cột `UpdatedAt` / `updated_by`.

### Khi có dữ liệu mới

- **Store gửi file nhân viên / lịch bận mới**: cách nhanh nhất là tab Nhân viên → **Upload Excel** (xem trên). Cách dòng lệnh (nhiều store một lúc):
  bỏ file vào `auto_scheduling/data/Availability File {store}.xlsx`, rồi:
  ```powershell
  cd auto_scheduling
  ..\.venv\Scripts\python -m auto_scheduling load-inputs --stores 2189,2030 --week 2026-11-16
  cd ..
  ```
  Ghi nhân viên vào `dbo.dim_employee` và thay lịch bận của tuần đó trong `dbo.employee_availability_slot`.
  Xem thay đổi ở `auto_scheduling/data/out/load_inputs/dq_report.md`. `--employees-only` = chỉ cập nhật nhân viên.
  Lệnh này không chuyển Inactive người vắng mặt trong file (upload trên web thì có).
- **Đổi target TCPH**: tab Cấu hình store, hoặc `load-inputs --tcph 2189=5.75,2184=6.08,2030=5.64` (ghi `dbo.ops_store_config`).
- **Giang nạp forecast tuần mới** vào `dbo.forecast_tc_hourly`: để trống `SCHED_DEFAULT_AVAILABILITY_WEEK` trong `.env`, khởi động lại API, rồi Tạo lịch.
- Sau khi nạp dữ liệu, bấm **Tạo lại lịch** trên web (hoặc lệnh `run`) để lịch dùng dữ liệu mới.

### Kiểm tra sau khi sửa code

```powershell
.venv\Scripts\python -m pytest -q                 # unit test
.venv\Scripts\python -m pytest -q -m integration  # đọc DB thật
.venv\Scripts\python -m ruff check <file đã sửa>
cd services/web; npm run typecheck; npm run build; cd ../..
```
Sửa API thì sinh lại type cho web: xem lệnh "Types" trong `CLAUDE.md`.

### Gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| "Sai email hoặc mật khẩu" | Dùng đúng tài khoản Workforce Planning; sai 5 lần thì đợi 5 phút. Quên mật khẩu: nhờ Admin đặt lại trên app .NET |
| Đăng nhập được nhưng báo "Không có quyền" / không thấy store | Role chưa có quyền xem (`Action.Planning.*`) hoặc chưa được phân store — sửa trên app .NET |
| Upload Excel báo lỗi từng dòng | Sửa đúng các dòng được liệt kê rồi upload lại; nên lấy file từ nút "Tải Excel" để đúng mẫu |
| Web báo "Không kết nối được SQL Server" (API trả 503) | Kiểm tra mạng tới `10.235.64.125`, chuỗi `SCHED_SQL_CONN` trong `.env`, ODBC Driver 18 |
| `Address already in use` khi mở API | Cổng 8010 đang có API khác chạy; tắt cửa sổ cũ hoặc đổi `--port` |
| Web trắng / 404 ở http://127.0.0.1:8010 | Chưa build web: `cd services/web; npm run build` |
| Store không có trong danh sách "Tạo lịch" | Thiếu nhân viên, target (`ops_store_config`) hoặc forecast của tuần đó — xem trang Dữ liệu đầu vào |
| File upload chấm công báo "ca không có mã chấm công" | Có ca không có trong bảng `dbo.dim_shift_code`; báo HR bổ sung mã (thêm dòng vào bảng) |
| Tạo lịch báo "đang chạy" | Đợi lần chạy trước của store-week đó xong (xem Lịch sử chạy) |

### Chạy engine bằng dòng lệnh để debug (xuất file review)

Đọc cùng nguồn dữ liệu với web (SQL Server), không ghi DB trừ khi có `--to-db`:

```powershell
cd auto_scheduling
..\.venv\Scripts\python -m auto_scheduling check --store 2184 --week 2026-11-09 --allow-past-weeks          # input + demand
..\.venv\Scripts\python -m auto_scheduling schedule --stores 2189,2184,2030 --week 2026-11-09 --allow-past-weeks --export-file2
#    -> reports/schedule_{store}_{week}/ schedule.csv, slot_coverage.csv, daily_kpi.csv, validation_issues.csv, roster_grid.csv, kpi.json,
#       review_{store}_{week}.xlsx, {store}_{ShortName}_Upload_Phan_Cong_{từ}-{đến}.xlsx (File 2, khi có --export-file2)
#    --availability-week 2026-11-16 ; --priority band_first|coverage_first ; --to-db ghi luôn vào sched ; -v in cả WARNING/INFO
#    exit 1 nếu bị chặn / CRITICAL
```

Chế độ back-test (`--allow-past-weeks`, hoặc `SCHED_ALLOW_PAST_WEEKS=true` cho web / lệnh `run`): được xếp tuần đã qua, File 2 vẫn xuất được nhưng
kèm WARNING `FILE2_EXPORT_BACKTEST`; publish bị chặn theo §8.4. Production đặt `SCHED_ALLOW_PAST_WEEKS=false`.

## Cấu trúc

Platform chạy **song song** app ASP.NET (`src/`) trên cùng DB `AutoScheduling`: .NET sở hữu bảng input `dbo.*`, platform sở hữu schema `sched`.

```
AutoScheduling/                    (gốc repo)
  CLAUDE.md, pyproject.toml        # quy tắc + ruff/pytest chung; .env (SCHED_SQL_CONN, không commit), .env.example
  auto_scheduling/                 # ← thư mục này: engine + ETL (package auto_scheduling, pip install -e)
    PLH_Auto_Scheduling_SPEC.md, README.md, pyproject.toml
    auto_scheduling/
      config.py            # §3 hằng số (dataclass Config, override per run)
      settings.py          # biến môi trường SCHED_* (.env): sql_conn, allow_past_weeks, default_availability_week, session_secret, ...
      db.py                # chuỗi kết nối ADO.NET → ODBC, SQLAlchemy engine
      issues.py            # Issue / IssueLog: CRITICAL / WARNING / INFO (§7.1 validation_issues)
      timeutil.py          # parse HH:mm, weekday (EN/VI), helper tuần
      models.py            # StoreParams, Employee (+ home_store / borrowed_weekdays), BusyBlock (+ away_to), Shift
      calendar.py          # §4.2/4.3/4.5 window setup/clean, operating slots, slot mapping, ca qua đêm
      planning_window.py   # §8.4 chặn tuần hiện tại/quá khứ, ALLOW_PAST_WEEKS
      pipeline.py          # prepare_store_week() + run_store_week(); nguồn SqlSource (mặc định) / InputPaths (file, debug); secondment
      service.py           # 1 lần chạy platform: sched.engine_run → engine → ghi lịch → data_version
      cli.py, __main__.py  # python -m auto_scheduling load-inputs | run | check | schedule
      web_platform_blueprint.md
      etl/
        load_inputs.py     # nạp Availability File + target OPS vào dbo (dim_employee, availability, ops_store_config)
      inputs/
        sql_source.py      # đọc input qua view sched.vw_engine_* (store, nhân viên, lịch bận, secondment, forecast)
        loaders.py         # §2 dim_store, ops_store_config, dim_employee, busy + validation
        availability_file.py # "Availability File {store}.xlsx" (2 sheet) -> dim_employee + busy
        forecast.py        # §2.1/5.1 forecast_tc_hourly
        shift_codes.py     # §7.3 dim_shift_code (+ sửa mã bị Excel làm hỏng)
      demand/
        slots.py           # §5.2 required_staff, daily band, TCPH feasibility, peak window
        coverage.py        # §5.3 slot coverage + daily TCPH
      optimizer/
        preflight.py       # §6.0 template ca (FT 8h / PT 4–8h / special 4h) lọc theo shift code
        roster.py          # trạng thái lịch: shift, OFF/AL, ngày đi hỗ trợ, availability (H02/H03/H17), coverage theo ngày
        objective.py       # §6.3 objective band-first (coverage_first giữ làm option)
        greedy.py          # §6.4 greedy v0 (bước 1–13)
      validation/
        rules.py           # §6.1 H01–H17 + S04 trên roster cuối
        kpi.py             # §8.1–8.3 utilization / coverage / planning status / recommendations
      output/
        tables.py          # §7.1 schedule, slot_coverage, daily_kpi, validation_issues + roster grid
        attendance.py      # §7.2 File 2 "Upload Phân Công" (openpyxl, blocking validation)
        db_writer.py       # ghi lịch vào schema sched (giá trị tiếng Việt, thay lịch cũ của store-week)
        review.py          # workbook review cho pilot (Roster / Coverage / Daily KPI / Issues)
    data/                # (không commit) Availability File {store}.xlsx cho `load-inputs`, out/ = DQ report
    tests/                 # pytest (81 unit + 11 integration); fixtures/shift_codes.csv = file mã ca gốc cho test
    reports/               # output của `check` / `schedule` (bị .gitignore)
  db/                      # Alembic + DDL đóng băng db/sql/000N_*.sql (schema sched)
  services/api/            # FastAPI /api/v1/sched (package sched_api: auth.py đăng nhập, input_edit.py + excel_io.py sửa input, routers/)
  services/web/            # Vite + React + TS + AntD + TanStack Query + ECharts
```

## Bảng trong DB

### Input — bảng `dbo` của app .NET, engine chỉ đọc qua view `sched.vw_engine_*`

| View | Bảng nguồn | Engine dùng |
|---|---|---|
| `vw_engine_store` | `dim_store` + `dim_store_detail` (OpenTime/CloseTime) + `ops_store_config` | Giờ mở/đóng, `tcph_target`, số người mở/đóng/tối thiểu |
| `vw_engine_employee` | `dim_employee` | Nhân viên (mã = `EmployeeNumber`), vị trí, FT/PT, labor group, trạng thái |
| `vw_engine_busy` | `employee_availability_slot` | 1 dòng / nhân viên / ngày; `BusyFrom/BusyTo` NULL = rảnh, `IsPaidLeave` = AL |
| `vw_engine_secondment` | `employee_secondment` | Nhân viên cho store khác mượn (store gốc, store nhận, từ ngày – đến ngày) |
| `vw_engine_forecast` | `forecast_tc_hourly` | TC theo giờ (`tc_p50`), hiện có W44–W46/2026 |
| `vw_engine_shift_code` | `dim_shift_code` (**platform tạo**, migration 0005) | Mã ca chấm công: khớp đúng (giờ vào, giờ ra); trùng giờ thì lấy `SortOrder` nhỏ nhất; `EndTime <= StartTime` = ca qua đêm |

Đăng nhập: `vw_auth_user` (dbo.Users + Roles, gồm `PasswordHash` dạng ASP.NET Identity), `vw_auth_user_permission`
(RolePermissions → Permissions.Code), `vw_auth_user_store` (UserStores → dim_store.Code). Platform chỉ đọc các bảng này.

### Output — schema `sched` (Alembic `db/`), API chỉ đọc qua view `sched.vw_*`

Mỗi bảng lịch đều có `StoreCode` + `WeekStart`. **Mỗi store-week chỉ có 1 lịch**: chạy lại thì xóa lịch cũ (`ScheduleWeeks`, các bảng con xóa theo)
và ghi lịch mới trong cùng 1 transaction. Giá trị hiển thị bằng tiếng Việt.

| Bảng | 1 dòng là | Nội dung chính |
|---|---|---|
| `ScheduleWeeks` | 1 store / 1 tuần | Tên store, giờ mở/đóng, trạng thái (Nháp / Không xếp được), đánh giá (Tốt / Cần chú ý / Rủi ro cao), TCPH target vs thực tế, % đủ người, % có quản lý, số lỗi/cảnh báo, tuần lịch bận dùng, run, ghi chú |
| `ScheduleRoster` | 1 nhân viên / 1 ngày | Thứ, tên, vị trí, FT/PT, store gốc (nhân viên mượn), loại ngày (Làm / OFF / Nghỉ phép / Không xếp ca / Đi hỗ trợ / Ở store gốc), giờ vào/ra, số giờ, mã ca, vai trò ca (Mở cửa / Đóng cửa / Quản lý giữa ca …), ghi chú |
| `ScheduleDailySummary` | 1 store / 1 ngày | TC dự báo, giờ công Regular/Training/NSO, TCPH, khoảng giờ công để đạt target, số giờ-người thiếu, số giờ không có quản lý, số người mở/đóng |
| `ScheduleHourlyCoverage` | 1 store / 1 giờ | Khung giờ (07:00-08:00), TC dự báo, cần bao nhiêu người, xếp bao nhiêu, số quản lý, thiếu bao nhiêu, trạng thái (Đủ / Dư / Thiếu người / Thiếu quản lý) |
| `ScheduleIssues` | 1 vấn đề | Mức độ (Lỗi / Cảnh báo / Gợi ý), ngày, nhân viên, nội dung, mã lỗi để tra SPEC |
| `engine_run` | 1 lần chạy | Store, tuần, tuần lịch bận, trạng thái (queued / running / done / failed), đánh giá, người chạy, thời gian |
| `meta_build` | 1 lần dữ liệu thay đổi | `DataVersion` tăng dần (web dùng để tự làm mới) |

Engine **không** ghi vào `DailyPlanningMetrics` (bảng publish của .NET). Issue mức INFO và cảnh báo dữ liệu hệ thống
(`SHIFT_CODE_SCI_NOTATION_REPAIRED`) không ghi vào `ScheduleIssues`.

Xem lịch một store-week:

```sql
SELECT Weekday, EmployeeName, Position, DayType, StartTime, EndTime, Hours, ShiftCode, ShiftRole, Note
FROM sched.vw_schedule_roster
WHERE StoreCode = N'2184' AND WeekStart = '2026-11-09'
ORDER BY SortOrder, WorkDate;
```

API `/api/v1/sched`: `/health` (không cần đăng nhập), `/auth/login|logout|me`, `/meta`, `/stores`, `/forecast-weeks`, `/schedules`,
`/schedules/{store}/{week}/overview|roster|file2`, `POST /runs` + `/runs`, `/inputs/...` (xem + sửa + `/inputs/excel/...`).
Response `{data, meta}` camelCase; `meta.backTest` cho web biết đang ở chế độ back-test.

## Dữ liệu không nằm trong DB

| File | Ghi chú |
|---|---|
| `data/Availability File {store}.xlsx` | Chỉ khi dùng lệnh `load-inputs`; trên web dùng Upload Excel. **Không commit** (data cá nhân) |
| `tests/fixtures/shift_codes.csv` | Bản gốc file mã ca của HR (còn 7 mã bị Excel làm hỏng) — chỉ để test chạy không cần DB |

Mọi dữ liệu engine dùng (giờ mở cửa, target, nhân viên, lịch bận, cho mượn, forecast, **mã ca**) đều đọc từ DB.

## Quy tắc nghiệp vụ đã chốt

| Ngày | Quy tắc |
|---|---|
| 05-Nov | Ca FT 8h không nghỉ; sàn 2 người/slot |
| 12-Nov | Setup/clean cố định 30' từ config (không có cột trong `dim_store`), store 24h = 0 |
| 13-Nov | "Bận từ / Bận đến" là **giờ bận**; bận cả ngày = không xếp ca |
| 13-Nov | Forecast ngoài giờ mở cửa bị bỏ qua (INFO, không cảnh báo) |
| 13-Nov | Giao ca 30' (store 06:30–22:30): khi bằng điểm ưu tiên ca có mặt thật nhiều hơn (cách C) |
| 13-Nov | Trạng thái ô giờ theo số người nguyên: chỉ "Dư người" khi xếp > cần (4/4 = Đủ người) |
| 13-Nov | Mỗi store-week chỉ 1 lịch, chạy lại thay lịch cũ; bảng / giá trị thân thiện, tiếng Việt |
| 18-Nov | Chạy song song .NET; back-test: forecast đến W46, lịch bận tuần 16/11 dùng lại theo thứ |
| 18-Nov | Secondment: store gốc coi ngày đi hỗ trợ là ngày làm (không xếp ca, không thành OFF); store nhận chỉ xếp ca ngày được mượn |
| 19-Nov | Ngày đi hỗ trợ **vẫn ghi giờ công**: ca 07:00–15:00, 8h, mã 1180 trong roster DB và File 2 (không đánh OFF) |
| 19-Nov | Đăng nhập bằng tài khoản .NET (platform tự kiểm tra mật khẩu); sửa input chuyển sang platform, màn hình .NET tương ứng ngưng dùng |
| 19-Nov | Upload Excel = thay: nhân viên vắng trong file → Ngừng làm (không xóa); lịch bận tuần được thay; cho mượn của store được thay |

## Nhật ký thực thi

### 12-Nov-2026 — P0 + P1

**Đã làm**
1. Khung project: `requirements.txt` (pandas, pyarrow, openpyxl, tzdata, pytest; ortools để P6), package `auto_scheduling/`.
   Đổi tên `io/` (theo §10) thành `inputs/` để không đè module `io` của stdlib.
2. `config.py`: toàn bộ hằng số §3 trong một dataclass `Config`; `with_overrides()` tạo bản sao cho mỗi lần chạy.
   Tham số theo store (tcph_target, open/close staff, min staff) được resolve thành `StoreParams`. Setup/clean cố định 30' từ config (không có cột trong `dim_store`), store 24h = 0.
3. `issues.py`: `IssueLog` dùng chung, severity CRITICAL (= "error" trong spec: store-week không được xếp) / WARNING / INFO.
4. Loader và validation §2:
   - `dim_employee`: `LABOR_GROUP_REQUIRED`, `INVALID_LABOR_GROUP`, `INVALID_EMPLOYMENT_TYPE`, bỏ nhân viên inactive/terminated, `DUPLICATE_EMPLOYEE_KEY` (giữ dòng đầu), `NO_MANAGER` (Training manager không tính).
     Phân loại theo §4.1 / demo `U.pos`: SM=1, ASM=2, SS=3; Barista Trainer = `can_act_as_manager`; `is_fixed` = FT hoặc manager; `is_special_pt` = PT Training/NSO.
   - `busy`: weekday nhận EN/VI (Mon, T2, Thứ Hai, CN…); `BAD_BUSY_TIME`, `ORPHAN_AVAILABILITY_RECORD`; AL chỉ cho FT/manager (PT → `AL_FOR_NON_FIXED_IGNORED`); > 6 ngày AL → `TOO_MANY_AL_DAYS`.
   - `dim_store` + `ops_input`: `STORE_HOURS_MISSING`, `STORE_HOURS_INVALID`, `TCPH_TARGET_MISSING` (không có default chain-wide); store 24h không có setup/clean, giờ 00:00–24:00.
5. `shift_codes.py`: match chính xác (start, end); mã qua đêm lưu end + 1440; cặp trùng → lấy mã đầu theo thứ tự file (INFO `SHIFT_CODE_DUPLICATE_PAIR`); sửa mã bị hỏng do định dạng khoa học.
6. `forecast.py` (§2.1/5.1): lọc store + week_start, lấy `created_at` mới nhất, dùng nguyên `tc_p50` (hoặc `FORECAST_QUANTILE`).
   CRITICAL: `FORECAST_MISSING_WEEK`, `FORECAST_DUPLICATE_KEY`, `FORECAST_NEGATIVE_TC`, `FORECAST_MISSING_DAY`.
   WARNING: `FORECAST_MISSING_HOUR` (TC = 0). INFO: `FORECAST_OUTSIDE_OPENING_HOURS` (kèm % TC bị bỏ; từ 13-Nov chỉ ghi INFO, forecast ngoài giờ mở cửa bị bỏ qua).
   Ngày đóng cửa (closed_sat/sun) không bắt buộc có forecast.
7. `calendar.py` (§4.2/4.3/4.5): window `[opening − setup, closing + clean]`; slot 60' trên lưới giờ; slot mapping kiểu demo (`floor_hour(start) ≤ slot`, `slot_end ≤ ceil_hour(end)`); store 24h: 24 slot, ca qua đêm trả về slot của ngày D+1; nhận diện opener/closer.
8. `demand/slots.py` (§5.2): `labor_hours = TC / tcph_target`; làm tròn half-up tự viết (không dùng `round()` vì Python làm tròn kiểu banker); `required_staff = max(min_staff, rounded)`, MOD nằm trong required_staff.
   Daily: band giờ công `[TC/(tcph×1.05), TC/tcph]`, `max_achievable_tcph = TC / (2 × số slot)` → `TCPH_TARGET_INFEASIBLE`.
   Peak window port từ demo `PeakWindowEngine` (gộp khi cách ≤ 1 slot và tổng ≤ 8h, kéo dài cho đủ ≥ 4h).
9. `demand/coverage.py` (§5.3): scheduled_staff gồm mọi labor group; MOD = manager-group không phải Training, nếu không có thì Barista Trainer (tối đa 1); AL không phủ slot; status MANAGER_GAP > STAFF_GAP > OVERSTAFF > OK; TCPH ngày không tính NSO, `tcph_nso` tính tất cả.
   Lệch có chủ đích so với demo: demo tính `staffGap = max(laborGap phân số, required − scheduled)`, ở đây theo spec là `required_staff − scheduled_staff`.
10. `planning_window.py` (§8.4): week_start phải là thứ Hai và lớn hơn hẳn thứ Hai của tuần hiện tại, theo giờ server Asia/Ho_Chi_Minh; `allow_past_weeks` bỏ qua check này, còn `can_publish()` luôn False trong chế độ đó.
11. `pipeline.prepare_store_week()` gom các bước P0 + P1; thêm check `INSUFFICIENT_MANAGER_CAPACITY` (§4.4).
12. CLI `mock` / `check`; 45 test pytest (§9 phần demand/input/planning window), tất cả pass.

**Kết quả chạy `check` tuần 2026-11-09 (mock, tcph_target = 8)**

| Store | Giờ | Slot/ngày | ADTC | Target 8 khả thi? | CRITICAL |
|---|---|---|---|---|---|
| 2001 | 07:00–23:00 | 16 | 300–399 | 7/7 ngày | 0 |
| 2024 | 06:00–22:00 | 16 | 88–168 | 0/7 (max 2.8–5.3) | 0 |
| 2054 | 06:00–23:00 | 17 | 231–255 | 1/7 (max 6.8–7.5) | 0 |
| 2077 | 24h | 24 | 167–197 | 0/7 (max 3.5–4.1) | 0 |

**Phát hiện cần xử lý**
1. **`PLH_Shift_Code_Map.csv` bị Excel làm hỏng 7 mã**: `11E1..11E7` bị lưu thành `110, 1100, …, 110000000`. Đã đối chiếu từng cặp (start, end) với `PLH_SHIFT_CODE_MAP` trong demo HTML (210/210 khớp). Loader tự sửa và ghi WARNING, nhưng **HR cần sửa file gốc**, và khi mở bằng Excel phải định dạng cột `shift_code` là Text.
2. Cặp trùng có thể gặp phải ngoài 3 cặp spec đã nêu: **05:30–13:30 `11C1`/`11E2`** (ca mở 8h của store 06:00). Bổ sung vào Q4.
3. **Giờ forecast khác giả định của spec**: tuần W46 có 145/264 store forecast giờ 6..22 (tức 06:00–23:00), 44 store giờ 7..22 (07:00–23:00); chỉ 4 store đúng 06:00–22:00 và 3 store đúng 07:00–22:00. Store 2001 (fixture của spec, giả định 07:00–22:00) có forecast giờ 22. Cần giờ mở/đóng thật (Q9).
4. **Store 24h**: chỉ 2077 có đủ 24 dòng hầu hết các ngày (2072 có 3 ngày, 9999 có 2 ngày); spec ghi 4 store. 19 store có giờ 0–23 nhưng thiếu nhiều giờ ở giữa → không phải 24h thật.
5. **TCPH target 8 không khả thi** ở 3/4 store pilot, đúng như cảnh báo trong Q10. Theo band-first, optimizer sẽ cắt về sàn 2 người/slot.
6. Các điểm trong spec cần chốt trước P2 (từ lần review plan):
   - Store 06:00–22:00: theo slot mapping §4.3, ca mở 05:30–13:30 + ca đóng 14:30–22:30 **đã phủ đủ 16 slot** → không có MOD gap, trái với test §9.
   - Store 24h: H10 không áp dụng, mà `MAX_MANAGER_GAP_FILL_SHIFTS = 2` chỉ phủ được 16h/24h → ngày nào cũng ra MANAGER_GAP.
   - FT luôn đủ 48h, band-first không cắt được → band vỡ khi số FT vượt nhu cầu.

### 13-Nov-2026 — P2 + P3 + P4, chạy pilot W46 với data thật

**Đã làm**
1. `inputs/availability_file.py`: đọc workbook "Availability File {store}.xlsx" (2 sheet) thành `dim_employee` + `busy`.
   Giờ dạng `15:00:00` (Excel) được `parse_hhmm` nhận. Tham số `busy_semantics`:
   `busy` (mặc định, đúng theo header "Bận từ/Bận đến") hoặc `available` (store điền ngược: khung giờ *có thể* làm → busy = phần còn lại).
   `InputPaths.real()` ưu tiên file này; không có thì đọc `data/real/dim_employee.csv` + `busy.csv`.
2. `optimizer/preflight.py` (§6.0): template trên lưới :00/:30 trong `[setup_start, clean_end]` (store 24h: cả ngày, cho phép qua đêm);
   bỏ template không có mã (`SHIFT_TEMPLATE_NO_CODE`, INFO); thiếu mã ca mở/đóng FT hoặc không có ca 8h nào phủ MOD gap → `REQUIRED_SHIFT_NO_CODE` (CRITICAL).
3. `optimizer/roster.py`: `Roster` giữ shift theo (employee, date), OFF / forced OFF / AL, busy block; `available()` gồm H02, H03, H17;
   `day_state()` tính coverage một ngày và nhận `extra` / `without` để chấm điểm nước đi giả định mà không sửa roster.
4. `optimizer/objective.py` (§6.3): band-first (1e8·out_of_band² + …); `coverage_first` giữ làm option qua `--priority`.
5. `optimizer/greedy_v0.py` (§6.4), khác biệt / diễn giải so với spec:
   - Bước 1 OFF: chọn ngày mà **giờ FT cố định vượt band max nhiều nhất** (band-first), tie → ADTC thấp nhất; manager trước, tối đa 1 manager OFF/ngày;
     forced OFF từ busy (> 1 ngày → `FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS` CRITICAL, nhân viên đó chỉ xếp những ngày còn lại); AL không bao giờ trùng OFF.
   - Bước 2: manager mở/đóng theo rank SM→ASM→SS (tie: ít giờ hơn), Barista Trainer chỉ khi không còn manager; MOD gap-fill tối đa `MAX_MANAGER_GAP_FILL_SHIFTS`
     (store 24h: tối thiểu 3); ghép Training manager vào đúng ca của một Regular manager (H12).
   - Bước 3: FT đặt theo score demo (160·MOD gap + 100·labor gap + 20·peak − 30·overstaff), **thêm pass cải thiện cửa sổ FT theo objective** (không chạm ca LOCKED)
     để FT không dồn hết vào buổi sáng.
   - Bước 4: PT mở/đóng (H09) không bị band chặn (hard rule).
   - Bước 5: PT lấp gap, PT ít giờ nhất trước, rồi kéo dài ca PT có sẵn; **chỉ nhận khi objective giảm** → band-first.
   - Bước 6–7 gộp: local search trên PT không LOCKED (cắt/xóa/dời/kéo ±30'/±1h), nhận khi objective giảm, không bao giờ xuống dưới sàn H09/H11/H13.
   - Bước 8–10: TCPH ngày/tuần ngoài band → WARNING `TCPH_OUT_OF_BAND`; evening balance nằm trong objective (S08).
   - Bước 11: hoán đổi ca PT từ người nhiều giờ nhất sang người ít giờ nhất khi chênh ≥ 8h. Bước 12: sàn 2 người/slot. Bước 13: special PT 4h tới 5 ngày/20h
     (NSO luôn xếp vì không tính TCPH; Training chỉ khi không phá band → `SPECIAL_PT_UNDER_TARGET` INFO).
   - Cuối cùng báo gap còn lại: `COVERAGE_SACRIFICED_FOR_TCPH_BAND` (có PT rảnh nhưng thêm 4h sẽ phá band), `STAFF_GAP_NO_AVAILABLE_STAFF`, `STAFF_GAP_NOT_WORTH_FILLING`.
6. `validation/rules.py`: check lại H01–H17 trên roster cuối (vi phạm = CRITICAL với đúng mã lỗi spec), S04 = WARNING.
   `validation/kpi.py`: utilization, coverage %, MOD coverage %, planning status (§8.2), top-5 recommendations (§8.3).
7. `output/tables.py` (§7.1) + `roster_grid`; `output/attendance.py` (§7.2): đúng 9 header, Template 2003, ngày `dd.MM.yyyy` dạng text, mã số → number,
   giờ = Excel time `HH:mm`, OFF để trống H/I, thứ tự dòng Regular→Training→NSO / SM→ASM→SS→BT→Crew / FT trước PT; chặn khi có ca không có mã.
   `output/review.py`: workbook review (Roster có `*` = ca LOCKED, Coverage tô màu theo status).
8. `pipeline.run_store_week()` + CLI `schedule`; thêm check `FIXED_LABOR_EXCEEDS_TCPH_BAND` (giờ FT cố định cả tuần > band max tuần).
9. Thêm 21 test (pre-flight, hard rules trên team giả lập, H15, MOD gap-fill store 06:30–22:30, Training manager pair, File 2, loader Availability) → 65 test pass.

**Kết quả chạy W46 (2026-11-09), data thật, `busy_semantics=busy`**

| Store | Giờ | NV (mgr/FT/PT) | TCPH tuần (band) | Coverage | MOD | Status | CRITICAL |
|---|---|---|---|---|---|---|---|
| 2189 | 07:00–22:00 | 15 (3/1/11) | 5.90 (5.75–6.04) ✅ 7/7 ngày | 100% | 100% | ATTENTION | 0 |
| 2184 | 06:30–22:30 | 21 (3/6/12) | 6.01 ✗ (3/7 ngày) | 85.9% FAIL | 98.1% | CRITICAL | 7 (5 × H15, 2 × H11 slot 14) |
| 2030 | 07:00–22:00 | 16 (3/4/9) | 5.62 ✗ (5.64–5.92; 2/7 ngày) | 91.4% FAIL | 100% | CRITICAL | 0 |

**Phát hiện cần xử lý**
1. **2184 – "Bận từ/Bận đến" là giờ bận** [DECISION 13-Nov-2026, Thanh]: ai điền bận cả ngày (vd `07:00–23:00`) thì ngày đó không đi làm được.
   Mặc định `busy_semantics=busy` là đúng; option `available` chỉ giữ lại cho trường hợp store khác điền ngược. Hệ quả với 2184:
   5 FT (Quỳnh Anh, Minh Thư, Tú Trinh, Văn Dương, Văn Ninh) bận cả ngày > 1 ngày → `FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS` (H15) và chỉ được xếp những ngày còn rảnh
   (Văn Ninh 0h); 2 PT (Hoàng Đình Trường, Phan Trọng Quân) bận cả tuần → 0h.
2. **Giờ FT cố định đã lấp gần hết band → PT gần như 0h** (band-first): 2030 có 7 FT (SM, 2 SS, BT, 3 crew) = 336h/tuần trong khi band 328–346h;
   2184 có 9 FT = 432h/tuần trong khi band 427–449h. Hệ quả: PT chỉ nhận ca 4h mở/đóng (H09) hoặc 0h; T7/CN của 2030 TCPH 5.26–5.41 vì 5 FT × 8h đã vượt
   band 37–38h. Phải chốt với Thịnh: giảm FT/đổi target, hay chấp nhận ngoài band (Q10/Q12).
3. **Band-first và ngưỡng KPI §8.1 mâu thuẫn**: giữ band thì coverage < 95% → `FAIL` → planning status `CRITICAL` dù không vi phạm hard rule nào (2030).
   Cần quyết định ngưỡng coverage áp dụng ra sao khi gap là do band (`COVERAGE_SACRIFICED_FOR_TCPH_BAND`).
4. **Store 06:30–22:30 (2184)**: window 06:00–23:00 = 17h, ca mở 06:00–14:00 + ca đóng 15:00–23:00 hở slot 14:00–15:00 → ngày nào cũng cần ca manager thứ 3;
   3 manager × 6 ngày = 18 < 21 ca → ngày manager OFF phải dùng Barista Trainer; ngày BT cũng bận → `INVALID_MANAGER_COVERAGE`. Store này cần ≥ 4 manager-group.
   Ngoài ra 60-min slot bỏ 06:30–07:00 và 22:00–22:30 (1.8% TC, `FORECAST_OUTSIDE_OPENING_HOURS`).
5. Nhiều ca PT 4h (13–15 ca/tuần) vì local search cắt giờ PT để giữ band; S11 (2 điểm/ca ngắn) quá nhỏ so với overstaff (25/h). Cân nhắc tăng S11 hoặc đặt min PT 5h.
6. Training PT (2189) nhận 0h vì giờ Training tính vào TCPH và band đã đầy; NSO đủ 5 ngày/20h.
7. **Lủng 30' lúc giao ca ở store 06:30–22:30 (2184)** [DECISION 13-Nov-2026, Thanh: cách C]. Slot mapping 60' (§4.3) tính ca 06:30–14:30 phủ trọn ô 14:00–15:00,
   nên 06:30–14:30 và 07:00–15:00 bằng điểm; engine chọn ca sớm hơn → 6/7 ngày không ai trên sàn 14:30–15:00 (ca đóng bắt đầu 15:00).
   Sửa: khi bằng điểm, ưu tiên ca có nhiều phút thật sự có mặt trong các ô được tính (`GreedyScheduler.presence`), áp dụng ở bước 2 (MOD gap-fill),
   bước 3 (FT + pass cải thiện), bước 5, bước 6–7 và bước 12. Sau sửa 2184 có 2–4 người lúc 14:30–15:00 mỗi ngày.
   **Còn lại**: KPI vẫn tính theo ô 60' nên có thể báo "đủ người" sai ở giờ giao ca; muốn đúng hẳn phải chuyển sang ô 30' (cách A).

### 18-Nov-2026 — Web platform (SQL Server → engine → FastAPI → React), bản demo

Theo `auto_scheduling/web_platform_blueprint.md`, chạy **song song** app .NET (quyết định của Thanh): .NET sở hữu bảng input `dbo.*`,
platform sở hữu schema `sched`. Lệnh chạy: xem `CLAUDE.md` ở gốc repo.

**Hiện trạng DB lúc bắt đầu**: app .NET đã thêm `dim_employee`, `employee_availability_slot` (1 dòng / nhân viên / ngày, NULL = rảnh),
`employee_secondment`, `ops_store_config` (`store_id` = `dim_store.Id`), `forecast_tc_hourly` (W44–W46), `dim_store_detail.OpenTime/CloseTime`.
5 bảng `dbo.Schedule*` tạo hôm 13/11 đã bị xóa; tạo lại trong schema `sched`. Đã gỡ entity / migration EF / script 007 cho các bảng đó.

**Đã làm**
1. `.venv` (Python 3.13, pandas 3.1, SQLAlchemy 2.1, FastAPI 0.163, Alembic 1.20); `pyproject.toml` cho engine + API; `.env` (`SCHED_SQL_CONN`, không commit).
2. `db/`: Alembic chạy DDL đóng băng `db/sql/0001_sched_core.sql` (bảng lịch, `engine_run`, `meta_build`, `vw_meta`),
   `0002_sched_engine_views.sql` (`vw_engine_store/employee/busy/secondment/forecast` map dbo → input contract của engine),
   `0003_sched_api_views.sql` (`vw_store_list`, `vw_schedule_*`, `vw_input_*`, `vw_engine_runs`).
3. ETL `load-inputs` (`etl/load_inputs.py`): nạp `Availability File` 2189, 2030 vào `dim_employee` (+15, +16) và lịch bận tuần 16/11
   (105 + 112 dòng); 2184 đã có sẵn và **khớp 100%** với file Excel (147/147 dòng, 21/21 nhân viên) nên giữ nguyên. `ops_store_config`:
   thêm 2189 = 5.75, 2184 = 6.08, 2030 = 5.64; xóa 2 dòng test (2001, 2002). Có DQ report `data/out/load_inputs/dq_report.md`.
4. Engine đọc SQL (`inputs/sql_source.py`, `SqlSource`): giờ mở/đóng từ `dim_store_detail`, target từ `ops_store_config`, nhân viên, lịch bận
   theo ngày, forecast từ DB. **Back-test**: lịch bận tuần 16/11 dùng lại theo thứ cho tuần 09/11 (forecast chỉ đến W46; Giang sẽ cập nhật).
   Kiểm tra: 2189 và 2030 ra **cùng roster** khi đọc file và đọc SQL.
5. **Secondment** (`employee_secondment`): store gốc — ngày đi hỗ trợ là ngày làm (không xếp ca, không thành OFF, tính 8h vào 48h tuần);
   store nhận — nhân viên được thêm, chỉ xếp ca ngày được mượn, không áp luật OFF / 6 ngày (thuộc store gốc). Ví dụ: SM Hồng Phú (2184)
   hỗ trợ 2023 ngày 16–17/11 → back-test thứ 2–3: "Đi hỗ trợ", làm 4 ca + OFF thứ 7 = 48h. File 2 + roster DB: ngày đi hỗ trợ vẫn ghi giờ công — ca 07:00–15:00, 8h, mã 1180 (như AL; config `away_shift_start/end`) [DECISION 19-Nov-2026].
6. `service.py` + lệnh `run`: tạo `sched.engine_run` (queued → running → done/failed), chạy engine, thay lịch của store-week, tăng `data_version`.
   KPI không còn tính cảnh báo dữ liệu hệ thống (`SHIFT_CODE_SCI_NOTATION_REPAIRED`) → 2189 = **Tốt**.
7. API FastAPI (`services/api`): `/meta`, `/stores`, `/forecast-weeks`, `/schedules`, `/schedules/{store}/{week}/overview|roster|file2`,
   `POST /runs` (thread nền, 1 run một lúc, chặn chạy trùng), `/runs`, `/inputs/store-config|employees|availability|secondments`.
   Response `{data, meta}` camelCase; API phục vụ luôn bản web build (1 process cho demo).
8. Web (`services/web`): Tổng quan (port mockup: KPI, chart ngày, heatmap độ phủ, timeline "Ai làm lúc nào" + TC dự báo, lỗi/gợi ý,
   kết quả vs mục tiêu, tóm tắt nhân sự), Roster tuần (lưới nhân viên × ngày), Dữ liệu đầu vào (nhân viên, lịch bận, cho mượn, cấu hình),
   Lịch sử chạy. Store/tuần trên URL; nút "Tạo lịch" + "File upload chấm công". Kiểm tra bằng Chrome headless: 4 trang, 0 lỗi console.
9. Test: 78 unit + 3 integration (DB thật) pass; ruff sạch trên code mới.

**Hạn chế / còn lại**
- Chưa có đăng nhập và deploy (demo). Cổng 8000 trên máy dev đang bị app khác dùng → API chạy cổng 8010.
- Message lỗi chi tiết vẫn bằng tiếng Anh (UI có nhãn tiếng Việt cho các lỗi hay gặp).
- Store nhận hỗ trợ (2023) chưa có nhân viên / target nên chưa xếp lịch được; logic store nhận mới kiểm tra bằng unit test.

### 19-Nov-2026 — Ngày đi hỗ trợ vẫn ghi giờ công

[DECISION 19-Nov-2026, Thanh] Ngày nhân viên đi hỗ trợ store khác **không đánh OFF**, vẫn ghi nhận giờ công ở store gốc.
`employee_secondment` không có giờ nên dùng ca giống nghỉ phép: **07:00–15:00, 8h, mã 1180** (config `away_shift_start` / `away_shift_end`).
1. `output/db_writer.py`: dòng "Đi hỗ trợ" trong `ScheduleRoster` có giờ vào/ra, 8h, mã ca (ghi chú "Hỗ trợ store …" giữ nguyên).
2. File 2: API `/file2` và `output/attendance.py` (nguồn file, tham số `away`) ghi ngày đi hỗ trợ = 1180 · 07:00 · 15:00.
3. Web Roster tuần: ô "HT …" hiện giờ + mã; tổng giờ / số ngày làm của nhân viên tính cả ngày đi hỗ trợ (SM Hồng Phú 2184 = 48h / 6 ngày).
   Giờ công và TCPH của store gốc **không** cộng 8h này (làm ở store khác).
4. Chạy lại 2184 (run 9); +1 test (File 2 ngày đi hỗ trợ) → 79 unit + 3 integration pass; ruff sạch trên file đã sửa.
5. README: viết lại phần đầu (trạng thái, hướng dẫn chạy, cấu trúc, bảng DB, quy tắc đã chốt) theo platform hiện tại.

### 19-Nov-2026 (2) — Đăng nhập + sửa dữ liệu đầu vào trên platform

[DECISION 19-Nov-2026, Thanh] Tận dụng đăng nhập / phân quyền của app .NET; các chức năng còn lại chuyển sang platform. Đợt này: login + sửa input.
1. `db/sql/0004_sched_auth_edit_views.sql` (Alembic 0004): `vw_auth_user`, `vw_auth_user_permission`, `vw_auth_user_store`; `vw_store_list`
   chỉ đếm nhân viên Active; `vw_input_*` thêm người / lúc cập nhật.
2. `sched_api/auth.py`: kiểm tra mật khẩu theo định dạng ASP.NET Core Identity (v3 PBKDF2 + v2, đã thử bằng test vector chuẩn); cookie
   `sched_session` ký HMAC (`SCHED_SESSION_SECRET`, 10 giờ, tự gia hạn); quyền + store đọc lại từ DB mỗi 30 giây (khóa user bên .NET là
   bị đẩy ra ngay); sai mật khẩu 5 lần / 5 phút thì chặn. Mọi API cần đăng nhập và lọc theo store của user; `requestedBy` của run = email.
3. `sched_api/input_edit.py` (sửa từng dòng) + `excel_io.py` (Tải Excel / Upload Excel có xem trước): nhân viên, lịch bận (sửa ô, chép tuần),
   cho mượn (chặn trùng thời gian), cấu hình store + giờ mở/đóng. Upload có lỗi thì không ghi gì.
4. Web: trang Đăng nhập, menu / nút theo quyền, tên user + Đăng xuất; trang Dữ liệu đầu vào sửa được (4 tab, hộp thoại Upload Excel 2 bước).
5. Kiểm tra: tải Excel rồi upload lại (3 store) = 0 thay đổi; file gốc store 2184 = 0 thay đổi; mọi thao tác ghi chạy thử trong transaction rồi
   rollback (DB không đổi); Chrome headless với user Admin và Manager giả lập: 0 lỗi console. +9 test → 82 unit + 9 integration pass.

### 19-Nov-2026 (3) — Dọn repo trước khi commit + sửa các điểm chặn deploy

1. Bỏ file không phục vụ platform: mock data P0 (`data/mock/`, `inputs/mock.py`, lệnh `mock`), `data/real/*.csv` (đã có trên DB),
   file demo HTML 628 KB, `requirements.txt` (thiếu thư viện DB; cài bằng `pip install -e`), dependency `pyyaml` không dùng,
   `tsconfig.tsbuildinfo` (thêm `*.tsbuildinfo` vào `.gitignore`). CLI `check` / `schedule` chỉ còn đọc SQL như web.
2. `optimizer/greedy_v0.py` + package re-export `greedy/` → một module `optimizer/greedy.py`.
3. Deploy: back-test theo biến `SCHED_ALLOW_PAST_WEEKS` (mặc định `false`, máy dev đặt `true`) thay vì cố định trong `service.py`;
   nhãn "DEMO · back-test" và thông báo back-test trên web chỉ hiện khi `meta.backTest`; thêm `GET /api/v1/sched/health` (không cần đăng nhập,
   kiểm tra DB); `SCHED_API_DOCS=false` tắt `/docs`.
4. Sự cố: thư mục `auto_scheduling/data/` và `reports/` bị chuyển vào Thùng rác lúc 11:37 (ngoài thao tác dọn repo). Đã khôi phục
   `PLH_Shift_Code_Map.csv` (engine bắt buộc); Availability xlsx / forecast parquet / reports để lại Thùng rác (dữ liệu đã có trên DB).
   Test đọc parquet được skip.
5. Kiểm tra: 81 unit + 9 integration pass (1 skip), ruff sạch trên file đã sửa, typecheck / lint / build web; chạy lại 2189 ra kết quả như cũ.

### 19-Nov-2026 (4) — Mã ca chấm công chuyển vào DB (`dbo.dim_shift_code`)

[DECISION 19-Nov-2026, Thanh] Bỏ file `PLH_Shift_Code_Map.csv`, mã ca nằm trong bảng `dbo.dim_shift_code`.
1. Migration `0005_dim_shift_code` (`db/sql/0005_dim_shift_code.sql`): tạo bảng (ShiftCode PK, StartTime, EndTime, DurationHours,
   IsOvernight tính sẵn, SortOrder, IsActive, Note, Created/UpdatedAt, UpdatedBy) + nạp 210 mã của HR — **7 mã `11E1`..`11E7` ghi đúng**
   (file cũ bị Excel đổi thành 110…110000000). Chỉ tạo bảng khi chưa có, chỉ nạp khi bảng rỗng. View `sched.vw_engine_shift_code`, `vw_input_shift_code`.
2. Engine (`SqlSource`) đọc mã ca từ view; file source (debug) phải truyền đường dẫn CSV. API `GET /api/v1/sched/inputs/shift-codes`.
3. Kiểm tra: mã ca DB = file HR (sau sửa 7 mã, 210/210 cặp giờ); chạy lại 2184 ra kết quả như cũ; File 2 gán mã đúng. +2 test.
   Bảng nằm trong `dbo` nhưng do platform tạo — báo người làm .NET để migration EF không đụng vào.

## Tiếp theo
- Giang nạp forecast tuần 16/11 trở đi → bỏ back-test (`SCHED_DEFAULT_AVAILABILITY_WEEK` để trống).
- Thịnh review 3 roster trên web; chốt các phát hiện 13-Nov #2–3 (FT lấp hết band, ngưỡng coverage khi giữ band).
- HR: sửa 7 mã ca bị Excel làm hỏng trong file gốc; xác nhận mã 1180 cho ngày đi hỗ trợ.
- Store nhận hỗ trợ (2023) cần nhân viên + target trên DB để thử xếp lịch phía store nhận.
- KPI giờ giao ca: chuyển ô 60' → 30' (cách A) nếu cần chính xác hơn.
- Người làm app .NET ẩn / ngưng các màn hình sửa nhân viên, lịch bận, cho mượn, cấu hình (đã chuyển sang platform).
- Cấp `Action.Employee.Manage` cho role Manager nếu muốn quản lý store tự sửa nhân viên / cho mượn.
- Chuyển tiếp các màn hình còn lại của .NET (Dashboard, Zone planning, publish, quản lý store / AM-OM) — cần liệt kê trước.
- Deploy (HTTPS: đặt `SCHED_COOKIE_SECURE=true`); bản demo offline 1 file HTML (blueprint §9) nếu cần.
- P6: CP-SAT (ortools) so sánh với greedy v0.
