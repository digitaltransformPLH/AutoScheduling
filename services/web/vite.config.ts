import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'demo' ? './' : '/',
  server: { port: 5173, proxy: { '/api': { target: process.env.SCHED_API_URL ?? 'http://127.0.0.1:8010', changeOrigin: true } } },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: { output: { manualChunks: { antd: ['antd', '@ant-design/icons'], charts: ['echarts', 'echarts-for-react'] } } },
  },
}))
