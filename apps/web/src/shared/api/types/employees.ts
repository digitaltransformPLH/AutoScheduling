export type EmployeeListItemDto = {
  id: number
  fullName: string
  employeeNumber: number
  plantCode: string
  plantName?: string | null
  position: string
  employmentType: string
  laborGroup: string
  status: string
  createdAt: string
  updatedAt: string
}

export type EmployeeDetailDto = EmployeeListItemDto

export type UpsertEmployeeRequest = {
  fullName: string
  employeeNumber: number
  plantCode: string
  position: string
  employmentType: string
  laborGroup: string
  status: string
}

export type EmployeeLookupsDto = {
  positions: string[]
  employmentTypes: string[]
  laborGroups: string[]
  statuses: string[]
}

export type PagedEmployees = {
  items: EmployeeListItemDto[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export type EmployeeImportRowErrorDto = {
  row: number
  message: string
}

export type EmployeeImportResultDto = {
  created: number
  updated: number
  failed: number
  errors: EmployeeImportRowErrorDto[]
}

export type EmployeeSecondmentListItemDto = {
  id: number
  employeeId: number
  employeeNumber: number
  fullName: string
  homePlantCode: string
  homePlantName?: string | null
  receivingStoreCode: string
  receivingStoreName?: string | null
  startDate: string
  endDate: string
  status: string
  createdAt: string
  updatedAt: string
  updatedBy: string
}

export type PagedEmployeeSecondments = {
  items: EmployeeSecondmentListItemDto[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export type CreateEmployeeSecondmentRequest = {
  startDate: string
  endDate: string
  receivingStoreCode: string
}

export type UpdateEmployeeSecondmentRequest = CreateEmployeeSecondmentRequest