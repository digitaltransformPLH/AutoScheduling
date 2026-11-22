import { apiFetch, getApiBase } from '../../shared/api/http'
import type {
  EmployeeAvailabilityEmployeePickDto,
  EmployeeAvailabilityImportResultDto,
  EmployeeAvailabilitySlotListItemDto,
  EmployeeAvailabilityWeekResponse,
  UpsertEmployeeAvailabilitySlotRequest,
} from '../../shared/api/types'

export function listEmployeeAvailabilityPicks(plantCode: string, weekDate: string, search?: string) {
  const q = new URLSearchParams({ plantCode, weekDate })
  if (search?.trim()) q.set('search', search.trim())
  return apiFetch<EmployeeAvailabilityEmployeePickDto[]>(`/employee-availability/employee-picks?${q}`)
}

export function getEmployeeAvailabilityWeek(
  plantCode: string,
  weekDate: string,
  page = 1,
  pageSize = 50,
  search?: string,
) {
  const q = new URLSearchParams({
    plantCode,
    weekDate,
    page: String(page),
    pageSize: String(pageSize),
  })
  if (search?.trim()) q.set('search', search.trim())
  return apiFetch<EmployeeAvailabilityWeekResponse>(`/employee-availability?${q}`)
}

export function createEmployeeAvailabilitySlot(weekDate: string, body: UpsertEmployeeAvailabilitySlotRequest) {
  return apiFetch<EmployeeAvailabilitySlotListItemDto>(`/employee-availability?weekDate=${encodeURIComponent(weekDate)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateEmployeeAvailabilitySlot(
  id: number,
  weekDate: string,
  body: UpsertEmployeeAvailabilitySlotRequest,
) {
  return apiFetch<EmployeeAvailabilitySlotListItemDto>(
    `/employee-availability/${id}?weekDate=${encodeURIComponent(weekDate)}`,
    {
      method: 'PUT',
      body: JSON.stringify(body),
    },
  )
}

export function deleteEmployeeAvailabilitySlot(id: number) {
  return apiFetch<void>(`/employee-availability/${id}`, { method: 'DELETE' })
}

export async function exportEmployeeAvailabilityExcel(
  plantCode: string,
  weekDate: string,
): Promise<{ blob: Blob; fileName: string }> {
  const q = new URLSearchParams({ plantCode, weekDate })
  const url = `${getApiBase()}/employee-availability/export?${q}`
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
  let fileName = 'Availability.xlsx'
  const match = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)"?/i)
  if (match?.[1]) fileName = decodeURIComponent(match[1].trim())
  return { blob, fileName }
}

export async function importEmployeeAvailabilityExcel(
  weekDate: string,
  file: File,
): Promise<EmployeeAvailabilityImportResultDto> {
  const form = new FormData()
  form.append('file', file)
  const url = `${getApiBase()}/employee-availability/import?weekDate=${encodeURIComponent(weekDate)}`
  const res = await fetch(url, { method: 'POST', credentials: 'include', body: form })
  const text = await res.text()
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const data = JSON.parse(text) as { message?: string }
      if (data.message) message = data.message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  return JSON.parse(text) as EmployeeAvailabilityImportResultDto
}