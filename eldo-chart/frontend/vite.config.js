import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 1. Mở kết nối IP (Quan trọng cho Cloudflare/WSL)
    host: '0.0.0.0',
    
    // 2. Danh sách tên miền được phép truy cập (Chặn lỗi "Blocked request")
    allowedHosts: [
      'eldo.gegeteam.xyz',
      'localhost'
    ],

    // 3. Cấu hình Proxy (Cầu nối trung gian)
    proxy: {
      // --- Cấu hình cho API (HTTP) ---
      // Frontend gọi: axios.get('/api/history') 
      // -> Server nhận: http://localhost:8001/history
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        // Dòng rewrite này sẽ xóa chữ '/api' đi trước khi gửi sang server.
        // Nếu backend của bạn có sẵn tiền tố /api thì hãy xóa dòng rewrite này đi.
        rewrite: (path) => path.replace(/^\/api/, ''), 
      },

      // --- Cấu hình cho WebSocket (Real-time) ---
      // Frontend gọi: new WebSocket('.../ws')
      // -> Server nhận: ws://localhost:8001/ws
      '/ws': {
        target: 'ws://localhost:8001',
        ws: true, // Bắt buộc: Kích hoạt chế độ WebSocket
        changeOrigin: true,
        secure: false,
      },
    },
  },
})