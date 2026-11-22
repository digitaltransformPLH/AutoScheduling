import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { PageLoading } from '../../shared/components/PageLoading'
import { useAuth } from './AuthContext'
import { defaultAdminPath } from './routing'

export function LoginPage() {
  const { me, loading, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const returnParam = new URLSearchParams(location.search).get('return')
  const from =
    returnParam ||
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="login-page">
        <PageLoading />
      </div>
    )
  }

  if (me) {
    const target = from && from !== '/login' ? from : defaultAdminPath(me)
    return <Navigate to={target} replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    setSubmitting(true)
    try {
      const loggedIn = await login({ email: email.trim(), password })
      const target = from && from !== '/login' ? from : defaultAdminPath(loggedIn)
      navigate(target, { replace: true })
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Đăng nhập thất bại')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>Đăng nhập</h1>
        <p className="sub">Phúc Long — Quản trị hệ thống</p>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="admin@phuclong.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="btn primary" style={{ width: '100%' }} disabled={submitting}>
          {submitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
        <div className="err">{err}</div>
      </form>
    </div>
  )
}
