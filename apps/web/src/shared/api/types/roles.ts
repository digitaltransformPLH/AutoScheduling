export interface RoleDto {
  id: number
  name: string
  description?: string | null
  isSystem: boolean
  permissions: string[]
  permissionIds: number[]
}

export interface UpsertRoleRequest {
  name: string
  description?: string | null
  permissionIds: number[]
}

export interface SetRolePermissionsRequest {
  permissionIds: number[]
}

export interface PermissionDto {
  id: number
  code: string
  name: string
}
