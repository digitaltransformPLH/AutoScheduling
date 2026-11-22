export function toDateInputValue(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function snapToMonday(anchorIso: string): string {
  const d = new Date(`${anchorIso}T12:00:00`)
  const dow = d.getDay()
  const diff = dow === 0 ? 6 : dow - 1
  d.setDate(d.getDate() - diff)
  return toDateInputValue(d)
}

export function weekEndSunday(mondayIso: string): string {
  const d = new Date(`${mondayIso}T12:00:00`)
  d.setDate(d.getDate() + 6)
  return toDateInputValue(d)
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + days)
  return toDateInputValue(d)
}

export function weekDayOptions(mondayIso: string): { value: string; label: string }[] {
  const labels = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
  const en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  return labels.map((label, i) => {
    const value = addDays(mondayIso, i)
    const short = new Date(`${value}T12:00:00`).toLocaleDateString('vi-VN')
    return { value, label: `${label} (${en[i]}) — ${short}` }
  })
}

export function fmtViDate(iso: string) {
  try {
    return new Date(`${iso}T12:00:00`).toLocaleDateString('vi-VN')
  } catch {
    return iso
  }
}