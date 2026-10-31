import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Builds into ../web, which the Python server serves. During development, `npm run dev`
// proxies API and live-update calls to the Python server on port 8000.
export default defineConfig({
  plugins: [react()],
  build: { outDir: '../web', emptyOutDir: true, chunkSizeWarningLimit: 900 },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000', '/ws': { target: 'ws://localhost:8000', ws: true } },
  },
});
