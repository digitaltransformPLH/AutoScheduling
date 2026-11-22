import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PageLoading } from '../../shared/components/PageLoading'
import { useAuth } from './AuthContext'

export function ProtectedRoute() {
  const { me, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <PageLoading />
  }

  if (!me) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
