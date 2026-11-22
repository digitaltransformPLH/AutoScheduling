import { apiFetch } from '../../shared/api/http'
import type {
  PagedResult,
  StoreDetailDto,
  StoreDto,
  StoreListRow,
  UpsertStoreRequest,
} from '../../shared/api/types'
import type { OperationManagerLookupResponse } from '../../shared/api/types'
import type { PersonDto } from '../../shared/api/types'

export function listStoresSimple() {
  return apiFetch<StoreDto[]>('/stores')
}

export function listStoresPaged(page: number, pageSize: number, search?: string) {
  const q = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  })
  if (search?.trim()) q.set('search', search.trim())
  return apiFetch<PagedResult<StoreListRow>>(`/stores?${q}`)
}

export function getStore(id: number) {
  return apiFetch<StoreDetailDto>(`/stores/${id}`)
}

export function createStore(body: UpsertStoreRequest) {
  return apiFetch<StoreDetailDto>('/stores', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateStore(id: number, body: UpsertStoreRequest) {
  return apiFetch<StoreDetailDto>(`/stores/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function deleteStore(id: number) {
  return apiFetch<void>(`/stores/${id}`, { method: 'DELETE' })
}

export function listPersons(role?: string) {
  const q = role ? `?role=${encodeURIComponent(role)}` : ''
  return apiFetch<PersonDto[]>(`/persons${q}`)
}

export function getOmByAm(areaManagerId: number) {
  return apiFetch<OperationManagerLookupResponse>(`/am-om-assignments/by-am/${areaManagerId}/om`)
}
