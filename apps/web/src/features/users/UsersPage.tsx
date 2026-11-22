import { useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery } from '@tanstack/react-query'
import { listRoles } from '../roles/api'
import { listStoresSimple } from '../stores/api'
import { useUsers, useUserMutations } from './hooks'
import { UserFormModal } from './UserFormModal'

export function UsersPage() {
  const usersQuery = useUsers()
  const { deactivate } = useUserMutations()
  const rolesQuery = useQuery({ queryKey: ['roles'], queryFn: listRoles })
  const storesQuery = useQuery({ queryKey: ['stores', 'simple'], queryFn: listStoresSimple })

  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  const users = usersQuery.data ?? []
  const roles = rolesQuery.data ?? []
  const stores = storesQuery.data ?? []

  async function onDeactivate(id: number, name: string) {
    if (!window.confirm(`Vô hiệu hóa user "${name}"?`)) return
    try {
      await deactivate.mutateAsync(id)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Lỗi')
    }
  }

  return (
    <>
      <p style={{ margin: '0 0 12px', color: 'var(--muted)' }}>
        Tạo và gán role / cửa hàng cho tài khoản
      </p>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Quản lý người dùng</h3>
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setEditingId(null)
              setModalOpen(true)
            }}
          >
            + Thêm người dùng
          </button>
        </div>
        <div className="pl-admin-card">
          {usersQuery.isLoading && <PageLoading compact />}
          {usersQuery.isError && (
            <div className="empty-state" style={{ color: 'var(--red)' }}>
              {(usersQuery.error as Error).message}
            </div>
          )}
          {!usersQuery.isLoading && !usersQuery.isError && (
            <table className="pl-admin-table">
              <thead>
                <tr>
                  <th>Tên</th>
                  <th>Email</th>
                  <th>Vai trò</th>
                  <th>Cửa hàng</th>
                  <th>Trạng thái</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={6}>Chưa có user</td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const storeLabel = u.allStores
                      ? 'Tất cả cửa hàng'
                      : (u.stores ?? []).map((s) => s.code).join(', ') || '—'
                    return (
                      <tr key={u.id}>
                        <td>{u.displayName}</td>
                        <td>{u.email}</td>
                        <td>{u.roleName}</td>
                        <td>{storeLabel}</td>
                        <td>
                          <span className={`pill ${u.isActive ? 'on' : 'off'}`}>
                            {u.isActive ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <button
                            type="button"
                            className="btn link"
                            onClick={() => {
                              setEditingId(u.id)
                              setModalOpen(true)
                            }}
                          >
                            Sửa
                          </button>
                          {u.isActive && (
                            <>
                              {' · '}
                              <button
                                type="button"
                                className="btn link danger"
                                onClick={() => void onDeactivate(u.id, u.displayName)}
                              >
                                Vô hiệu hóa
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <UserFormModal
        open={modalOpen}
        userId={editingId}
        roles={roles}
        stores={stores}
        onClose={() => setModalOpen(false)}
      />
    </>
  )
}
