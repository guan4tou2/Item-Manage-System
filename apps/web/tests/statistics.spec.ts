import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: "secret1234" },
  })
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("statistics page shows chart cards", async ({ page, request }) => {
  const u = `stat_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  // 圖表卡片標題（CardTitle 為 div，非 heading 語意）
  await expect(page.getByText("依分類", { exact: true })).toBeVisible()
  await expect(page.getByText("依位置", { exact: true })).toBeVisible()
  await expect(page.getByText("熱門標籤", { exact: true })).toBeVisible()
})

test("empty DB shows empty state in each chart", async ({ page, request }) => {
  const u = `stat2_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  // 五張圖表（趨勢／分類／位置／倉庫／標籤）皆顯示空狀態
  await expect(page.getByText("尚無資料", { exact: true })).toHaveCount(5)
})
