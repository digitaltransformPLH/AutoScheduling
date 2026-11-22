import { useEffect, useState, type FormEvent } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import {
  StoreConfigDefaults,
  type StoreConfigDetailDto,
  type UpsertStoreConfigRequest,
} from '../../shared/api/types'
import { useAuth } from '../auth/AuthContext'
import { PermissionCodes } from '../../shared/api/types'
import * as storeConfigApi from './api'

type Props = {
  open: boolean
  storeId: number | null
  onClose: () => void
  onSaved: () => void
}

const emptyForm: UpsertStoreConfigRequest = {
  tcphTarget: 0,
  tcphCeilingMult: StoreConfigDefaults.tcphCeilingMult,
  openStaff: StoreConfigDefaults.openStaff,
  closeStaff: StoreConfigDefaults.closeStaff,
  minStaffPerSlot: StoreConfigDefaults.minStaffPerSlot,
}

export function StoreConfigFormModal({ open, storeId, onClose, onSaved }: Props) {
  const { hasPermission } = useAuth()
  const canManage = hasPermission(PermissionCodes.StoreConfigManage)

  const [detail, setDetail] = useState<StoreConfigDetailDto | null>(null)
  const [form, setForm] = useState<UpsertStoreConfigRequest>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!open || storeId == null) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setErr('')
      try {
        const d = await storeConfigApi.getStoreConfig(storeId)
        if (cancelled) return
        setDetail(d)
        setForm({
          tcphTarget: d.isConfigured ? d.tcphTarget : 0,
          tcphCeilingMult: d.tcphCeilingMult,
          openStaff: d.openStaff,
          closeStaff: d.closeStaff,
          minStaffPerSlot: d.minStaffPerSlot,
        })
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Lỗi')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, storeId])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canManage || storeId == null) return
    setErr('')
    setLoading(true)
    try {
      await storeConfigApi.upsertStoreConfig(storeId, form)
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lỗi')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className={`modal-back${open ? ' show' : ''}`}
      role="presentation"
      onClick={onClose}
    >
      <div className="modal" role="dialog" onClick={(ev) => ev.stopPropagation()}>
        <h3>Cấu hình OPS — {detail?.storeCode ?? '…'}</h3>
        {detail && <p className="muted">{detail.storeName}</p>}
        {loading && !detail ? (
          <PageLoading compact label="Đang tải dữ liệu…" />
        ) : (
          <form onSubmit={onSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="sc-tcph">TCPH target *</label>
                <input
                  id="sc-tcph"
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  disabled={!canManage}
                  value={form.tcphTarget || ''}
                  onChange={(ev) =>
                    setForm((f) => ({ ...f, tcphTarget: Number(ev.target.value) }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="sc-ceiling">Hệ số trần TCPH</label>
                <input
                  id="sc-ceiling"
                  type="number"
                  step="0.01"
                  min="1.01"
                  max="2"
                  required
                  disabled={!canManage}
                  value={form.tcphCeilingMult}
                  onChange={(ev) =>
                    setForm((f) => ({ ...f, tcphCeilingMult: Number(ev.target.value) }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="sc-open">Open staff</label>
                <input
                  id="sc-open"
                  type="number"
                  min="1"
                  step="1"
                  required
                  disabled={!canManage}
                  value={form.openStaff}
                  onChange={(ev) =>
                    setForm((f) => ({ ...f, openStaff: Number(ev.target.value) }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="sc-close">Close staff</label>
                <input
                  id="sc-close"
                  type="number"
                  min="1"
                  step="1"
                  required
                  disabled={!canManage}
                  value={form.closeStaff}
                  onChange={(ev) =>
                    setForm((f) => ({ ...f, closeStaff: Number(ev.target.value) }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="sc-min">Min staff / slot</label>
                <input
                  id="sc-min"
                  type="number"
                  min="1"
                  step="1"
                  required
                  disabled={!canManage}
                  value={form.minStaffPerSlot}
                  onChange={(ev) =>
                    setForm((f) => ({ ...f, minStaffPerSlot: Number(ev.target.value) }))
                  }
                />
              </div>
            </div>
            {err && <div className="err">{err}</div>}
            <div className="modal-actions">
              <button type="button" className="btn" onClick={onClose}>
                Đóng
              </button>
              {canManage && (
                <button type="submit" className="btn primary" disabled={loading}>
                  Lưu
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  )
}