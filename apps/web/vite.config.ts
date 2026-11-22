import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ['antd', '@ant-design/icons', 'echarts', 'echarts-for-react', 'dayjs'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5224',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../api/wwwroot',
    emptyOutDir: true,
  },
})
