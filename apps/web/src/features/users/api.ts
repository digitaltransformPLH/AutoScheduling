import { apiFetch } from '../../shared/api/http'
import type { UpsertUserRequest, UserDetailDto, UserListItemDto } from '../../shared/api/types'

export function listUsers() {
  return apiFetch<UserListItemDto[]>('/users')
}

export function getUser(id: number) {
  return apiFetch<UserDetailDto>(`/users/${id}`)
}

export function createUser(body: UpsertUserRequest) {
  return apiFetch<UserDetailDto>('/users', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateUser(id: number, body: UpsertUserRequest) {
  return apiFetch<UserDetailDto>(`/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function deactivateUser(id: number) {
  return apiFetch<{ success: boolean }>(`/users/${id}`, { method: 'DELETE' })
}
