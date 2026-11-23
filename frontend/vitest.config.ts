import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  envDir: false,
  test: {
    environment: 'jsdom',
    include: ['tests/components/*.test.tsx'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/utils/loginValidation.ts', 'src/utils/loginErrors.ts'],
      reportsDirectory: 'coverage/components',
      reporter: ['text', 'lcovonly'],
    },
  },
})
