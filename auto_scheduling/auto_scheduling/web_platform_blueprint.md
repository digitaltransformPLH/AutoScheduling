# Blueprint: web-based data platform (SQL Server → Python ETL → FastAPI → React)

Rút từ platform Cluster Strategy (repo `tradezone-cluster`, 11/2026), **bỏ phần map** (deck.gl / MapLibre / H3).
Dùng làm khung cho repo mới: copy file này vào repo đó, đổi `<app>` (tên package), `<sch>` (schema SQL) và nghiệp vụ.

Phù hợp khi:
- dữ liệu nội bộ nằm ở SQL Server / Databricks / Excel;
- cần dashboard nhiều trang, có filter, chart, bảng và vài form nhập tay;
- đội nhỏ, máy dev Windows, chưa có docker.

---

## 1. Stack & phiên bản đã chạy ổn

| Lớp | Công nghệ | Phiên bản | Ghi chú |
|---|---|---|---|
| DB | SQL Server 2022 | — | 1 schema riêng cho app. API chỉ gọi `usp_*` / `vw_*` |
| Migration | Alembic + file DDL `.sql` đóng băng | alembic 1.14+ (đang chạy 1.20) | Alembic chỉ đọc và chạy file `.sql` (tách batch theo `GO`) |
| Python | 3.12+ (dev: 3.13) | — | `.venv` + `pip install -e`; uv workspace nếu máy có uv |
| DB driver | SQLAlchemy 2 + pyodbc + ODBC Driver 18 | 2.0.36+ / 5.2+ | `fast_executemany=True` cho bulk insert |
| Settings | pydantic-settings | 2.6+ | prefix env `<APP>_`, đọc `.env` ở root |
| ETL | pandas + CLI argparse/typer | pandas 2.2+ | lệnh `<app>-etl <nhóm> <lệnh>` |
| API | FastAPI + uvicorn | 0.115+ / 0.32+ | endpoint `def` (pyodbc sync), GZip middleware |
| Lint / test | ruff, pytest | ruff 0.8+, pytest 8.3+ | line-length 120 |
| Web build | Vite + React + TypeScript | vite 6.4 · react 18.3 · TS 5.9 | |
| UI kit | Ant Design 5 + @ant-design/icons | antd 5.29 | theme qua `ConfigProvider` token |
| Data fetching | TanStack Query 5 | 5.107 | `queryKey` chứa `data_version` |
| Routing | react-router-dom 6 (data router) | 6.30 | `createBrowserRouter` (cần cho `useBlocker`) |
| Chart | ECharts 5 + echarts-for-react | 5.6 / 3.0 | |
| API types | openapi-typescript | 7.13 | sinh `schema.d.ts` từ `app.openapi()` |
| Lint web | oxlint | 1.9x | rules-of-hooks = error |
| Cache (sau) | Redis | — | giữ interface cache, bật khi deploy |

Không dùng thêm state manager (Redux / Zustand): state server nằm trong TanStack Query, state filter nằm trên URL.

---

## 2. Kiến trúc

```
Nguồn (SQL Server nguồn, Databricks, Excel / CSV ở data/raw — không commit)
   │  ETL Python (pandas): đọc → làm sạch → tính → validate (DQ report)
   ▼
SQL Server, schema <sch>
   ├─ bảng fact / dim / agg (ETL ghi đè theo component)
   ├─ <sch>.meta_build (component, data_version, built_at, row_counts, source_files)
   ├─ <sch>.usp_* (stored procedure: filter, aggregate)  ← API chỉ gọi lớp này
   └─ <sch>.vw_*  (view)
   ▼
FastAPI /api/v1/<sch>/…  → JSON {data, meta}  (meta.data_version)
   ▼
React (Vite): hooks TanStack Query → trang AntD + ECharts
```

Nguyên tắc:
1. **Mọi tính toán nặng ở ETL** (join, phân loại, mô hình). API chỉ lọc và trả; UI chỉ hiển thị.
2. **API không viết SQL ad-hoc**: mỗi endpoint = 1 `EXEC <sch>.usp_x` hoặc `SELECT … FROM <sch>.vw_x`. Đổi logic = migration mới.
3. **Ngưỡng, mapping, màu nhóm** đặt ở `config/*.yaml`, không hard-code trong UI. API đọc yaml (có cache theo mtime).
4. **Không bịa số liệu**: thiếu data thì trả `null`, UI hiện "Pending" kèm lý do, không để 0.
5. **`data_version`** tăng mỗi lần ETL nạp. UI poll `/meta` và đưa version vào mọi `queryKey`, nên ETL chạy xong là UI tự làm mới.

