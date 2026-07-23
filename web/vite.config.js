import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 프론트(5173)에서 /consult, /health 호출을 백엔드(8000)로 프록시 → CORS 신경 안 씀
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/consult': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    },
  },
})
