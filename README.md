# Workforce Planning — Publish Daily Metrics API

ASP.NET Core API + SPA for workforce planning. Auth is **cookie session** with **email/password** and full **RBAC** (Role + Permission). Store assignment is data scope only.

## Architecture

```
Browser (wwwroot/index.html)
  → POST /api/v1/auth/login  (cookie)
  → GET  /api/v1/me
  → POST /api/v1/publish | Users/Roles admin APIs
  → SQL Server
```

## Projects

| Project | Role |
|---|---|
| `WorkforcePlanning.Api` | Controllers, cookie auth, static HTML |
| `WorkforcePlanning.Application` | DTOs, FluentValidation |
| `WorkforcePlanning.Domain` | Entities / permission codes |
| `WorkforcePlanning.Infrastructure` | EF Core, services |

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

## Local development

1. Copy `src/WorkforcePlanning.Api/appsettings.Development.json.example` → `appsettings.Development.json` and set SQL + Auth passwords (file is gitignored).
2. Run:

```bash
dotnet run --project src/WorkforcePlanning.Api
```

3. Open the site URL (not `file://`). Login with seeded admin.
4. Optional schema script: [`database/005_CookieAuthRbac.sql`](database/005_CookieAuthRbac.sql) (prefer `dotnet ef database update` / app startup migrate).

## IIS on-prem deploy

1. Install [.NET Hosting Bundle](https://dotnet.microsoft.com/download/dotnet) matching TFM.
2. Publish:

```bash
dotnet publish src/WorkforcePlanning.Api -c Release -o C:\inetpub\WorkforcePlanning
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
