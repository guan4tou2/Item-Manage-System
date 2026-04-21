import { defineConfig } from "vitest/config"

export default defineConfig({
  test: {
    // Playwright E2E specs live in tests/ — exclude them from Vitest
    exclude: ["tests/**", "node_modules/**"],
  },
})
