import type { PermissionDto } from '../../shared/api/types'

type Props = {
  permissions: PermissionDto[]
  checkedIds: Set<number>
  onToggle: (id: number, on: boolean) => void
  onSelectAll: () => void
  onClearAll: () => void
}

export function RolePermissionGrid({
  permissions,
  checkedIds,
  onToggle,
  onSelectAll,
  onClearAll,
}: Props) {
  return (
    <>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <button type="button" className="btn" onClick={onSelectAll}>
          Select all
        </button>
        <button type="button" className="btn" onClick={onClearAll}>
          Clear all
        </button>
      </div>
      <div className="pl-perm-grid">
        {permissions.map((p) => (
          <label key={p.id}>
            <input
              type="checkbox"
              checked={checkedIds.has(p.id)}
              onChange={(e) => onToggle(p.id, e.target.checked)}
            />
            <span>
              <strong>{p.name}</strong>
              <br />
              <small style={{ color: 'var(--muted)' }}>{p.code}</small>
            </span>
          </label>
        ))}
      </div>
    </>
  )
}
