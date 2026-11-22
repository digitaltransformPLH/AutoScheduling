import { apiFetch, getApiBase } from '../../shared/api/http'
import type {
  CreateEmployeeSecondmentRequest,
  EmployeeDetailDto,
  EmployeeImportResultDto,
  EmployeeLookupsDto,
  EmployeeSecondmentListItemDto,
  PagedEmployeeSecondments,
  PagedEmployees,
  UpdateEmployeeSecondmentRequest,
  UpsertEmployeeRequest,
} from '../../shared/api/types'

export function listEmployeesPaged(
  page: number,
  pageSize: number,
  search?: string,
  plantCode?: string,
) {
  const q = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  })
  if (search?.trim()) q.set('search', search.trim())
  if (plantCode?.trim()) q.set('plantCode', plantCode.trim())
  return apiFetch<PagedEmployees>(`/employees?${q}`)
}

export function getEmployeeLookups() {
  return apiFetch<EmployeeLookupsDto>('/employees/lookups')
}

export function getEmployee(id: number) {
  return apiFetch<EmployeeDetailDto>(`/employees/${id}`)
}

export function createEmployee(body: UpsertEmployeeRequest) {
  return apiFetch<EmployeeDetailDto>('/employees', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateEmployee(id: number, body: UpsertEmployeeRequest) {
  return apiFetch<EmployeeDetailDto>(`/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function deleteEmployee(id: number) {
  return apiFetch<void>(`/employees/${id}`, { method: 'DELETE' })
}

export async function exportEmployeesExcel(plantCode?: string): Promise<{ blob: Blob; fileName: string }> {
  const q = plantCode?.trim() ? `?plantCode=${encodeURIComponent(plantCode.trim())}` : ''
  const url = `${getApiBase()}/employees/export${q}`
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
  let fileName = 'Employee_Master.xlsx'
  const match = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)"?/i)
  if (match?.[1]) fileName = decodeURIComponent(match[1].trim())
  return { blob, fileName }
}

export function listEmployeeSecondmentsPaged(
  page: number,
  pageSize: number,
  search?: string,
  plantCode?: string,
  status?: string,
) {
  const q = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  })
  if (search?.trim()) q.set('search', search.trim())
  if (plantCode?.trim()) q.set('plantCode', plantCode.trim())
  if (status?.trim()) q.set('status', status.trim())
  return apiFetch<PagedEmployeeSecondments>(`/employee-secondments?${q}`)
}

export function createEmployeeSecondment(employeeId: number, body: CreateEmployeeSecondmentRequest) {
  return apiFetch<EmployeeSecondmentListItemDto>(`/employees/${employeeId}/secondments`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateEmployeeSecondment(id: number, body: UpdateEmployeeSecondmentRequest) {
  return apiFetch<EmployeeSecondmentListItemDto>(`/employee-secondments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function cancelEmployeeSecondment(id: number) {
  return apiFetch<EmployeeSecondmentListItemDto>(`/employee-secondments/${id}/cancel`, {
    method: 'POST',
  })
}

export async function importEmployeesExcel(file: File): Promise<EmployeeImportResultDto> {
  const url = `${getApiBase()}/employees/import`
  const body = new FormData()
  body.append('file', file)
  const res = await fetch(url, { method: 'POST', credentials: 'include', body })
  const text = await res.text()
  const data = text ? (JSON.parse(text) as EmployeeImportResultDto & { message?: string }) : null
  if (!res.ok) throw new Error(data?.message ?? `HTTP ${res.status}`)
  return data as EmployeeImportResultDto
}