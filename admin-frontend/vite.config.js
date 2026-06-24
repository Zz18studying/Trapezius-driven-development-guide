import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
   base: '/admin/',
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // ========== 添加以下 server 配置 ==========
  server: {
    host: '0.0.0.0',           // 允许局域网访问
    port: 5173,                 // 端口
    proxy: {
      '/api': {
       target: 'http://110.42.246.141:8000',  // 后端 API 地址
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')  // 保持路径不变
      }
    }
  }
})