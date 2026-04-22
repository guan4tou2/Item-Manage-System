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
  await page.getByText("物品").click()
  await page.waitForURL("**/items")
  // drawer 應已關閉（sheet content 不可見）
  await expect(page.getByRole("dialog")).toHaveCount(0)
})
