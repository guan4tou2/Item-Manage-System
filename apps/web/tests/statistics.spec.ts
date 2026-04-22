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

test("statistics page shows three chart cards", async ({ page, request }) => {
  const u = `stat_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  await expect(page.getByRole("heading", { name: "依分類" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "依位置" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "熱門標籤" })).toBeVisible()
})

test("empty DB shows empty state in each chart", async ({ page, request }) => {
  const u = `stat2_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  await expect(page.getByText("尚無資料")).toHaveCount(3)
})
