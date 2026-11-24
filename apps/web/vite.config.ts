import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Production HTML references ./assets/… so a virtual directory (for example
  // /auto-scheduling) works. The API injects <base href> from the IIS path.
  base: command === 'build' ? './' : '/',
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
}))
