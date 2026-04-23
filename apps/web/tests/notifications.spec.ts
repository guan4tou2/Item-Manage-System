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

test("new user sees welcome notification and unread badge", async ({ page, request }) => {
  const u = `notif_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await expect(page.getByTestId("notification-badge")).toHaveText("1")

  await page.getByRole("link", { name: "通知" }).first().click()
  await page.waitForURL("**/notifications")
  await expect(page.getByText("歡迎使用 IMS")).toBeVisible()
})

test("clicking a notification marks it read and navigates", async ({ page, request }) => {
  const u = `notif2_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/notifications")
  await page.getByRole("button", { name: /open notification/i }).first().click()
  await page.waitForURL("**/dashboard")
  await page.goto("/notifications")
  await expect(page.getByTestId("notification-badge")).toHaveCount(0)
})

test("mark all read empties unread tab", async ({ page, request }) => {
  const u = `notif3_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/notifications")
  await page.getByRole("button", { name: "全部標為已讀" }).click()
  await page.getByRole("tab", { name: "未讀" }).click()
  await expect(page.getByText("尚無通知")).toBeVisible()
})

test("low-stock notification appears after API update", async ({ page, request }) => {
  const u = `notif4_${unique()}`
  await register(request, u)
  const login = await request.post("/api/auth/login", {
    data: { username: u, password: "secret1234" },
  })
  const token = (await login.json()).access_token
  const item = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "便當盒", quantity: 5, min_quantity: 2 },
  })
  const itemId = (await item.json()).id
  await request.patch(`/api/items/${itemId}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { quantity: 1 },
  })

  await loginUi(page, u)
  await page.goto("/notifications")
  await expect(page.getByText(/庫存不足/)).toBeVisible()
})
