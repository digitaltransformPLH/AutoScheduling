import type { EmployeeImportRowErrorDto } from './employees'

export type EmployeeAvailabilitySlotListItemDto = {
  id: number
  plantCode: string
  plantName?: string | null
  employeeNumber: number
  employeeId?: number | null
  employeeName: string
  weekStartMonday: string
  workDate: string
  weekdayLabel: string
  busyFrom?: string | null
  busyTo?: string | null
  isPaidLeave: boolean
}

export type EmployeeAvailabilityWeekResponse = {
  weekStartMonday: string
  weekEndSunday: string
  plantCode?: string | null
  items: EmployeeAvailabilitySlotListItemDto[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export type UpsertEmployeeAvailabilitySlotRequest = {
  plantCode: string
  employeeNumber: number
  workDate: string
  busyFrom?: string | null
  busyTo?: string | null
  isPaidLeave: boolean
}

export type EmployeeAvailabilityImportResultDto = {
  created: number
  failed: number
  errors: EmployeeImportRowErrorDto[]
  weekStartMonday: string
  weekEndSunday: string
}

export type EmployeeAvailabilityEmployeePickDto = {
  employeeNumber: number
  fullName: string
  position: string
  source: 'store' | 'borrowed' | string
  homePlantCode?: string | null
  secondmentStart?: string | null
  secondmentEnd?: string | null
}