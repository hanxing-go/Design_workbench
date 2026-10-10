import { defineConfig } from 'vite';
export default defineConfig({
  build: {
    outDir: '../src/design_workbench/static',
    emptyOutDir: true,
    rollupOptions: { input: { main: 'index.html', capture: 'capture.html' } },
  },
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
});
