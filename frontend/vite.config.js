import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  server: {
    port: 3000,
    open: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/api/v1/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [
    // 使用默认 include 以兼容带查询参数的模块 id（避免 /src/*.jsx?t=xxxx 不匹配）
    react({ jsxRuntime: 'automatic' }),
  ],
});
