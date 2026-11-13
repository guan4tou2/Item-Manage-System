import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
}

async function loginUi(page: import("@playwright/test").Page, username: string, password = PASSWORD) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

/** 從 zustand persist 的 localStorage 取出目前的 access token。 */
async function storedToken(page: import("@playwright/test").Page): Promise<string> {
  return page.evaluate(() => JSON.parse(localStorage.getItem("ims-auth") ?? "{}").state.accessToken as string)
}

test("改密碼後仍保持登入，可繼續操作，且舊 token 失效", async ({ page, request }) => {
  const u = `pw_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  const oldToken = await storedToken(page)

  await page.goto("/settings/password")
  await page.getByLabel("目前密碼").fill(PASSWORD)
  await page.getByLabel("新密碼", { exact: true }).fill("newsecret5678")
  await page.getByLabel("再次輸入新密碼").fill("newsecret5678")
  await page.getByRole("button", { name: "變更密碼" }).click()
  await expect(page.getByText("密碼已更新")).toBeVisible()
  await expect(page.getByText("其他裝置已登出")).toBeVisible()

  // store 內的 token 已換成後端重新簽發的新 token
  await expect.poll(() => storedToken(page)).not.toBe(oldToken)

  // 仍在登入狀態：重新整理與換頁都不會被踢回登入頁
  await page.goto("/dashboard")
  await expect(page).toHaveURL(/\/dashboard/)
  await page.goto("/settings/profile")
  await expect(page).toHaveURL(/\/settings\/profile/)

  // 舊 token 已失效，新 token 可用
  const stale = await request.get("/api/users/me", { headers: { Authorization: `Bearer ${oldToken}` } })
  expect(stale.status()).toBe(401)
  const fresh = await request.get("/api/users/me", { headers: { Authorization: `Bearer ${await storedToken(page)}` } })
  expect(fresh.status()).toBe(200)
})

test("登出所有裝置：導回登入頁，舊 token 打 API 回 401", async ({ page, request }) => {
  const u = `lo_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  const token = await storedToken(page)

  await page.goto("/settings/password")
  await page.getByRole("button", { name: "登出所有裝置" }).click()
  // AlertDialog 確認
  await page.getByRole("alertdialog").getByRole("button", { name: "登出" }).click()
  await page.waitForURL("**/login")

  const stale = await request.get("/api/users/me", { headers: { Authorization: `Bearer ${token}` } })
  expect(stale.status()).toBe(401)

  // 再進受保護頁面仍被導回登入頁
  await page.goto("/dashboard")
  await page.waitForURL("**/login")
})
