import { useEffect, useState, type FormEvent } from 'react'
import type { AmOmAssignmentDto, PersonDto } from '../../shared/api/types'
import * as amOmApi from './api'

type Props = {
  open: boolean
  row: AmOmAssignmentDto | null
  areaManagers: PersonDto[]
  operationManagers: PersonDto[]
  onClose: () => void
  onSaved: () => void
}

export function AmOmFormModal({
  open,
  row,
  areaManagers,
  operationManagers,
  onClose,
  onSaved,
}: Props) {
  const [amId, setAmId] = useState<number | ''>('')
  const [omId, setOmId] = useState<number | ''>('')
  const [effectiveFrom, setEffectiveFrom] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!open) return
    setErr('')
    if (row) {
      setAmId(row.areaManagerId)
      setOmId(row.operationManagerId)
      setEffectiveFrom(row.effectiveFrom?.slice(0, 10) ?? '')
    } else {
      setAmId('')
      setOmId('')
      setEffectiveFrom(new Date().toISOString().slice(0, 10))
    }
  }, [open, row])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!omId) {
      setErr('Chọn Operation Manager.')
      return
    }
    try {
      if (row) {
        await amOmApi.updateAmOm(row.areaManagerId, {
          operationManagerId: Number(omId),
          effectiveFrom: effectiveFrom || null,
        })
      } else {
        if (!amId) {
          setErr('Chọn Area Manager.')
          return
        }
        await amOmApi.createAmOm({
          areaManagerId: Number(amId),
          operationManagerId: Number(omId),
          effectiveFrom: effectiveFrom || null,
        })
      }
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lưu thất bại')
    }
  }

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{row ? 'Sửa mapping AM → OM' : 'Thêm mapping'}</h3>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Area Manager</label>
            {row ? (
              <input readOnly value={row.areaManagerName} />
            ) : (
              <select value={amId} onChange={(e) => setAmId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">—</option>
                {areaManagers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.fullName}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="field">
            <label>Operation Manager</label>
            <select value={omId} onChange={(e) => setOmId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">—</option>
              {operationManagers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.fullName}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Hiệu lực từ</label>
            <input
              type="date"
              value={effectiveFrom}
              onChange={(e) => setEffectiveFrom(e.target.value)}
            />
          </div>
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
      </div>
    </div>
  )
}
