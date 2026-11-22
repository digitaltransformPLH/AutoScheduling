export interface StoreDto {
  id: number
  code: string
  name: string
  isActive: boolean
}

export interface StoreDetailDto {
  id: number
  code: string
  name: string
  city?: string | null
  concept?: string | null
  openDate?: string | null
  closeDate?: string | null
  email?: string | null
  areaManagerId?: number | null
  areaManagerName?: string | null
  operationManagerName?: string | null
  isActive: boolean
}

export interface UpsertStoreRequest {
  code: string
  name: string
  city?: string | null
  concept?: string | null
  openDate?: string | null
  closeDate?: string | null
  email?: string | null
  areaManagerId?: number | null
  isActive: boolean
}

export interface PagedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface StoreListRow extends StoreDetailDto {}
