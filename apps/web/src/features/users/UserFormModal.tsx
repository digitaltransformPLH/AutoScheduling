import { useEffect, useState, type FormEvent } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import type { RoleDto, StoreDto, UpsertUserRequest } from '../../shared/api/types'
import * as usersApi from './api'
import { useUserMutations } from './hooks'

type Props = {
  open: boolean
  userId: number | null
  roles: RoleDto[]
  stores: StoreDto[]
  onClose: () => void
}

const emptyForm: UpsertUserRequest = {
  email: '',
  displayName: '',
  password: '',
  roleId: 0,
  allStores: false,
  isActive: true,
  storeIds: [],
}

export function UserFormModal({ open, userId, roles, stores, onClose }: Props) {
  const { save } = useUserMutations()
  const [form, setForm] = useState<UpsertUserRequest>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!open) return
    setErr('')
    if (!userId) {
      setForm({ ...emptyForm, roleId: roles[0]?.id ?? 0 })
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const u = await usersApi.getUser(userId)
        if (cancelled) return
        setForm({
          email: u.email,
          displayName: u.displayName,
          password: '',
          roleId: u.roleId,
          allStores: u.allStores,
          isActive: u.isActive,
          storeIds: u.storeIds ?? [],
        })
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Lỗi tải user')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, userId, roles])

  function toggleStore(id: number, checked: boolean) {
    setForm((f) => ({
      ...f,
      storeIds: checked ? [...new Set([...f.storeIds, id])] : f.storeIds.filter((x) => x !== id),
    }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    const payload: UpsertUserRequest = {
      ...form,
      email: form.email.trim(),
      displayName: form.displayName.trim(),
      storeIds: form.allStores ? [] : form.storeIds,
    }
    if (!payload.password) delete payload.password
    try {
      await save.mutateAsync({ id: userId, body: payload })
      onClose()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Lưu thất bại')
    }
  }

  return (
    <div className={`modal-back${open ? ' show' : ''}`} onClick={onClose}>
      <div className="modal" role="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>{userId ? 'Sửa người dùng' : 'Thêm người dùng'}</h3>
        {loading ? (
          <PageLoading compact />
        ) : (
          <form onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="displayName">Họ tên</label>
              <input
                id="displayName"
                value={form.displayName}
                onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="userEmail">Email</label>
              <input
                id="userEmail"
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="userPassword">Mật khẩu</label>
              <input
                id="userPassword"
                type="password"
                placeholder={userId ? 'Để trống nếu giữ nguyên' : ''}
                value={form.password ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                required={!userId}
              />
            </div>
            <div className="field">
              <label htmlFor="userRole">Vai trò</label>
              <select
                id="userRole"
                value={form.roleId}
                onChange={(e) => setForm((f) => ({ ...f, roleId: Number(e.target.value) }))}
              >
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={form.allStores}
                  onChange={(e) => setForm((f) => ({ ...f, allStores: e.target.checked }))}
                />
                Tất cả cửa hàng
              </label>
            </div>
            <div className="field">
              <label>Cửa hàng</label>
              <div className="stores-box" style={{ opacity: form.allStores ? 0.5 : 1 }}>
                {stores.map((s) => (
                  <label key={s.id}>
                    <input
                      type="checkbox"
                      disabled={form.allStores}
                      checked={form.storeIds.includes(s.id)}
                      onChange={(e) => toggleStore(s.id, e.target.checked)}
                    />
                    {s.code} — {s.name}
                  </label>
                ))}
              </div>
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
              <button type="submit" className="btn primary" disabled={save.isPending}>
                Lưu
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