---

## 3. Cấu trúc repo

```
<repo>/
├─ CLAUDE.md                     # quy tắc + lệnh (template ở §11)
├─ pyproject.toml                # workspace, ruff, pytest
├─ .env                          # KHÔNG commit (conn string, token)
├─ config/                       # *.yaml: ngưỡng, mapping, màu
├─ data/raw/                     # input thô — KHÔNG commit
├─ data/out/                     # output ETL / DQ report — KHÔNG commit
├─ db/
│  ├─ alembic.ini
│  ├─ migrations/env.py
│  ├─ migrations/versions/000N_<tên>.py   # chỉ đọc và chạy db/sql/000N_*.sql
│  └─ sql/000N_<tên>.sql                  # DDL đóng băng (bảng, view, SP), batch tách bằng GO
├─ packages/core/src/<app>_core/          # settings, db engine, schema SQLAlchemy Table (cho bulk insert)
├─ services/etl/src/<app>_etl/
│  ├─ cli.py                     # <app>-etl db upgrade | <nhóm> <lệnh> [--sink files]
│  ├─ sources/                   # reader nguồn (sql_source.py, databricks.py, excel.py)
│  └─ <domain>/                  # mỗi bước 1 module: build() thuần (DataFrame in → out) + load.py
├─ services/api/src/<app>_api/
│  ├─ main.py                    # FastAPI app, include routers, GZip
│  ├─ deps.py                    # get_conn, csv_list
│  ├─ core/                      # config() cache yaml + logic thuần (không I/O)
│  ├─ routers/<sch>_*.py
│  └─ schemas/<sch>*.py          # Pydantic response model (sinh ra OpenAPI → TS types)
├─ services/web/                 # Vite + React
│  ├─ src/api/{client.ts,hooks.ts,schema.d.ts}
│  ├─ src/{pages,components,lib,theme}/
│  ├─ public/                    # logo, icon
│  └─ scripts/                   # dump_demo.py, inline-demo.mjs (bản offline, §9)
└─ tests/unit/                   # pytest cho logic thuần ETL / core
```

`.gitignore` tối thiểu:

```gitignore
.venv/
__pycache__/
.env
data/*
!data/README.md
*.xlsx
*.csv
*.parquet
node_modules/
services/web/dist/
services/web/dist-demo/
# openapi.json sinh từ FastAPI (KHÔNG viết comment cuối dòng: gitignore sẽ coi cả dòng là pattern)
services/web/openapi.json
```

---

## 4. Khởi tạo (Windows, không uv, không docker)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\python -m pip install -e packages/core -e services/etl -e services/api alembic pytest ruff
# web
npm create vite@latest services/web -- --template react-ts
cd services/web
npm i antd @ant-design/icons @tanstack/react-query react-router-dom echarts echarts-for-react
npm i -D openapi-typescript oxlint
```

PowerShell 5.1 không có `&&`: dùng `;` hoặc `cmd; if ($?) { cmd2 }`.

---

## 5. Backend: các pattern đã kiểm chứng

### 5.1 Settings + engine

```python
# packages/core/src/<app>_core/settings.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="<APP>_", env_file=REPO_ROOT / ".env", extra="ignore")
    sql_conn: str = ("mssql+pyodbc://@localhost\\SQLEXPRESS/<db>"
                     "?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes")
    config_dir: Path = REPO_ROOT / "config"
    data_dir: Path = REPO_ROOT / "data"
    databricks_host: str | None = None      # nguồn phụ: để None → bước ETL đó báo thiếu, không crash

@lru_cache
def get_settings() -> Settings: return Settings()

# db.py
@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().sql_conn, fast_executemany=True, pool_pre_ping=True)
```

### 5.2 Migration = file SQL đóng băng

```python
# db/migrations/versions/0005_<sch>_x.py
SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
def upgrade() -> None:
    for batch in (SQL_DIR / "0005_<sch>_x.sql").read_text(encoding="utf-8").split("\nGO"):
        if batch.strip():
            op.execute(batch)
def downgrade() -> None:
    op.execute("DROP PROCEDURE IF EXISTS <sch>.usp_x")  # liệt kê ngược thứ tự tạo
