import { ConfigProvider } from 'antd'
import type { ReactNode } from 'react'
import { antdTheme } from './theme/tokens'
import './scheduling.css'

export function SchedulingShell({ children }: { children: ReactNode }) {
  return (
    <ConfigProvider theme={antdTheme}>
      <div className="scheduling-root">{children}</div>
    </ConfigProvider>
  )
}