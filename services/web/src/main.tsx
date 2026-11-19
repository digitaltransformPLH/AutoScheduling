import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import './styles.css'
import { antdTheme } from './theme/tokens'

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 10 * 60_000, retry: 1, refetchOnWindowFocus: false } } })
const router = createBrowserRouter([{ path: '*', element: <App /> }], { future: { v7_relativeSplatPath: true } })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={antdTheme} locale={viVN}>
        <AntApp>
          <RouterProvider router={router} future={{ v7_startTransition: true }} />
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