```

- `env.py`: `version_table_schema="etl"`, tạo schema trước (`IF SCHEMA_ID('etl') IS NULL EXEC('CREATE SCHEMA etl')`).
- Sửa SP = migration mới với `CREATE OR ALTER PROCEDURE`, **không sửa file `.sql` cũ** đã chạy.
- Tham số list truyền dạng CSV: `WHERE (@codes IS NULL OR code IN (SELECT LTRIM(RTRIM(value)) FROM STRING_SPLIT(@codes, ',')))`.
- Tìm kiếm không dấu: `COLLATE Latin1_General_CI_AI LIKE @like COLLATE Latin1_General_CI_AI`.
- Ghép số thực thành chuỗi: `CAST(x AS DECIMAL(12,7))` trước `CONCAT` (nếu không, float bị cắt còn 6 chữ số).
- Input JSON từ form: `OPENJSON(@payload) WITH (col NVARCHAR(20), …)` **cắt ngầm** chuỗi dài, nên giới hạn `max_length` ở Pydantic bằng đúng độ dài cột.

### 5.3 ETL: hàm thuần + load ghi đè + meta_build

```python
# <domain>/build.py — thuần, test được không cần DB
def build(src: pd.DataFrame, cfg: dict) -> Result: ...

# load.py
def records(df):  # pyodbc không nhận NaN/NaT
    return df.astype(object).where(pd.notna(df), None).to_dict("records")

def next_version(conn):
    return int(conn.execute(text("SELECT ISNULL(MAX(data_version),0)+1 FROM <sch>.meta_build")).scalar())

def replace(conn, table, df, build_id, chunk=2000):
    cols = [c.name for c in table.columns if c.name in df.columns or c.name == "build_id"]
    rows = records(df.assign(build_id=build_id)[cols])
    conn.execute(text(f"TRUNCATE TABLE {table.schema}.{table.name}"))   # tên bảng từ metadata, không từ input
    for i in range(0, len(rows), chunk):
        conn.execute(insert(table), rows[i:i + chunk])

def load_x(conn, res, sources):
    v = next_version(conn)
    build_id = write_meta(conn, "x", v, sources, {"rows": len(res.df)})   # ghi meta_build
    replace(conn, s.<sch>_x, res.df, build_id)
```

- CLI: `<app>-etl <nhóm> <lệnh> [--sink db|files] [--force]`; mỗi lệnh in số dòng và ghi DQ report `data/out/<nhóm>/dq_report.md`.
- Chạy trong `engine.begin()` (1 transaction / lệnh), lỗi giữa chừng thì không mất dữ liệu cũ.
- Đọc Excel: chỉ định `sheet_name`, `header=`; hyperlink trong ô đọc bằng openpyxl `cell.hyperlink.target`. CSV nội bộ hay gặp `;` + cp1252 + số lẫn `,` / `.`.
- **Không ghi vào file nguồn** (Excel OneDrive của team): đề xuất sửa trong một workbook review riêng.

### 5.4 API

```python
# deps.py
def get_conn() -> Iterator[Connection]:
    with get_engine().connect() as conn:
        yield conn
def csv_list(v: str | None) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()] if v else []

# core/__init__.py — yaml cache theo mtime (uvicorn --reload chỉ theo dõi .py)
_CACHE: dict[str, tuple[float, Any]] = {}
def config(name: str) -> dict:
    path = get_settings().config_dir / f"{name}.yaml"
    m = path.stat().st_mtime
    hit = _CACHE.get(name)
    if hit is None or hit[0] != m:
        hit = (m, yaml.safe_load(path.read_text(encoding="utf-8"))); _CACHE[name] = hit
    return hit[1]

# routers/<sch>_x.py
router = APIRouter(prefix="/<sch>", tags=["<sch>"])

@router.get("/x", response_model=XResponse)
def get_x(region: str | None = Query(None), items: str | None = Query(None, description="CSV"),
          conn: Connection = Depends(get_conn)) -> dict:      # def, không async (pyodbc sync)
    rows = conn.execute(text("EXEC <sch>.usp_x @region = :r, @items = :i"),
                        {"r": region, "i": ",".join(csv_list(items)) or None}).mappings()
    return {"data": [dict(r) for r in rows], "meta": _meta(conn)}
