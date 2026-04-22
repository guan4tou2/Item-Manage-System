import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("register via API then login via UI lands on /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `e2e_${suffix}`
  const email = `e2e_${suffix}@example.com`
  const password = "secret1234"

  const reg = await request.post("/api/auth/register", {
    data: { email, username, password },
  })
  expect(reg.status()).toBe(201)

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()

  await page.waitForURL("**/dashboard")
  await expect(page.getByRole("heading", { name: "儀表板" })).toBeVisible()
})

test("wrong password shows error", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill("does-not-exist")
  await page.getByLabel("密碼").fill("wrong-pass")
  await page.getByRole("button", { name: /登入/ }).click()

  await expect(page.getByRole("alert")).toHaveText("帳號或密碼錯誤")
})
