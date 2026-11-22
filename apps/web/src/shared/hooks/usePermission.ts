import { useAuth } from '../../features/auth/AuthContext'

export function usePermission(code: string) {
  const { hasPermission } = useAuth()
  return hasPermission(code)
}
