import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
        timeout: 120000, // LSTM训练可能需要较长时间，代理超时设为120秒
      }
    }
  }
})
