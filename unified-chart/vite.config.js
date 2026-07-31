import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5176,
    allowedHosts: [
      'localhost',
      'gegechart.xyz',
      'dashboard.gegechart.xyz',
      '.gegechart.xyz'
    ]
  }
})
