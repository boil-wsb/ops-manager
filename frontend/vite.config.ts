import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // 产物目录改名 static,避免与前端路由 /assets(资产管理)同名冲突:
    // F5 刷新 /assets 时 try_files 会命中同名目录导致 301→403
    assetsDir: 'static',
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
