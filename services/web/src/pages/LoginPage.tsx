// Login with the Workforce Planning (.NET) account: same email / password, same roles and store assignments.
import { LockOutlined, MailOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Input } from 'antd'
import { useLogin } from '../api/hooks'
import logo from '../assets/pl-logo.jpg'

export function LoginPage({ expired = false }: { expired?: boolean }) {
  const login = useLogin()
  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-brand">
          <img src={logo} alt="Phúc Long" className="login-logo" />
          <div>PHÚC LONG<small>Auto Scheduling</small></div>
        </div>
        <h1 className="action-title" style={{ fontSize: 20, marginBottom: 18 }}>Đăng nhập</h1>
        {expired && !login.error && <Alert type="info" showIcon style={{ marginBottom: 12 }} message="Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại." />}
        {login.error && <Alert type="error" showIcon style={{ marginBottom: 12 }} message={(login.error as Error).message} />}
        <Form layout="vertical" requiredMark={false} onFinish={(v: { email: string; password: string }) => login.mutate(v)}>
          <Form.Item name="email" label="Email" rules={[{ required: true, message: 'Nhập email' }]}>
            <Input prefix={<MailOutlined />} autoComplete="username" autoFocus placeholder="ten@phuclong.com.vn" />
          </Form.Item>
          <Form.Item name="password" label="Mật khẩu" rules={[{ required: true, message: 'Nhập mật khẩu' }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={login.isPending}>Đăng nhập</Button>
        </Form>
      </div>
    </div>
  )
}
