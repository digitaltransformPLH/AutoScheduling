import { ApiError, getApiBase } from '../../../shared/api/http'

export const SCHED_API_BASE = `${getApiBase().replace(/\/$/, '')}/sched`

export type Meta = {
  dataVersion: number
  builtAt?: string | null
  source: string
  backTest: boolean
  availabilityWeek?: string | null
}

export type Envelope<T> = { data: T; meta: Meta }

export type StoreItem = {
  storeCode: string
  storeName: string
  openingTime?: string | null
  closingTime?: string | null
  tcphTarget?: number | null
  employeeCount: number
  hasForecast: boolean
  readyToSchedule: boolean
  scheduledWeeks: number
}

export type ForecastWeek = { weekStart: string; storeCount: number; createdAt?: string | null; methodVersion?: string | null }

export type ScheduleWeek = {
  storeCode: string
  weekStart: string
  weekEnd: string
  storeName?: string | null
  openingTime?: string | null
  closingTime?: string | null
  status: string
  assessment?: string | null
  tcphTarget?: number | null
  weeklyTcph?: number | null
  tcphInTarget?: boolean | null
  forecastTc?: number | null
  laborHours?: number | null
  nsoHours?: number | null
  staffCoveragePct?: number | null
  managerCoveragePct?: number | null
  employeeCount?: number
  errorCount: number
  warningCount?: number
  availabilityWeek?: string | null
  runId?: number | null
  note?: string | null
  createdAt?: string
  createdBy?: string
  runStatus?: string | null
  runFinishedAt?: string | null
}

export type DaySummary = {
  workDate: string
  weekday: string
  dayStatus: string
  forecastTc?: number | null
  regularHours?: number | null
  trainingHours?: number | null
  nsoHours?: number | null
  tcph?: number | null
  tcphInclNso?: number | null
  tcphInTarget?: boolean | null
  targetHoursMin?: number | null
  targetHoursMax?: number | null
  neededStaffHours?: number | null
  scheduledStaffHours?: number | null
  missingStaffHours?: number | null
  hoursWithoutManager?: number | null
  openers?: number | null
  closers?: number | null
}

export type HourCoverage = {
  workDate: string
  weekday: string
  slot: number
  timeSlot: string
  forecastTc: number
  isPeakHour: boolean
  neededStaff: number
  scheduledStaff: number
  managersOnDuty: number
  missingStaff: number
  status: string
}

export type RosterDay = {
  workDate: string
  weekday: string
  employeeId: string
  employeeName: string
  position: string
  employmentType: string
  laborGroup: string
  homeStore?: string | null
  dayType: string
  startTime?: string | null
  endTime?: string | null
  hours: number
  shiftCode?: string | null
  shiftRole?: string | null
  note?: string | null
  sortOrder: number
}

export type Issue = {
  severity: string
  workDate?: string | null
  employeeId?: string | null
  employeeName?: string | null
  message: string
  issueCode?: string | null
}

export type Overview = {
  week: ScheduleWeek
  days: DaySummary[]
  hourly: HourCoverage[]
  roster: RosterDay[]
  issues: Issue[]
}

export type Run = {
  runId: number
  storeCode: string
  weekStart: string
  availabilityWeek?: string | null
  status: string
  assessment?: string | null
  message?: string | null
  requestedBy: string
  requestedAt: string
  startedAt?: string | null
  finishedAt?: string | null
}

export type RunRequest = { storeCode: string; weekStart: string; availabilityWeek?: string | null }

export type Params = Record<string, string | number | boolean | null | undefined>

export const qs = (p: Params = {}) => {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) {
    if (v !== undefined && v !== null && v !== '' && v !== false) sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = res.statusText
    try {
      const b = await res.json()
      msg = typeof b.detail === 'string' ? b.detail : (b.message ?? JSON.stringify(b.detail ?? msg))
    } catch {
      /* not JSON */
    }
    throw new ApiError(msg, res.status)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function getJson<T>(path: string, params?: Params): Promise<T> {
  const url = `${SCHED_API_BASE}${path}${qs(params)}`
  return handle<T>(
    await fetch(url, { credentials: 'include', headers: { Accept: 'application/json' } }),
  )
}

export async function sendJson<T>(path: string, body: unknown, method = 'POST'): Promise<T> {
  return handle<T>(
    await fetch(`${SCHED_API_BASE}${path}`, {
      method,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}

export const fileUrl = (path: string, params?: Params) => `${SCHED_API_BASE}${path}${qs(params)}`