```

- Response luôn có dạng `{data, meta}`; `meta` = `{data_version, built_at, components{…}, source}` lấy từ `<sch>.vw_meta`.
- Endpoint ghi (PUT): payload JSON đưa vào 1 SP `usp_x_upsert @payload, @user` (SP ghi kèm log), rồi `conn.commit()`.
  Pydantic `Field(max_length=…)` cho mọi chuỗi và cả list.
- Query param số nguyên có tập giá trị cố định: khai báo `int` rồi tự kiểm tra (`Literal[4, 2]` trong query bị lỗi).
- Logic thuần (health band, rule engine) đặt ở `core/`, đọc ngưỡng từ yaml, có unit test.
- Auth: lúc đầu dùng header `X-User` (localStorage); trước khi lên server phải thay bằng SSO / JWT.

---

## 6. Frontend: các pattern đã kiểm chứng

### 6.1 `vite.config.ts`

```ts
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'demo' ? './' : '/',
  server: { port: 5173, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: { output: { manualChunks: { antd: ['antd', '@ant-design/icons'], charts: ['echarts', 'echarts-for-react'] } } },
  },
}))
```

### 6.2 API client: type sinh từ OpenAPI, không viết tay

```ts
// src/api/client.ts
import type { components } from './schema'          // npm run gen:api
export type Schemas = components['schemas']
export type XResponse = Schemas['XResponse']
export const API_BASE = '/api/v1/<sch>'
export class ApiError extends Error { constructor(public status: number, msg: string) { super(msg) } }
export type Params = Record<string, string | number | boolean | null | undefined>
export const qs = (p: Params = {}) => {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== null && v !== '' && v !== false) sp.set(k, String(v))
  const s = sp.toString(); return s ? `?${s}` : ''
}
export async function getJson<T>(path: string, params?: Params): Promise<T> {
  const res = await fetch(`${API_BASE}${path}${qs(params)}`, { headers: { Accept: 'application/json' } })
  if (!res.ok) {
    let msg = res.statusText
    try { const b = await res.json(); msg = b.error?.message ?? (typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail ?? msg)) } catch { /* not JSON */ }
    throw new ApiError(res.status, msg)
  }
  return res.json() as Promise<T>
}
```

Sinh type:

```powershell
.venv\Scripts\python -c "import json; from <app>_api.main import app; json.dump(app.openapi(), open('services/web/openapi.json','w'))"
cd services/web; npm run gen:api   # "gen:api": "openapi-typescript openapi.json -o src/api/schema.d.ts"
```

### 6.3 Hooks: `data_version` trong `queryKey`

```ts
export function useMeta() {
  return useQuery({ queryKey: ['<sch>', 'meta'], queryFn: () => getJson<MetaResponse>('/meta'),
                    staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, select: (r) => r.data })
}
const useDataVersion = () => useMeta().data?.data_version ?? 0

export function useX(region: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['<sch>', 'x', { region }, v],
    queryFn: () => getJson<XResponse>('/x', { region }),
    select: (r) => r.data,
    placeholderData: keepPreviousData,     // đổi filter không bị nháy trắng
  })
}
export function useSaveX() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (rows: XInput[]) => sendJson('/x', { rows }),
                       onSuccess: () => qc.invalidateQueries({ queryKey: ['<sch>', 'x'] }) })
}
```

`QueryClient` mặc định: `staleTime: 10 phút, retry: 1, refetchOnWindowFocus: false`.

### 6.4 State filter trên URL

Hook `useUrlFilters()` dùng `useSearchParams`: parse query thành object có default, setter ghi ngược lên URL
(`replace: true` cho thay đổi nhỏ). Nhờ vậy share link giữ nguyên view và nút Back hoạt động. Đổi filter cha thì xoá filter con.

### 6.5 Router + chặn rời trang khi form chưa lưu

```tsx
const router = createBrowserRouter([{ path: '*', element: <App /> }], { future: { v7_relativeSplatPath: true } })
// trong App: <Routes> các trang; trong form: useBlocker(dirty) + Modal.confirm
root.render(
  <QueryClientProvider client={queryClient}>
    <ConfigProvider theme={antdTheme} locale={viVN}>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </ConfigProvider>
  </QueryClientProvider>)
