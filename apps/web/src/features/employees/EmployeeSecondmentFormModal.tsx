import { useEffect, useState, type FormEvent } from 'react'
import type {
  CreateEmployeeSecondmentRequest,
  EmployeeListItemDto,
  EmployeeSecondmentListItemDto,
  StoreDto,
} from '../../shared/api/types'
import * as employeesApi from './api'

type EmployeePick = Pick<EmployeeListItemDto, 'id' | 'fullName' | 'employeeNumber' | 'plantCode' | 'plantName'>

type Props = {
  open: boolean
  employee: EmployeePick | null
  secondment: EmployeeSecondmentListItemDto | null
  stores: StoreDto[]
  onClose: () => void
  onSaved: () => void
}

export function EmployeeSecondmentFormModal({
  open,
  employee,
  secondment,
  stores,
  onClose,
  onSaved,
}: Props) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [receivingStoreCode, setReceivingStoreCode] = useState('')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const activeStores = stores.filter((s) => s.isActive !== false)
  const isEdit = secondment != null
  const contextEmployee = employee ?? (secondment
    ? {
        id: secondment.employeeId,
        fullName: secondment.fullName,
        employeeNumber: secondment.employeeNumber,
        plantCode: secondment.homePlantCode,
        plantName: secondment.homePlantName,
      }
    : null)

  useEffect(() => {
    if (!open) return
    setErr('')
    setSaving(false)
    if (secondment) {
      setStartDate(secondment.startDate.slice(0, 10))
      setEndDate(secondment.endDate.slice(0, 10))
      setReceivingStoreCode(secondment.receivingStoreCode)
    } else {
      const today = new Date().toISOString().slice(0, 10)
      setStartDate(today)
      setEndDate(today)
      setReceivingStoreCode('')
    }
  }, [open, secondment])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!contextEmployee) {
      setErr('Thiếu thông tin nhân viên.')
      return
    }
    if (!receivingStoreCode) {
      setErr('Chọn store nhận.')
      return
    }
    if (receivingStoreCode === contextEmployee.plantCode) {
      setErr('Store nhận phải khác plant gốc của nhân viên.')
      return
    }

    const body: CreateEmployeeSecondmentRequest = {
      startDate,
      endDate,
      receivingStoreCode,
    }

    setSaving(true)
    try {
      if (isEdit && secondment) {
        await employeesApi.updateEmployeeSecondment(secondment.id, body)
      } else {
        await employeesApi.createEmployeeSecondment(contextEmployee.id, body)
      }
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lưu thất bại')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h3>{isEdit ? 'Sửa điều động tạm' : 'Điều động tạm nhân sự'}</h3>
        {contextEmployee && (
          <p style={{ fontSize: 13, color: '#5a6b5f', margin: '0 0 12px' }}>
            {contextEmployee.employeeNumber} — {contextEmployee.fullName}
            <br />
            Plant gốc: {contextEmployee.plantCode}
            {contextEmployee.plantName ? ` — ${contextEmployee.plantName}` : ''}
          </p>
        )}
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Ngày bắt đầu</label>
            <input
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Ngày kết thúc</label>
            <input type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div className="field">
            <label>Store nhận</label>
            <select
              required
              value={receivingStoreCode}
              onChange={(e) => setReceivingStoreCode(e.target.value)}
            >
              <option value="">— Chọn store —</option>
              {activeStores.map((s) => (
                <option key={s.id} value={s.code}>
                  {s.code} — {s.name}
                </option>
              ))}
            </select>
          </div>
          {err && <p className="form-err">{err}</p>}
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Hủy
            </button>
            <button type="submit" className="btn primary" disabled={saving}>
              {saving ? 'Đang lưu...' : 'Lưu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}