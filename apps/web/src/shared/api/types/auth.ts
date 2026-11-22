export interface LoginRequest {
  email: string
  password: string
}

export interface StoreAccessDto {
  id: number
  code: string
  name: string
}

export interface MeResponse {
  id: number
  email: string
  displayName: string
  role: string
  roleId: number
  allStores: boolean
  isActive: boolean
  permissions: string[]
  stores: StoreAccessDto[]
}
