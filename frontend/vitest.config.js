import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, 'src'),
    },
  },
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    include: ['test-runtime/**/*.test.js'],
  },
})
