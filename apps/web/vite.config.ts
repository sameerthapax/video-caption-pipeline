import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: __dirname,
  plugins: [react()],
  resolve: {
    alias: {
      '@shared-types': resolve(__dirname, '../../libs/shared-types/src/index.ts')
    }
  },
  build: {
    outDir: resolve(__dirname, '../../dist/apps/web'),
    emptyOutDir: true
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts'
  }
});
