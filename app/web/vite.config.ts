import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

const apiProxy=process.env.SE2026_API_PROXY || 'http://127.0.0.1:8000'
if(!['127.0.0.1','localhost','[::1]'].includes(new URL(apiProxy).hostname))throw new Error('API proxy must remain local')
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {alias: {'@': fileURLToPath(new URL('./src', import.meta.url))}},
  server: {host: '127.0.0.1', port: 5173, strictPort: true, proxy: {'/api': {target: apiProxy, changeOrigin: true}},
    headers: {'Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'}},
  build: {sourcemap: false, rolldownOptions:{output:{codeSplitting:{groups:[{name:'charts',test:/node_modules[\\/](echarts|zrender)[\\/]/},{name:'framework',test:/node_modules[\\/](react|react-dom|@tanstack)[\\/]/}]}}}},
})
