import { apiFetch, getApiBase } from '../../shared/api/http'
import type { PagedResult } from '../../shared/api/types/stores'
import type {
  StoreConfigDetailDto,
  StoreConfigImportResultDto,
  StoreConfigListItemDto,
  UpsertStoreConfigRequest,
} from '../../shared/api/types'

export function listStoreConfigsPaged(page: number, pageSize: number, search?: string) {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  })
  if (search?.trim()) params.set('search', search.trim())
  return apiFetch<PagedResult<StoreConfigListItemDto>>(`/store-configs?${params}`)
}

export function getStoreConfig(storeId: number) {
  return apiFetch<StoreConfigDetailDto>(`/store-configs/${storeId}`)
}

export function upsertStoreConfig(storeId: number, body: UpsertStoreConfigRequest) {
  return apiFetch<StoreConfigDetailDto>(`/store-configs/${storeId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function exportStoreConfigsExcel(): Promise<{ blob: Blob; fileName: string }> {
  const url = `${getApiBase()}/store-configs/export`
  const res = await fetch(url, { credentials: 'include' })
  if (!res.ok) {
    const text = await res.text()
    let message = `HTTP ${res.status}`
    try {
      const data = JSON.parse(text) as { message?: string }
      if (data.message) message = data.message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition')
  let fileName = 'Store_Config.xlsx'
  const match = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)"?/i)
  if (match?.[1]) fileName = decodeURIComponent(match[1].trim())
  return { blob, fileName }
}

export async function importStoreConfigsExcel(file: File): Promise<StoreConfigImportResultDto> {
  const url = `${getApiBase()}/store-configs/import`
  const body = new FormData()
  body.append('file', file)
  const res = await fetch(url, { method: 'POST', credentials: 'include', body })
  const text = await res.text()
  const data = text ? (JSON.parse(text) as StoreConfigImportResultDto & { message?: string }) : null
  if (!res.ok) throw new Error(data?.message ?? `HTTP ${res.status}`)
  return data as StoreConfigImportResultDto
}