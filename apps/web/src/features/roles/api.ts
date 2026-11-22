import { apiFetch } from '../../shared/api/http'
import type {
  PermissionDto,
  RoleDto,
  SetRolePermissionsRequest,
  UpsertRoleRequest,
} from '../../shared/api/types'

export function listRoles() {
  return apiFetch<RoleDto[]>('/roles')
}

export function listPermissions() {
  return apiFetch<PermissionDto[]>('/permissions')
}

export function createRole(body: UpsertRoleRequest) {
  return apiFetch<RoleDto>('/roles', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function setRolePermissions(id: number, body: SetRolePermissionsRequest) {
  return apiFetch<RoleDto>(`/roles/${id}/permissions`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function cloneRole(id: number) {
  return apiFetch<RoleDto>(`/roles/${id}/clone`, { method: 'POST' })
}

export function deleteRole(id: number) {
  return apiFetch<{ success: boolean }>(`/roles/${id}`, { method: 'DELETE' })
}
