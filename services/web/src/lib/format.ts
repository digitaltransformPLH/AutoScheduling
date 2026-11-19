export const fmt = (v: number | null | undefined, d = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d })

export const ddmm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`
export const ddmmyyyy = (iso: string) => `${ddmm(iso)}/${iso.slice(0, 4)}`

export const toMin = (hhmm: string) => {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}
export const hhmm = (m: number) => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

/** "Nguyễn Phạm Quỳnh Anh" -> "Quỳnh Anh"; drops a trailing "(NSO)". */
export const shortName = (n: string) => {
  const p = n.replace(/\s*\(.*\)$/, '').trim().split(/\s+/)
  return p.length > 2 ? p.slice(-2).join(' ') : p.join(' ')
}

export const isManagerPos = (p: string) => /Manager|Supervisor/i.test(p)

/** ISO week number (for "Tuần 46" labels). */
export function isoWeek(iso: string) {
  const d = new Date(`${iso}T00:00:00Z`)
  const day = (d.getUTCDay() + 6) % 7
  d.setUTCDate(d.getUTCDate() - day + 3)
  const firstThu = new Date(Date.UTC(d.getUTCFullYear(), 0, 4))
  return 1 + Math.round(((d.getTime() - firstThu.getTime()) / 86400000 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7)
}

export const addDays = (iso: string, n: number) => {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}
