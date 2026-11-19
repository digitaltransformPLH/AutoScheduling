import { LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Layout, Menu, Result, Spin, Tag, Tooltip } from 'antd'
import { useEffect, useState } from 'react'
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import type { Me } from './api/client'
import { AUTH_EVENT } from './api/client'
import { useLogout, useMe, useMeta } from './api/hooks'
import { InputsPage } from './pages/InputsPage'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { RosterPage } from './pages/RosterPage'
import { RunsPage } from './pages/RunsPage'

const NAV = [
  { key: '/', label: 'Tổng quan', perm: 'scheduleView', el: <OverviewPage /> },
  { key: '/roster', label: 'Roster tuần', perm: 'scheduleView', el: <RosterPage /> },
  { key: '/inputs', label: 'Dữ liệu đầu vào', perm: 'inputView', el: <InputsPage /> },
  { key: '/runs', label: 'Lịch sử chạy', perm: 'scheduleView', el: <RunsPage /> },
]

const Denied = () => <Result status="403" title="Không có quyền" subTitle="Tài khoản của bạn chưa được cấp quyền xem trang này. Liên hệ quản trị Workforce Planning." />

function Shell({ me }: { me: Me }) {
  const nav = useNavigate()
  const loc = useLocation()
  const meta = useMeta()
  const logout = useLogout()
  const items = NAV.filter((n) => me.can[n.perm])
  const home = items[0]
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header className="app-header">
        <div className="brand">PHÚC LONG<small>Auto Scheduling</small></div>
        <Menu theme="dark" mode="horizontal" selectedKeys={[loc.pathname]} items={items.map(({ key, label }) => ({ key, label }))}
          onClick={(e) => nav({ pathname: e.key, search: loc.search })} />
        <div className="header-right">
          {meta.data?.backTest && <Tag color="#9A3F22" style={{ marginInlineEnd: 0 }}>DEMO · back-test</Tag>}
          <Tooltip title={meta.data?.builtAt ? `Cập nhật lúc ${meta.data.builtAt}` : ''}>
            <span>dữ liệu v{meta.data?.dataVersion ?? '…'}</span>
          </Tooltip>
          <Tooltip title={`${me.email} · ${me.allStores ? 'tất cả cửa hàng' : `${me.stores.length} cửa hàng`}`}>
            <span className="user-chip"><UserOutlined /> {me.displayName} <small>{me.role}</small></span>
          </Tooltip>
          <Tooltip title="Đăng xuất">
            <Button size="small" type="text" className="logout-btn" icon={<LogoutOutlined />} loading={logout.isPending}
              onClick={() => logout.mutate()} />
          </Tooltip>
        </div>
      </Layout.Header>
      <Layout.Content>
        {items.length === 0 ? <Denied /> : (
          <Routes>
            {NAV.map((n) => <Route key={n.key} path={n.key} element={me.can[n.perm] ? n.el : <Denied />} />)}
            <Route path="*" element={home.el} />
          </Routes>
        )}
      </Layout.Content>
    </Layout>
  )
}

export function App() {
  const me = useMe()
  const qc = useQueryClient()
  const [expired, setExpired] = useState(false)
  useEffect(() => {
    // any 401 from the API (session expired, user deactivated in .NET) -> back to the login screen
    const onUnauthorized = () => {
      if (qc.getQueryData(['auth', 'me'])) setExpired(true)
      qc.setQueryData(['auth', 'me'], null)
    }
    window.addEventListener(AUTH_EVENT, onUnauthorized)
    return () => window.removeEventListener(AUTH_EVENT, onUnauthorized)
  }, [qc])

  if (me.isLoading) return <div className="login-wrap"><Spin size="large" /></div>
  const status = (me.error as { status?: number } | null)?.status
  if (me.error && status !== 401) {
    return <Result status="500" title="Không kết nối được máy chủ" subTitle={(me.error as Error).message}
      extra={<Button onClick={() => me.refetch()}>Thử lại</Button>} />
  }
  if (!me.data) return <LoginPage expired={expired} />
  return <Shell me={me.data} />
}
