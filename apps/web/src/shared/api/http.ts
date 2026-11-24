import { getPathBase } from './pathBase'

const envBase = import.meta.env.VITE_API_BASE as string | undefined

/** API base URL (e.g. `/api/v1` or `/auto-scheduling/api/v1`). */
export function getApiBase(): string {
  if (envBase) return envBase.replace(/\/$/, '')
  const meta = document.querySelector('meta[name="api-base"]')?.getAttribute('content')
  if (meta) return meta.replace(/\/$/, '')
  const pb = getPathBase()
  if (pb) return `${pb}/api/v1`
  const base = import.meta.env.BASE_URL?.replace(/\/$/, '') ?? ''
  if (base && base !== '.') return `${base}/api/v1`
  return '/api/v1'
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const base = getApiBase()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, {
    ...options,
    credentials: 'include',
    headers,
  })

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { raw: text }
    }
  }

  if (!res.ok) {
    const msg =
      (data as { message?: string; Message?: string })?.message ??
      (data as { message?: string; Message?: string })?.Message ??
      `HTTP ${res.status}`
    throw new ApiError(msg, res.status)
  }

  if (res.status === 204) return undefined as T
  return data as T
}
