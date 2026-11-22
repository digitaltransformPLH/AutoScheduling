import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../features/auth/AuthContext'
import { PermissionCodes } from '../api/types'

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? 'active' : ''
}

function AdminNavSection({
  title,
  show,
  children,
}: {
  title: string
  show: boolean
  children: ReactNode
}) {
  if (!show) return null
  return (
    <section className="admin-menu-block">
      <div className="admin-menu-title">{title}</div>
      <nav className="admin-nav">{children}</nav>
    </section>
  )
}

export function AdminLayout() {
  const { me, logout, hasPermission } = useAuth()

  const showUsers = hasPermission(PermissionCodes.UserManage)
  const showRoles = hasPermission(PermissionCodes.RoleManage)
  const showStores = hasPermission(PermissionCodes.StoreManage)
  const showAmOm = hasPermission(PermissionCodes.AmOmManage)
  const showEmployees =
    hasPermission(PermissionCodes.EmployeeView) || hasPermission(PermissionCodes.EmployeeManage)
  const showSchedView =
    hasPermission(PermissionCodes.PlanningOverviewView) ||
    hasPermission(PermissionCodes.PlanningAnalysisView)
  const showEmployeeAvailability =
    hasPermission(PermissionCodes.EmployeeAvailabilityView) ||
    hasPermission(PermissionCodes.EmployeeAvailabilityManage)
  const showStoreConfig =
    hasPermission(PermissionCodes.StoreConfigView) ||
    hasPermission(PermissionCodes.StoreConfigManage)
  const showDataInputs = showEmployees || showEmployeeAvailability || showStoreConfig
  const showOrganization = showStores || showAmOm
  const showSystem = showUsers || showRoles

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <h1>Phúc Long</h1>
          <p>Workforce Planning</p>
        </div>

        {showSchedView && (
          <nav className="admin-nav admin-nav-primary">
            <NavLink to="/scheduling" end className={navClass}>
              Tổng quan
            </NavLink>
          </nav>
        )}

        <AdminNavSection title="Xếp lịch tự động" show={showSchedView}>
          <NavLink to="/scheduling/roster" className={navClass}>
            Roster tuần
          </NavLink>
          <NavLink to="/scheduling/runs" className={navClass}>
            Lịch sử engine
          </NavLink>
        </AdminNavSection>

        <AdminNavSection title="Dữ liệu đầu vào" show={showDataInputs}>
          {showEmployees && (
            <NavLink to="/employees" className={navClass}>
              Nhân viên
            </NavLink>
          )}
          {showEmployeeAvailability && (
            <NavLink to="/employee-availability" className={navClass}>
              Lịch bận nhân viên
            </NavLink>
          )}
          {showStoreConfig && (
            <NavLink to="/store-config" className={navClass}>
              Cấu hình cửa hàng (OPS)
            </NavLink>
          )}
        </AdminNavSection>

        <AdminNavSection title="Tổ chức" show={showOrganization}>
          {showStores && (
            <NavLink to="/stores" className={navClass}>
              Cửa hàng
            </NavLink>
          )}
          {showAmOm && (
            <NavLink to="/am-om" className={navClass}>
              Mapping AM → OM
            </NavLink>
          )}
        </AdminNavSection>

        <AdminNavSection title="Quản trị hệ thống" show={showSystem}>
          {showUsers && (
            <NavLink to="/users" className={navClass}>
              Người dùng
            </NavLink>
          )}
          {showRoles && (
            <NavLink to="/roles" className={navClass}>
              Vai trò & quyền
            </NavLink>
          )}
        </AdminNavSection>
      </aside>

      <div className="admin-main">
        <header className="admin-header">
          <div>
            <h2>Workforce Planning</h2>
            <p>Quản trị dữ liệu, xếp lịch và phân quyền</p>
          </div>
          <div className="admin-user">
            <div className="meta">
              <b>{me?.displayName || me?.email || '—'}</b>
              <span>{me?.role || '—'}</span>
            </div>
            <button type="button" className="btn" onClick={() => void logout()}>
              Đăng xuất
            </button>
          </div>
        </header>
        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}