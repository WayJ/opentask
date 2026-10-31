import { resolve } from 'node:path';
import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'e2e'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/types/',
        'src/typings/',
        'src/main.ts',
        'src/**/*.d.ts',
        '**/*.test.ts',
        '**/*.spec.ts',
        'src/router/'
      ],
      // 设置覆盖率目标为 70%
      lines: 70,
      functions: 70,
      branches: 70,
      statements: 70
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
});
