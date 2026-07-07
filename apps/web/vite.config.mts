import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const currentDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: currentDir,
  plugins: [react()],
  resolve: {
    alias: {
      '@shared-types': resolve(currentDir, '../../libs/shared-types/src/index.ts')
    }
  },
  build: {
    outDir: resolve(currentDir, '../../dist/apps/web'),
    emptyOutDir: true
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts'
  }
});
