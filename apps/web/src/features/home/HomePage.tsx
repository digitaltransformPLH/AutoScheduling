import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { defaultAdminPath } from '../auth/routing'

export function HomePage() {
  const { me } = useAuth()
  if (!me) return null

  const adminPath = defaultAdminPath(me)
  if (adminPath !== '/home') {
    return <Navigate to={adminPath} replace />
  }

  return (
    <div className="pl-admin-shell">
      <div className="pl-admin-card" style={{ padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>Chào {me.displayName || me.email}</h3>
        <p style={{ color: 'var(--muted)' }}>
          Dùng menu bên trái để mở các chức năng theo quyền của bạn. Liên hệ administrator nếu thiếu quyền.
        </p>
      </div>
    </div>
  )
}