import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function RequirePermission({
  permission,
  children,
}: {
  permission: string
  children: React.ReactNode
}) {
  const { me } = useAuth()
  if (!me) return null
  const ok = me.permissions.some((p) => p.toLowerCase() === permission.toLowerCase())
  if (!ok) return <Navigate to="/" replace />
  return <>{children}</>
}

export function RequireAnyPermission({
  permissions,
  children,
}: {
  permissions: string[]
  children: React.ReactNode
}) {
  const { me } = useAuth()
  if (!me) return null
  const ok = permissions.some((perm) =>
    me.permissions.some((p) => p.toLowerCase() === perm.toLowerCase()),
  )
  if (!ok) return <Navigate to="/" replace />
  return <>{children}</>
}