```

### 6.6 Theme: một file token làm nguồn sự thật

`src/theme/tokens.ts`: bảng màu brand (`plh.green`, `plh.dkgreen`, `plh.cream`, `plh.lime`, `plh.rust`…), màu ngữ nghĩa
(status chip), `fontFamily`, và `antdTheme: ThemeConfig` (token + components: Layout, Table header tối, Segmented, Tag).
ECharts dùng cùng `fontFamily` và màu này. Không viết mã màu rời trong component.

### 6.7 Component hay dùng lại

- **KPI tiles**: `Card` nhỏ gồm label, số lớn, phụ chú; thiếu data thì hiện `Tag` "Pending".
- **LineCard**: ECharts line This year vs Last year, badge YoY.
- **Stack 100% bar**: ECharts bar `stack`, nhãn %; dùng cho channel mix, daypart mix.
- **Bảng có hàng mở rộng**: AntD `Table` `expandable` để mở chi tiết, deep link bằng query `?row=…`.
- **Form bảng nhập tay**: state cục bộ + `useBlocker` + nút Lưu (mutation) + `message.error` khi lỗi.
- **Header search**: `AutoComplete` + `useQuery` debounce, chọn kết quả thì `navigate(url)`.

---

## 7. Quy ước code

- Python: ruff (`E,F,I,UP,B,SIM`, ignore `B008` cho FastAPI `Depends`), line 120. **Chỉ chạy `ruff format` trên file mình sửa**,
  không format cả repo (dễ làm bẩn diff file khác).
- TS: `strict`, `noUnusedLocals`, `verbatimModuleSyntax`; oxlint `react/rules-of-hooks: error`.
- Comment và docstring ngắn, giải thích *vì sao*; tên biến và cột tiếng Anh, nội dung UI theo đối tượng dùng.
- Mỗi phase kết thúc bằng các bước kiểm tra ở §10.

---

## 8. Kiểm thử

- `tests/unit/`: test hàm `build()` thuần của ETL với DataFrame nhỏ dựng tay, test logic `core/`.
- Marker `integration` cho test cần SQL Server thật (`addopts = "-m 'not integration'"`).
- Smoke test API in-process: `fastapi.testclient.TestClient(app).get("/api/v1/<sch>/meta")`, không cần chạy server.
- UI: kiểm tra bằng Chrome headless qua CDP (Node 24 có sẵn `WebSocket`): mở trang, bắt `Runtime.exceptionThrown` / console error, chụp ảnh.

---

## 9. Bản demo offline: 1 file HTML gửi user (không cần API / VPN)

Dùng khi chưa deploy mà cần cho user xem. Cách làm:

1. **Dump snapshot** (`scripts/dump_demo.py`): `TestClient(app)` gọi mọi endpoint với các tổ hợp tham số hữu hạn và lưu
   `{key: {s: status, b: body}}`, với key = path + query đã sort. Asset `/public` đổi thành data URI. Kết quả: gzip, rồi base64.
2. **Chế độ demo trong client**: `isDemo = import.meta.env.MODE === 'demo'`. Khi đó `getJson` tra snapshot (filter tự do thì lọc
   ngay trên trình duyệt từ dữ liệu thô), `sendJson` báo "chỉ xem". Dữ liệu đọc từ `<script id="demo-data">` bằng
   `DecompressionStream('gzip')`, và chỉ `render()` sau khi nạp xong.
3. **Router**: `createHashRouter` khi demo (file:// không có server trả index.html).
4. **Build**: `vite build --mode demo` với `base: './'`, `assetsInlineLimit` lớn, `cssCodeSplit: false`,
   `rollupOptions.output.inlineDynamicImports: true`. Sau đó chạy script Node gộp JS / CSS / data vào 1 HTML
   (module script rời không nạp được qua file://).
5. Gắn tag "DEMO · ngày snapshot" trên header. Dữ liệu là số thật, nên cân nhắc trước khi gửi.

Bẫy khi gộp: dùng **replacement dạng function** `html.replace('</body>', () => …)` vì bundle chứa `$&` / `$'`;
escape `</script` trong JS.

---

