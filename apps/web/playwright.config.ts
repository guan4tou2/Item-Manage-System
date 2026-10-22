import { defineConfig, devices, type Project } from '@playwright/test'

/**
 * Phase 35：AI stub 模式（`AI_MODE=stub`）讓 AI 成功路徑可進 e2e。
 *
 * - `chromium`（預設）：live／無 key 的 fallback 路徑（既有 spec）
 * - `ai-stub`：AI 成功路徑（收據品項／搜尋 chip／問答引用／批次入庫）
 *   需 `E2E_AI_STUB=1` 才註冊（避免一般 run 出現整組 skip 噪音），
 *   且 API 須以 `AI_MODE=stub` 啟動；spec 內部另以 `/api/ai/status` 自我防護。
 */
const projects: Project[] = [
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'] },
    // AI stub 專用情境只在 ai-stub 專案執行
    testIgnore: /ai-stub\.spec\.ts/,
  },
]

if (process.env.E2E_AI_STUB === '1') {
  projects.push({
    name: 'ai-stub',
    use: { ...devices['Desktop Chrome'] },
    testMatch: /ai-stub\.spec\.ts/,
  })
}

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost',
    trace: 'retain-on-failure',
    // Playwright Test 預設注入 locale en-US（Accept-Language en-US），
    // 會讓 app 以英文渲染，spec 的中文標籤全部失效；固定 zh-TW 對齊 app 預設語系。
    locale: 'zh-TW',
  },
  projects,
})
