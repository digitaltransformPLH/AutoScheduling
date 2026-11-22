import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ApiError } from '../../shared/api/http'
import * as authApi from './api'
import type { LoginRequest, MeResponse } from '../../shared/api/types'

type AuthState = {
  me: MeResponse | null
  loading: boolean
  refresh: () => Promise<void>
  login: (body: LoginRequest) => Promise<MeResponse>
  logout: () => Promise<void>
  hasPermission: (code: string) => boolean
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await authApi.getMe()
      setMe(data)
    } catch (e) {
      setMe(null)
      if (!(e instanceof ApiError && e.status === 401)) {
        console.error(e)
      }
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const data = await authApi.getMe()
        if (!cancelled) setMe(data)
      } catch {
        if (!cancelled) setMe(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (body: LoginRequest) => {
    const data = await authApi.login(body)
    setMe(data)
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setMe(null)
    }
  }, [])

  const hasPermission = useCallback(
    (code: string) => {
      const perms = me?.permissions ?? []
      return perms.some((p) => p.toLowerCase() === code.toLowerCase())
    },
    [me],
  )

  const value = useMemo(
    () => ({ me, loading, refresh, login, logout, hasPermission }),
    [me, loading, refresh, login, logout, hasPermission],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
