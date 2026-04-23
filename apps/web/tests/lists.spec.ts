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

test("create list, add entries, toggle, delete entry", async ({ page, request }) => {
  const u = `lst_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  await page.goto("/lists")
  await expect(page.getByText("尚無清單")).toBeVisible()

  await page.getByRole("button", { name: "新增清單" }).click()
  await page.getByLabel("清單名稱…").fill("週末露營")
  await page.getByRole("button", { name: "建立" }).click()

  await page.waitForURL(/\/lists\/[^/]+/)
  await expect(page.getByRole("heading", { name: "週末露營" })).toBeVisible()

  await page.getByPlaceholder("輸入項目名稱，按 Enter 新增").fill("帳篷")
  await page.getByRole("button", { name: "建立" }).click()
  await page.getByPlaceholder("輸入項目名稱，按 Enter 新增").fill("睡袋")
  await page.getByRole("button", { name: "建立" }).click()

  await expect(page.getByText("帳篷")).toBeVisible()
  await expect(page.getByText("睡袋")).toBeVisible()

  await page.getByRole("checkbox", { name: "帳篷" }).click()
  await expect(page.getByText(/2 項 · 1 已完成/)).toBeVisible()

  const row = page.getByText("睡袋").locator("..").locator("..")
  await row.getByRole("button", { name: "刪除" }).click()
  await expect(page.getByText("睡袋")).toHaveCount(0)
})

test("delete list navigates back to index", async ({ page, request }) => {
  const u = `lst2_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  await page.goto("/lists")
  await page.getByRole("button", { name: "新增清單" }).click()
  await page.getByLabel("清單名稱…").fill("丟掉我")
  await page.getByRole("button", { name: "建立" }).click()

  await page.getByRole("button", { name: "刪除清單" }).click()
  await page.getByRole("button", { name: "刪除清單" }).click()
  await page.waitForURL("**/lists")
  await expect(page.getByText("丟掉我")).toHaveCount(0)
})
