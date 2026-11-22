export interface PersonDto {
  id: number
  fullName: string
  email?: string | null
  phone?: string | null
  role: string
  isActive: boolean
}

export interface AmOmAssignmentDto {
  id: number
  areaManagerId: number
  areaManagerName: string
  operationManagerId: number
  operationManagerName: string
  effectiveFrom: string
  effectiveTo?: string | null
}

export interface CreateAmOmAssignmentRequest {
  areaManagerId: number
  operationManagerId: number
  effectiveFrom?: string | null
}

export interface UpsertAmOmAssignmentRequest {
  operationManagerId: number
  effectiveFrom?: string | null
}

export interface OperationManagerLookupResponse {
  operationManagerId: number
  operationManagerName: string
}
