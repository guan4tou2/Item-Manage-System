import { defineConfig, devices } from '@playwright/test'

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
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
