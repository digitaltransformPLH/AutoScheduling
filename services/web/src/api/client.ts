// API client: types generated from FastAPI OpenAPI (npm run gen:api), never written by hand.
import type { components } from './schema'

export type Schemas = components['schemas']
export type Meta = Schemas['Meta']
export type StoreItem = Schemas['StoreItem']
export type ForecastWeek = Schemas['ForecastWeek']
export type ScheduleWeek = Schemas['ScheduleWeek']
export type DaySummary = Schemas['DaySummary']
export type HourCoverage = Schemas['HourCoverage']
export type RosterDay = Schemas['RosterDay']
export type Issue = Schemas['Issue']
export type Overview = Schemas['Overview']
export type Run = Schemas['Run']
export type RunRequest = Schemas['RunRequest']
export type StoreConfig = Schemas['StoreConfig']
export type EmployeeItem = Schemas['EmployeeItem']
export type AvailabilityItem = Schemas['AvailabilityItem']
export type SecondmentItem = Schemas['SecondmentItem']
export type Me = Schemas['Me']
export type LoginRequest = Schemas['LoginRequest']
export type InputOptions = Schemas['InputOptions']
export type EmployeeIn = Schemas['EmployeeIn']
export type EmployeeUpdate = Schemas['EmployeeUpdate']
export type AvailabilityDayIn = Schemas['AvailabilityDayIn']
export type SecondmentIn = Schemas['SecondmentIn']
export type SecondmentUpdate = Schemas['SecondmentUpdate']
export type StoreConfigIn = Schemas['StoreConfigIn']
export type ImportResult = Schemas['ImportResult']
export type Saved = Schemas['Saved']
export type Envelope<T> = { data: T; meta: Meta }

export const API_BASE = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api/v1/sched`.replace(/^\.\//, '')

export class ApiError extends Error {
  status: number
  constructor(status: number, msg: string) {
    super(msg)
    this.status = status
  }
}

export type Params = Record<string, string | number | boolean | null | undefined>

export const qs = (p: Params = {}) => {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== null && v !== '' && v !== false) sp.set(k, String(v))
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// 401 anywhere (session expired / not logged in) -> the app shows the login screen
export const AUTH_EVENT = 'sched:unauthorized'

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 401 && !res.url.endsWith('/auth/login')) window.dispatchEvent(new Event(AUTH_EVENT))
  if (!res.ok) {
    let msg = res.statusText
    try {
      const b = await res.json()
      msg = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail ?? msg)
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function getJson<T>(path: string, params?: Params): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}${qs(params)}`, { headers: { Accept: 'application/json' } }))
}

export async function sendJson<T>(path: string, body: unknown, method = 'POST'): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}`, {
    method, headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body),
  }))
}

export async function sendForm<T>(path: string, form: FormData): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { Accept: 'application/json' }, body: form }))
}

export const fileUrl = (path: string, params?: Params) => `${API_BASE}${path}${qs(params)}`
