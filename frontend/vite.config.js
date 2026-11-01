import { defineConfig } from 'vite';

// Sem plugins: o esbuild do próprio Vite compila o JSX (runtime automático do React).
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8010';

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  css: { modules: { localsConvention: 'camelCase' } },
  server: {
    port: 5173,
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
    watch: { usePolling: !!process.env.VITE_POLLING },
  },
});
