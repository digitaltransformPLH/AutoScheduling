# Workforce Planning — Publish Daily Metrics API

ASP.NET Core API + **React admin SPA** (login, users, roles, stores, AM→OM). Auth is **cookie session** with **email/password** and full **RBAC**. Weekly planning vẫn là HTML legacy tại `/planning/` (ngoài scope refactor).

## Repository layout

```text
apps/
  api/          ASP.NET Core host + wwwroot
  web/          Vite + React (admin SPA)
packages/
  WorkforcePlanning.Domain/
  WorkforcePlanning.Application/
  WorkforcePlanning.Infrastructure/
database/       SQL scripts & migrations helpers
```

## Architecture

```
Browser (React at /, build from apps/web/)
  → POST /api/v1/auth/login  (cookie)
  → GET  /api/v1/me
  → Admin APIs: users, roles, stores, am-om-assignments
  → SQL Server

/planning/ → legacy HTML (optional)
```

## Projects

| Path | Role |
|---|---|
| `apps/web/` | Vite + React + TypeScript (`features/`, `shared/`) → `apps/api/wwwroot` |
| `apps/api/` | Controllers, cookie auth, static files |
| `packages/WorkforcePlanning.Application` | DTOs, FluentValidation |
| `packages/WorkforcePlanning.Domain` | Entities / permission codes |
| `packages/WorkforcePlanning.Infrastructure` | EF Core, services |

## Auth & permissions

Configured in `Auth` section:

```json
"Auth": {
  "AdminEmail": "admin@phuclong.com",
  "AdminPassword": "Admin@123",
  "AdminDisplayName": "Administrator",
  "SessionHours": 10
}
```

On startup the app migrates DB and seeds admin (role **Administrator**, `AllStores = true`) if missing.

| Permission | Meaning |
|---|---|
| `Action.Published.View` | View published daily metrics / dashboard |
| `Action.Publish.Schedule` | Publish schedule |
| `Action.User.Manage` | User CRUD |
| `Action.Role.Manage` | Role / permission management |
| `Action.Store.View` | List stores for assignment |

System roles: Administrator, Manager, Staff, Viewer.

## API

| Method | Path | Access |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Anonymous |
| `POST` | `/api/v1/auth/logout` | Authenticated |
| `GET` | `/api/v1/me` | Authenticated |
| `POST` | `/api/v1/publish` | `Action.Publish.Schedule` + store access |
| `GET` | `/api/v1/stores/{storeCode}/daily?weekStart=` | `Action.Published.View` + store access |
| `GET/POST/PUT/DELETE` | `/api/v1/users` | `Action.User.Manage` |
| `GET/POST/PUT/DELETE` | `/api/v1/roles` | `Action.Role.Manage` |
| `PUT` | `/api/v1/roles/{id}/permissions` | `Action.Role.Manage` |
| `POST` | `/api/v1/roles/{id}/clone` | `Action.Role.Manage` |
| `GET` | `/api/v1/permissions` | Role/User manage |
| `GET` | `/api/v1/stores` | Store.View or User.Manage |
| `GET` | `/api/v1/sched/*` | `Action.Planning.Overview.View` or `Analysis.View` + store scope (đọc `sched.vw_*`) |
| `POST` | `/api/v1/sched/runs` | `Action.Publish.Schedule` + store scope (engine Python) |

## Local development

1. Copy `apps/api/appsettings.Development.json.example` → `apps/api/appsettings.Development.json` and set SQL + Auth passwords (file is gitignored).
2. **React admin UI** (login, users, roles) + **legacy planning** at `/planning/`:

**Option A — integrated (giống production)**

```powershell
cd apps/web
npm install
npm run build
cd ../..
dotnet run --project apps/api
```

Mở `http://localhost:5224` (React). Planning: `http://localhost:5224/planning/`.

**Option B — hot reload React**

```powershell
# Terminal 1
dotnet run --project apps/api

# Terminal 2
cd apps/web
npm install
npm run dev
```

Mở Vite (thường `http://localhost:5173`); API proxy `/api` → API port.

3. Login với admin seed. Quản trị: `/users`, `/roles`, `/stores`, `/am-om`. **Auto scheduling UI** (trong admin SPA): `/scheduling`, `/scheduling/roster`, `/scheduling/runs` — API đọc lịch tại `/api/v1/sched/*` (schema `sched` trên SQL Server). Nút **Tạo lịch** cần Python + package `auto_scheduling` (`Scheduling:PythonExecutable` trong `appsettings`). Weekly planning (legacy): `/planning/`.

### Cấu trúc React (`apps/web/src`)

- `app/` — router, QueryClient  
- `features/auth|users|roles|stores|am-om|home` — màn hình + API  
- `shared/api`, `shared/layouts` — HTTP client, types, AdminLayout

4. EF migrations (from repo root):

```powershell
dotnet ef database update --project packages/WorkforcePlanning.Infrastructure --startup-project apps/api
```

5. Optional schema script: [`database/005_CookieAuthRbac.sql`](database/005_CookieAuthRbac.sql) (prefer `dotnet ef database update` / app startup migrate).

`scripts/local-publish.ps1` chạy `npm run build` trước `dotnet publish`.

## IIS on-prem deploy

1. Install [.NET Hosting Bundle](https://dotnet.microsoft.com/download/dotnet) matching TFM.
2. Publish:

```bash
dotnet publish apps/api -c Release -o C:\inetpub\WorkforcePlanning
```

3. IIS:
   - App Pool: **No Managed Code**, Integrated
   - **Anonymous Authentication**: Enabled
   - **Windows Authentication**: Disabled
4. Set production connection string and `Auth__AdminPassword` via environment variables.

## Deploy scripts

Auto-deploy via share folder (keeps `appsettings.json` and `web.config` on the server).

**Defaults:** local share `C:\Users\tienlta\OneDrive - WIN\Project\weekly_workforce_planning\Deploy`, server share `D:\Source publish\WorkforcePlanning_Tmp`, deploy `D:\WorkforcePlanning\WorkforcePublish`, App Pool `WorkforcePlanningPool`.

1. On the build machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-publish.ps1
```

2. On the server (after the zip is on the share):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\server-deploy.ps1
```

Server script needs IIS/Admin rights to stop/start the App Pool. Override paths with `-ShareDir`, `-DeployPath`, `-AppPoolName` if needed.

## UAT checklist

- [ ] Login with admin email/password
- [ ] `GET /api/v1/me` returns role + permissions + stores
- [ ] Create user, assign role + stores
- [ ] Clone role / edit permissions
- [ ] Publish schedule for an allowed store
- [ ] User without store access receives 403 on publish/daily
- [ ] Logout clears session
