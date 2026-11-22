import { useEffect, useState, type FormEvent } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import type { PersonDto, UpsertStoreRequest } from '../../shared/api/types'
import * as storesApi from './api'

type Props = {
  open: boolean
  storeId: number | null
  areaManagers: PersonDto[]
  onClose: () => void
  onSaved: () => void
}

const empty: UpsertStoreRequest = {
  code: '',
  name: '',
  city: '',
  concept: '',
  openDate: '',
  email: '',
  areaManagerId: null,
  isActive: true,
}

export function StoreFormModal({ open, storeId, areaManagers, onClose, onSaved }: Props) {
  const [form, setForm] = useState<UpsertStoreRequest>(empty)
  const [omPreview, setOmPreview] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!open) return
    setErr('')
    if (!storeId) {
      setForm(empty)
      setOmPreview('')
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const s = await storesApi.getStore(storeId)
        if (cancelled) return
        setForm({
          code: s.code,
          name: s.name,
          city: s.city ?? '',
          concept: s.concept ?? '',
          openDate: s.openDate ?? '',
          email: s.email ?? '',
          areaManagerId: s.areaManagerId ?? null,
          isActive: s.isActive,
        })
        setOmPreview(s.operationManagerName ?? '')
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

  async function onAmChange(amId: number | null) {
    setForm((f) => ({ ...f, areaManagerId: amId }))
    if (!amId) {
      setOmPreview('')
      return
    }
    try {
      const om = await storesApi.getOmByAm(amId)
      setOmPreview(om.operationManagerName)
    } catch {
      setOmPreview('')
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      if (storeId) await storesApi.updateStore(storeId, form)
      else await storesApi.createStore(form)
      onSaved()
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lưu thất bại')
    }
  }

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{storeId ? 'Sửa cửa hàng' : 'Thêm cửa hàng'}</h3>
        {loading ? (
          <PageLoading compact />
        ) : (
          <form onSubmit={onSubmit}>
            <div className="field">
              <label>Mã cửa hàng (PLANT)</label>
              <input
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                required
                disabled={!!storeId}
              />
            </div>
            <div className="field">
              <label>Tên cửa hàng</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </div>
            <div className="field">
              <label>Thành phố</label>
              <input value={form.city ?? ''} onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))} />
            </div>
            <div className="field">
              <label>Concept</label>
              <input
                value={form.concept ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, concept: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                value={form.email ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Ngày mở</label>
              <input
                type="date"
                value={form.openDate ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, openDate: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Area Manager</label>
              <select
                value={form.areaManagerId ?? ''}
                onChange={(e) => {
                  const v = e.target.value ? Number(e.target.value) : null
                  void onAmChange(v)
                }}
              >
                <option value="">—</option>
                {areaManagers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.fullName}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Operation Manager</label>
              <input readOnly placeholder="Tự động theo AM" value={omPreview} />
            </div>
            <div className="field checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={form.isActive}
                  onChange={(e) => setForm((f) => ({ ...f, isActive: e.target.checked }))}
                />
                Đang hoạt động
              </label>
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
        )}
      </div>
    </div>
  )
}
