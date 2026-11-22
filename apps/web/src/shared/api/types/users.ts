import type { StoreAccessDto } from './auth'

export interface UserListItemDto {
  id: number
  email: string
  displayName: string
  roleId: number
  roleName: string
  allStores: boolean
  isActive: boolean
  stores: StoreAccessDto[]
}

export interface UserDetailDto extends UserListItemDto {
  storeIds: number[]
}

export interface UpsertUserRequest {
  email: string
  displayName: string
  password?: string | null
  roleId: number
  allStores: boolean
  isActive: boolean
  storeIds: number[]
}
