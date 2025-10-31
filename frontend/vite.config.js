import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import process from 'node:process';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_TARGET || 'http://backend:8000';

  // Build allowed hosts list
  const allowedHosts = ['localhost', '.localhost'];
  if (env.VITE_ALLOWED_HOST) {
    allowedHosts.push(env.VITE_ALLOWED_HOST);
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      allowedHosts,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          // Proxy /api/* to backend /api/* (no rewrite needed with versioning)
        },
        '/healthz': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/_debug': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
