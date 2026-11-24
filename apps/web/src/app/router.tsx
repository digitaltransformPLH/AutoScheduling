import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getPathBase } from '../shared/api/pathBase'
import { PermissionCodes } from '../shared/api/types'
import { AdminLayout } from '../shared/layouts/AdminLayout'
import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { RequireAnyPermission, RequirePermission } from '../features/auth/RequirePermission'
import { HomePage } from '../features/home/HomePage'
import { UsersPage } from '../features/users/UsersPage'
import { RolesPage } from '../features/roles/RolesPage'
import { StoresPage } from '../features/stores/StoresPage'
import { AmOmPage } from '../features/am-om/AmOmPage'
import { EmployeesPage } from '../features/employees/EmployeesPage'
import { EmployeeAvailabilityPage } from '../features/employee-availability/EmployeeAvailabilityPage'
import { StoreConfigPage } from '../features/store-config/StoreConfigPage'
import { SchedulingShell } from '../features/scheduling/SchedulingShell'
import { OverviewPage } from '../features/scheduling/pages/OverviewPage'
import { RosterPage } from '../features/scheduling/pages/RosterPage'
import { RunsPage } from '../features/scheduling/pages/RunsPage'

const schedViewPerms = [PermissionCodes.PlanningOverviewView, PermissionCodes.PlanningAnalysisView]
const basename = getPathBase() || undefined

export function AppRouter() {
  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AdminLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/home" element={<HomePage />} />
            <Route
              path="/users"
              element={
                <RequirePermission permission={PermissionCodes.UserManage}>
                  <UsersPage />
                </RequirePermission>
              }
            />
            <Route
              path="/roles"
              element={
                <RequirePermission permission={PermissionCodes.RoleManage}>
                  <RolesPage />
                </RequirePermission>
              }
            />
            <Route
              path="/stores"
              element={
                <RequirePermission permission={PermissionCodes.StoreManage}>
                  <StoresPage />
                </RequirePermission>
              }
            />
            <Route
              path="/employees"
              element={
                <RequireAnyPermission
                  permissions={[PermissionCodes.EmployeeView, PermissionCodes.EmployeeManage]}
                >
                  <EmployeesPage />
                </RequireAnyPermission>
              }
            />
            <Route
              path="/am-om"
              element={
                <RequirePermission permission={PermissionCodes.AmOmManage}>
                  <AmOmPage />
                </RequirePermission>
              }
            />
            <Route
              path="/employee-availability"
              element={
                <RequireAnyPermission
                  permissions={[
                    PermissionCodes.EmployeeAvailabilityView,
                    PermissionCodes.EmployeeAvailabilityManage,
                  ]}
                >
                  <EmployeeAvailabilityPage />
                </RequireAnyPermission>
              }
            />
            <Route
              path="/store-config"
              element={
                <RequireAnyPermission
                  permissions={[PermissionCodes.StoreConfigView, PermissionCodes.StoreConfigManage]}
                >
                  <StoreConfigPage />
                </RequireAnyPermission>
              }
            />
            <Route
              path="/scheduling"
              element={
                <RequireAnyPermission permissions={schedViewPerms}>
                  <SchedulingShell>
                    <OverviewPage />
                  </SchedulingShell>
                </RequireAnyPermission>
              }
            />
            <Route
              path="/scheduling/roster"
              element={
                <RequireAnyPermission permissions={schedViewPerms}>
                  <SchedulingShell>
                    <RosterPage />
                  </SchedulingShell>
                </RequireAnyPermission>
              }
            />
            <Route
              path="/scheduling/runs"
              element={
                <RequireAnyPermission permissions={schedViewPerms}>
                  <SchedulingShell>
                    <RunsPage />
                  </SchedulingShell>
                </RequireAnyPermission>
              }
            />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
