import { useEffect, useState, type FormEvent } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import type { EmployeeLookupsDto, StoreDto, UpsertEmployeeRequest } from '../../shared/api/types'
import * as employeesApi from './api'

type Props = {
  open: boolean
  employeeId: number | null
  stores: StoreDto[]
  lookups: EmployeeLookupsDto | undefined
  onClose: () => void
  onSaved: () => void
}

const empty: UpsertEmployeeRequest = {
  fullName: '',
  employeeNumber: 0,
  plantCode: '',
  position: '',
  employmentType: '',
  laborGroup: 'Regular',
  status: 'Active',
}

function fmtDt(iso: string) {
  try {
    return new Date(iso).toLocaleString('vi-VN')
  } catch {
    return iso
  }
}

export function EmployeeFormModal({
  open,
  employeeId,
  stores,
  lookups,
  onClose,
  onSaved,
}: Props) {
  const [form, setForm] = useState<UpsertEmployeeRequest>(empty)
  const [createdAt, setCreatedAt] = useState('')
  const [updatedAt, setUpdatedAt] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!open) return
    setErr('')
    if (!employeeId) {
      setForm({
        ...empty,
        position: lookups?.positions[0] ?? '',
        employmentType: lookups?.employmentTypes[0] ?? '',
        laborGroup: lookups?.laborGroups[0] ?? 'Regular',
      })
      setCreatedAt('')
      setUpdatedAt('')
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const e = await employeesApi.getEmployee(employeeId)
        if (cancelled) return
        setForm({
          fullName: e.fullName,
          employeeNumber: e.employeeNumber,
          plantCode: e.plantCode,
          position: e.position,
          employmentType: e.employmentType,
          laborGroup: e.laborGroup,
          status: e.status,
        })
        setCreatedAt(e.createdAt)
        setUpdatedAt(e.updatedAt)
      } catch (ex) {
        if (!cancelled) setErr(ex instanceof Error ? ex.message : 'Lỗi')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, employeeId, lookups])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      if (employeeId) await employeesApi.updateEmployee(employeeId, form)
      else await employeesApi.createEmployee(form)
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lưu thất bại')
    }
  }

  const positions = lookups?.positions ?? []
  const employmentTypes = lookups?.employmentTypes ?? []
  const laborGroups = lookups?.laborGroups ?? []
  const statuses = lookups?.statuses ?? []

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h3>{employeeId ? 'Sửa nhân viên' : 'Thêm nhân viên'}</h3>
        {loading ? (
          <PageLoading compact />
        ) : (
          <form onSubmit={onSubmit}>
            <div className="field">
              <label>Employee Name</label>
              <input
                required
                value={form.fullName}
                onChange={(ev) => setForm((f) => ({ ...f, fullName: ev.target.value }))}
              />
            </div>
            <div className="field">
              <label>Employee ID</label>
              <input
                type="number"
                required
                min={1}
                disabled={employeeId !== null}
                value={form.employeeNumber || ''}
                onChange={(ev) =>
                  setForm((f) => ({ ...f, employeeNumber: Number(ev.target.value) }))
                }
              />
            </div>
            <div className="field">
              <label>Plant (mã cửa hàng)</label>
              <select
                required
                value={form.plantCode}
                onChange={(ev) => setForm((f) => ({ ...f, plantCode: ev.target.value }))}
              >
                <option value="">— Chọn —</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.code}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Position</label>
              <select
                required
                value={form.position}
                onChange={(ev) => setForm((f) => ({ ...f, position: ev.target.value }))}
              >
                {positions.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Employment Type</label>
              <select
                required
                value={form.employmentType}
                onChange={(ev) => setForm((f) => ({ ...f, employmentType: ev.target.value }))}
              >
                {employmentTypes.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Labor group</label>
              <select
                required
                value={form.laborGroup}
                onChange={(ev) => setForm((f) => ({ ...f, laborGroup: ev.target.value }))}
              >
                {laborGroups.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Status</label>
              <select
                required
                value={form.status}
                onChange={(ev) => setForm((f) => ({ ...f, status: ev.target.value }))}
              >
                {statuses.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            {employeeId !== null && (createdAt || updatedAt) && (
              <p className="muted" style={{ fontSize: '0.9rem', marginBottom: 12 }}>
                Tạo: {createdAt ? fmtDt(createdAt) : '—'} · Cập nhật:{' '}
                {updatedAt ? fmtDt(updatedAt) : '—'}
              </p>
            )}
            <div className="err">{err}</div>
            <div className="modal-actions">
              <button type="button" className="btn" onClick={onClose}>
                Hủy
              </button>
              <button type="submit" className="btn primary">
                Lưu
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}