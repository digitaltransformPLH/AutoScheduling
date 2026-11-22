import { apiFetch } from '../../shared/api/http'
import type { LoginRequest, MeResponse } from '../../shared/api/types'

export function getMe() {
  return apiFetch<MeResponse>('/me')
}

export function login(body: LoginRequest) {
  return apiFetch<MeResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function logout() {
  return apiFetch<void>('/auth/logout', { method: 'POST' })
}
