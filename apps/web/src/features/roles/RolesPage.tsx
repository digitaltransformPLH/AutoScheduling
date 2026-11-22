import { useEffect, useMemo, useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { RoleDto } from '../../shared/api/types'
import * as rolesApi from './api'
import { RolePermissionGrid } from './RolePermissionGrid'

export function RolesPage() {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set())
  const [msg, setMsg] = useState('')

  const rolesQuery = useQuery({ queryKey: ['roles'], queryFn: rolesApi.listRoles })
  const permsQuery = useQuery({ queryKey: ['permissions'], queryFn: rolesApi.listPermissions })

  const roles = rolesQuery.data ?? []
  const permissions = permsQuery.data ?? []

  const selected: RoleDto | undefined = useMemo(
    () => roles.find((r) => r.id === selectedId),
    [roles, selectedId],
  )

  useEffect(() => {
    if (!selectedId && roles.length) setSelectedId(roles[0].id)
  }, [roles, selectedId])

  useEffect(() => {
    if (!selected) {
      setCheckedIds(new Set())
      return
    }
    setCheckedIds(new Set(selected.permissionIds ?? []))
  }, [selected?.id, selected?.permissionIds])

  const savePerms = useMutation({
    mutationFn: () =>
      rolesApi.setRolePermissions(selectedId!, { permissionIds: [...checkedIds] }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['roles'] })
      setMsg('Đã lưu quyền.')
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : 'Lỗi'),
  })

  const createRole = useMutation({
    mutationFn: (name: string) =>
      rolesApi.createRole({ name, description: '', permissionIds: [] }),
    onSuccess: async (created) => {
      await qc.invalidateQueries({ queryKey: ['roles'] })
      setSelectedId(created.id)
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : 'Lỗi'),
  })

  const cloneRole = useMutation({
    mutationFn: () => rolesApi.cloneRole(selectedId!),
    onSuccess: async (cloned) => {
      await qc.invalidateQueries({ queryKey: ['roles'] })
      setSelectedId(cloned.id)
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : 'Lỗi'),
  })

  const removeRole = useMutation({
    mutationFn: () => rolesApi.deleteRole(selectedId!),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['roles'] })
      setSelectedId(null)
      setMsg('Đã xóa role.')
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : 'Lỗi'),
  })

  const busy =
    savePerms.isPending ||
    createRole.isPending ||
    cloneRole.isPending ||
    removeRole.isPending

  return (
    <div className="pl-admin-shell">
      <div className="pl-admin-toolbar">
        <h3>Phân quyền</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            className="btn"
            disabled={!selectedId || busy}
            onClick={() => void cloneRole.mutate()}
          >
            Nhân bản
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={busy}
            onClick={() => {
              const name = window.prompt('Tên role mới?')
              if (name?.trim()) createRole.mutate(name.trim())
            }}
          >
            + Tạo role
          </button>
        </div>
      </div>

      {rolesQuery.isLoading || permsQuery.isLoading ? (
        <PageLoading />
      ) : (
        <div className="pl-roles-layout">
          <div className="pl-role-list">
            {roles.map((r) => (
              <button
                key={r.id}
                type="button"
                className={`pl-role-item${r.id === selectedId ? ' active' : ''}`}
                onClick={() => setSelectedId(r.id)}
              >
                <strong>{r.name}</strong>
                {r.isSystem && (
                  <span style={{ display: 'block', fontSize: 11, color: 'var(--muted)' }}>System</span>
                )}
              </button>
            ))}
          </div>

          <div className="pl-role-panel">
            <h3 style={{ marginTop: 0 }}>{selected?.name ?? 'Chọn role'}</h3>
            {selected?.description && (
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>{selected.description}</p>
            )}
            <RolePermissionGrid
              permissions={permissions}
              checkedIds={checkedIds}
              onToggle={(id, on) =>
                setCheckedIds((prev) => {
                  const next = new Set(prev)
                  if (on) next.add(id)
                  else next.delete(id)
                  return next
                })
              }
              onSelectAll={() => setCheckedIds(new Set(permissions.map((p) => p.id)))}
              onClearAll={() => setCheckedIds(new Set())}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn primary"
                disabled={!selectedId || busy}
                onClick={() => void savePerms.mutate()}
              >
                Lưu quyền
              </button>
              <button
                type="button"
                className="btn danger"
                disabled={!selectedId || busy || selected?.isSystem}
                onClick={() => {
                  if (!selected || selected.isSystem) return
                  if (window.confirm(`Xóa role "${selected.name}"?`)) removeRole.mutate()
                }}
              >
                Xóa role
              </button>
            </div>
            {msg && (
              <p style={{ color: msg.startsWith('Đã') ? 'var(--green)' : 'var(--red)' }}>{msg}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
