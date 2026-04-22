import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("logout clears auth cookie and redirects to /login", async ({ page, request }) => {
  const suffix = unique()
  const username = `out_${suffix}`
  const email = `out_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.getByRole("button", { name: /使用者選單/ }).click()
  await page.getByRole("menuitem", { name: /登出/ }).click()

  await page.waitForURL("**/login")

  // 直接再進 /dashboard 應又被踢回 /login
  await page.goto("/dashboard")
  await page.waitForURL("**/login")
})
