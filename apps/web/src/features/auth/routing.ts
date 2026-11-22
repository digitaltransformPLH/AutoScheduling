import { PermissionCodes } from '../../shared/api/types'
import type { MeResponse } from '../../shared/api/types'

export function defaultAdminPath(me: MeResponse | { permissions: string[] }): string {
  const perms = me.permissions ?? []
  const has = (code: string) => perms.some((p) => p.toLowerCase() === code.toLowerCase())
  if (has(PermissionCodes.PlanningOverviewView) || has(PermissionCodes.PlanningAnalysisView)) {
    return '/scheduling'
  }
  if (has(PermissionCodes.UserManage)) return '/users'
  if (has(PermissionCodes.RoleManage)) return '/roles'
  if (has(PermissionCodes.StoreManage)) return '/stores'
  if (has(PermissionCodes.EmployeeManage)) return '/employees'
  if (has(PermissionCodes.EmployeeView)) return '/employees'
  if (has(PermissionCodes.AmOmManage)) return '/am-om'
  return '/home'
}
