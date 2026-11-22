import { useEffect, useState, type FormEvent } from 'react'
import type {
  EmployeeAvailabilitySlotListItemDto,
  UpsertEmployeeAvailabilitySlotRequest,
} from '../../shared/api/types'
import * as availabilityApi from './api'
import { EmployeePickCombobox } from './EmployeePickCombobox'
import { weekDayOptions } from './weekUtils'

type Props = {
  open: boolean
  weekDate: string
  plantCode: string
  editing: EmployeeAvailabilitySlotListItemDto | null
  onClose: () => void
  onSaved: () => void
}

const empty = (plantCode: string): UpsertEmployeeAvailabilitySlotRequest => ({
  plantCode,
  employeeNumber: 0,
  workDate: '',
  busyFrom: '07:00',
  busyTo: '15:00',
  isPaidLeave: false,
})

export function EmployeeAvailabilityFormModal({
  open,
  weekDate,
  plantCode,
  editing,
  onClose,
  onSaved,
}: Props) {
  const [form, setForm] = useState<UpsertEmployeeAvailabilitySlotRequest>(empty(plantCode))
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const dayOptions = weekDayOptions(weekDate)

  useEffect(() => {
    if (!open) return
    setErr('')
    if (editing) {
      setForm({
        plantCode: editing.plantCode,
        employeeNumber: editing.employeeNumber,
        workDate: editing.workDate,
        busyFrom: editing.isPaidLeave ? null : editing.busyFrom ?? '07:00',
        busyTo: editing.isPaidLeave ? null : editing.busyTo ?? '15:00',
        isPaidLeave: editing.isPaidLeave,
      })
    } else {
      setForm({
        ...empty(plantCode),
        workDate: weekDate,
      })
    }
  }, [open, editing, plantCode, weekDate])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.employeeNumber || form.employeeNumber < 1) {
      setErr('Nhập Employee ID hợp lệ.')
      return
    }
    if (!form.workDate) {
      setErr('Chọn ngày trong tuần.')
      return
    }
    setLoading(true)
    setErr('')
    try {
      const body: UpsertEmployeeAvailabilitySlotRequest = {
        ...form,
        plantCode: plantCode.trim(),
        busyFrom: form.isPaidLeave ? null : form.busyFrom,
        busyTo: form.isPaidLeave ? null : form.busyTo,
      }
      if (editing) {
        await availabilityApi.updateEmployeeAvailabilitySlot(editing.id, weekDate, body)
      } else {
        await availabilityApi.createEmployeeAvailabilitySlot(weekDate, body)
      }
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lỗi lưu')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose} role="presentation">
      <div className="modal" role="dialog" aria-modal onClick={(e) => e.stopPropagation()}>
        <h3>{editing ? 'Sửa lịch bận' : 'Thêm lịch bận'}</h3>
        <form onSubmit={(e) => void onSubmit(e)}>
          <div className="field">
            <label htmlFor="ea-plant">Plant</label>
            <input id="ea-plant" type="text" value={plantCode} readOnly disabled />
          </div>
          <div className="field">
            <label htmlFor="ea-emp">Nhân viên</label>
            <EmployeePickCombobox
              plantCode={plantCode}
              weekDate={weekDate}
              workDate={form.workDate}
              value={form.employeeNumber}
              disabled={Boolean(editing)}
              onChange={(employeeNumber) => setForm((f) => ({ ...f, employeeNumber }))}
            />
            {editing && (
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>Không đổi nhân viên khi sửa.</span>
            )}
          </div>
          <div className="field">
            <label htmlFor="ea-day">Ngày trong tuần</label>
            <select
              id="ea-day"
              required
              value={form.workDate}
              onChange={(e) => setForm((f) => ({ ...f, workDate: e.target.value }))}
            >
              {dayOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ea-al">
              <input
                id="ea-al"
                type="checkbox"
                checked={form.isPaidLeave}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    isPaidLeave: e.target.checked,
                    busyFrom: e.target.checked ? null : f.busyFrom ?? '07:00',
                    busyTo: e.target.checked ? null : f.busyTo ?? '15:00',
                  }))
                }
              />{' '}
              Nghỉ phép (AL) — bận cả ngày
            </label>
          </div>
          {!form.isPaidLeave && (
            <>
              <div className="field">
                <label htmlFor="ea-from">Bận từ</label>
                <input
                  id="ea-from"
                  type="time"
                  required
                  value={form.busyFrom ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, busyFrom: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="ea-to">Bận đến</label>
                <input
                  id="ea-to"
                  type="time"
                  required
                  value={form.busyTo ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, busyTo: e.target.value }))}
                />
              </div>
            </>
          )}
          {err && (
            <p className="err" style={{ marginBottom: 12 }} role="alert">
              {err}
            </p>
          )}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
            <button type="button" className="btn" onClick={onClose} disabled={loading}>
              Hủy
            </button>
            <button type="submit" className="btn primary" disabled={loading}>
              {loading ? 'Đang lưu…' : 'Lưu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}