import { apiFetch } from '../../shared/api/http'
import type {
  AmOmAssignmentDto,
  CreateAmOmAssignmentRequest,
  UpsertAmOmAssignmentRequest,
} from '../../shared/api/types'

export function listAmOm() {
  return apiFetch<AmOmAssignmentDto[]>('/am-om-assignments')
}

export function createAmOm(body: CreateAmOmAssignmentRequest) {
  return apiFetch<AmOmAssignmentDto>('/am-om-assignments', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateAmOm(areaManagerId: number, body: UpsertAmOmAssignmentRequest) {
  return apiFetch<AmOmAssignmentDto>(`/am-om-assignments/${areaManagerId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}