## 10. Kiểm tra trước khi xong một phase / trước commit

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check .
cd services/web; npm run typecheck; if ($?) { npm run build }
```

Commit: không commit `data/`, `.env`, `dist*`, `openapi.json`, file Excel. Làm việc trên branch `feature/*`.

---

## 11. Bẫy đã gặp (đỡ mất nửa ngày)

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Bundle có 2 bản React, lỗi "No QueryClient set" / dispatcher null | Build từ Git Bash: cwd `d:` thường, path module lẫn `D:` / `d:` | Chạy `vite build` từ PowerShell / cmd |
| `&&` lỗi trong PowerShell 5.1 | Không hỗ trợ pipeline chain | `;` hoặc `if ($?) { … }` |
| pyodbc lỗi khi insert NaN | Driver không hiểu NaN / NaT | `df.astype(object).where(pd.notna(df), None)` |
| Toạ độ / số thập phân bị cắt khi `CONCAT` | float → chuỗi 6 chữ số | `CAST(x AS DECIMAL(12,7))` |
| Text nhập form bị cắt mất | `OPENJSON … WITH (NVARCHAR(n))` cắt ngầm | Pydantic `max_length = n` → 422 |
| FastAPI query `Literal[4, 2]` lỗi | Query luôn là string | `int` + tự kiểm tra |
| Sửa yaml mà API không đổi | `--reload` chỉ theo dõi `.py` | Cache yaml theo mtime (§5.4) |
| `print` tiếng Việt crash trên console Windows | stdout cp1252 | `sys.stdout.reconfigure(encoding="utf-8")` |
| Heredoc bash vỡ khi có `'` `"` lồng nhau | Quoting | Viết file script tạm rồi chạy |
| `ruff format .` làm bẩn file không liên quan | Format toàn repo | Chỉ format file đã sửa |
| `.gitignore` có `path   # comment` không ăn | Gitignore không có comment cuối dòng | Comment ở dòng riêng |
| CRLF / LF cảnh báo khi commit | Windows | `.gitattributes` `* text=auto eol=lf` |
| Google Fonts / CDN bị proxy công ty chặn | Mạng nội bộ | Khai báo font fallback; self-host font trong `public/fonts` |

---

## 12. Template `CLAUDE.md` cho repo mới

```markdown
# <Tên platform> — <công ty / team>

Monorepo Python + SQL Server + React: `packages/core` (settings, DB, schema), `services/etl` (`<app>-etl`),
`services/api` (FastAPI `/api/v1/<sch>`), `services/web` (Vite + React + TS + AntD + TanStack Query + ECharts).
User: <tên, vai trò>. Trả lời bằng tiếng Việt, giữ thuật ngữ kỹ thuật tiếng Anh.

## Rules
- Không bịa số liệu / tên. Thiếu data → UI hiện "Pending" kèm lý do, không để trống / 0.
- API chỉ gọi `<sch>.usp_*` / `<sch>.vw_*`, không SQL ad-hoc trong router. Endpoint `def` (pyodbc sync).
- Migration: Alembic `db/migrations/versions/000N_*.py` chạy DDL đóng băng `db/sql/000N_*.sql`; sửa SP = migration mới.
- Tính toán ở ETL; ngưỡng / mapping ở `config/*.yaml`, không hard-code trong UI.
- Type web sinh từ OpenAPI (`npm run gen:api`), không viết tay.
- Không commit data/, .env, dist*, file Excel. Không sửa file nguồn của team (OneDrive) — đề xuất qua workbook review.
- Mỗi phase kết thúc: `pytest -q`, `ruff check .`, `npm run typecheck && npm run build` (build từ PowerShell).

## Commands
- Python: `.venv/Scripts/python` (3.13)
- DB: `python -m <app>_etl.cli db upgrade`
- ETL: `python -m <app>_etl.cli <nhóm> <lệnh> [--sink files]`
- API: `python -m uvicorn <app>_api.main:app --reload` → http://127.0.0.1:8000/docs
- Web: `cd services/web; npm run dev` (port 5173, proxy /api → 8000)
- Types: dump `openapi.json` rồi `npm run gen:api`
- Demo offline: `python services/web/scripts/dump_demo.py` rồi `npm run build:demo`
- Test: `python -m pytest -q; ruff check .`
```

---

## 13. Thứ tự build gợi ý cho repo mới

1. **P0 Khung**: repo, `.venv`, settings, engine, Alembic + schema `<sch>` + `meta_build` / `vw_meta`; FastAPI `/meta`; Vite app
   có header, theme, router, `useMeta`. Kiểm tra: `/meta` hiện trên UI.
2. **P1 Dữ liệu lõi**: reader nguồn, `build()` + DQ report, load + `data_version`, unit test.
3. **P2 Trang tổng quan**: SP aggregate, endpoint, `gen:api`, trang KPI tiles + bảng + chart.
4. **P3+ Trang chi tiết**: filter trên URL, drill-down, form nhập tay (PUT + log + `useBlocker`).
5. **Trước deploy**: auth thật, Redis cache, Nginx proxy `/api`, self-host font; demo offline nếu cần cho user xem sớm.
