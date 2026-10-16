import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("anon user accessing /dashboard redirects to /login", async ({ page }) => {
  await page.goto("/dashboard")
  await page.waitForURL("**/login")
  expect(page.url()).toContain("/login")
})

test("anon user accessing /items redirects to /login", async ({ page }) => {
  await page.goto("/items")
  await page.waitForURL("**/login")
  expect(page.url()).toContain("/login")
})

test("after login, landing / redirects to /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `nav_${suffix}`
  const email = `nav_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // 訪問 / 應自動 redirect 到 /dashboard
  await page.goto("/")
  await page.waitForURL("**/dashboard")
  expect(page.url()).toContain("/dashboard")
})

test("logged-in user visiting /login bounces to /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `nav2_${suffix}`
  const email = `nav2_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.goto("/login")
  await page.waitForURL("**/dashboard")
})

test("mobile viewport: drawer opens and nav works", async ({ page, request }) => {
  const suffix = unique()
  const username = `mob_${suffix}`
  const email = `mob_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.getByRole("button", { name: /開啟選單/ }).click()
  await page.getByRole("dialog").getByRole("button", { name: "物品", exact: true }).click()
  await page.waitForURL("**/items")
  // drawer 應已關閉（sheet content 不可見）
  await expect(page.getByRole("dialog")).toHaveCount(0)
})

test("settings 索引頁與子路由可達性抽查", async ({ page, request }) => {
  const suffix = unique()
  const username = `setnav_${suffix}`
  const email = `setnav_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", { data: { email, username, password } })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // 索引頁：群組卡（新註冊一律非 admin，管理群組隱藏）
  await page.goto("/settings")
  await expect(page.getByText("個人", { exact: true })).toBeVisible()
  await expect(page.getByText("通知與提醒", { exact: true })).toBeVisible()
  await expect(page.getByText("整合與資料", { exact: true })).toBeVisible()

  // 子路由 1：個人資料
  await page.getByRole("link", { name: /個人資料/ }).click()
  await page.waitForURL("**/settings/profile")
  await expect(page.getByRole("heading", { name: "個人資料" })).toBeVisible()

  // 子路由 2：通知管道
  await page.goto("/settings")
  await page.getByRole("link", { name: /通知管道/ }).click()
  await page.waitForURL("**/settings/channels")
  await expect(page.getByRole("heading", { name: "通知管道" })).toBeVisible()

  // 子路由 3：taxonomy（既有頁面經索引卡可達）
  await page.goto("/settings")
  await page.getByRole("link", { name: /分類／位置／標籤/ }).click()
  await page.waitForURL("**/settings/taxonomy")
  await expect(page.getByRole("heading", { name: "分類與位置" })).toBeVisible()
})
