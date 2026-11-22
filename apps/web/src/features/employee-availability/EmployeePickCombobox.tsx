import { useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { EmployeeAvailabilityEmployeePickDto } from '../../shared/api/types'
import { PageLoading } from '../../shared/components/PageLoading'
import * as availabilityApi from './api'

function pickLabel(p: EmployeeAvailabilityEmployeePickDto) {
  const tag = p.source === 'borrowed' ? ` · mượn từ ${p.homePlantCode ?? '?'}` : ''
  return `${p.employeeNumber} — ${p.fullName}${tag}`
}

function isEligibleOnDate(p: EmployeeAvailabilityEmployeePickDto, workDate: string) {
  if (!workDate || p.source !== 'borrowed') return true
  if (!p.secondmentStart || !p.secondmentEnd) return true
  return workDate >= p.secondmentStart && workDate <= p.secondmentEnd
}

type Props = {
  plantCode: string
  weekDate: string
  workDate: string
  value: number
  disabled?: boolean
  onChange: (employeeNumber: number) => void
}

export function EmployeePickCombobox({
  plantCode,
  weekDate,
  workDate,
  value,
  disabled,
  onChange,
}: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const blurTimer = useRef<number | null>(null)

  const picksQuery = useQuery({
    queryKey: ['employee-availability', 'picks', plantCode, weekDate, query],
    queryFn: () => availabilityApi.listEmployeeAvailabilityPicks(plantCode, weekDate, query),
    enabled: Boolean(plantCode) && !disabled,
  })

  const picks = picksQuery.data ?? []

  const selected = useMemo(
    () => picks.find((p) => p.employeeNumber === value),
    [picks, value],
  )

  const filtered = useMemo(() => {
    const list = picks.filter((p) => isEligibleOnDate(p, workDate))
    const q = query.trim().toLowerCase()
    if (!q) return list
    return list.filter(
      (p) =>
        p.fullName.toLowerCase().includes(q)
        || String(p.employeeNumber).includes(q)
        || p.position.toLowerCase().includes(q),
    )
  }, [picks, workDate, query])

  const home = filtered.filter((p) => p.source === 'store')
  const borrowed = filtered.filter((p) => p.source === 'borrowed')

  function onPick(p: EmployeeAvailabilityEmployeePickDto) {
    onChange(p.employeeNumber)
    setQuery(pickLabel(p))
    setOpen(false)
  }

  const displayValue =
    open ? query : value > 0 ? (selected ? pickLabel(selected) : String(value)) : query

  return (
    <div className="emp-pick">
      <input
        id="ea-emp"
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        disabled={disabled}
        placeholder="Gõ tên hoặc Employee ID để tìm…"
        value={displayValue}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => {
          if (blurTimer.current) window.clearTimeout(blurTimer.current)
          setOpen(true)
        }}
        onBlur={() => {
          blurTimer.current = window.setTimeout(() => setOpen(false), 150)
        }}
      />
      {open && !disabled && (
        <ul className="emp-pick-list" role="listbox">
          {picksQuery.isLoading && (
            <li className="emp-pick-empty">
              <PageLoading compact label="Đang tải danh sách…" />
            </li>
          )}
          {!picksQuery.isLoading && filtered.length === 0 && (
            <li className="emp-pick-empty">Không có nhân viên phù hợp.</li>
          )}
          {home.length > 0 && (
            <li className="emp-pick-group">Thuộc cửa hàng ({plantCode})</li>
          )}
          {home.map((p) => (
            <li key={`h-${p.employeeNumber}`}>
              <button type="button" role="option" onMouseDown={(e) => e.preventDefault()} onClick={() => onPick(p)}>
                <b>{p.employeeNumber}</b> {p.fullName}
                <span className="emp-pick-meta">{p.position}</span>
              </button>
            </li>
          ))}
          {borrowed.length > 0 && <li className="emp-pick-group">Mượn vào (còn hạn trong tuần)</li>}
          {borrowed.map((p) => (
            <li key={`b-${p.employeeNumber}`}>
              <button type="button" role="option" onMouseDown={(e) => e.preventDefault()} onClick={() => onPick(p)}>
                <b>{p.employeeNumber}</b> {p.fullName}
                <span className="emp-pick-meta">
                  {p.homePlantCode} → {plantCode}
                  {p.secondmentStart && p.secondmentEnd
                    ? ` · ${p.secondmentStart} – ${p.secondmentEnd}`
                    : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}