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

test("non-admin：管理群組隱藏、admin 子頁顯示僅限管理員空態", async ({ page, request }) => {
  const u = `set_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  await page.goto("/settings")
  await expect(page.getByText("個人", { exact: true })).toBeVisible()
  await expect(page.getByText("通知與提醒", { exact: true })).toBeVisible()
  await expect(page.getByText("整合與資料", { exact: true })).toBeVisible()
  await expect(page.getByText("管理", { exact: true })).toHaveCount(0)
  await expect(page.getByText("系統尚無管理員。")).toBeVisible()

  // 直接 URL 訪問 admin 子頁 → 空態（不 redirect）
  await page.goto("/settings/members")
  await expect(page.getByText("此頁僅限管理員檢視。")).toBeVisible()
  await expect(page).toHaveURL(/\/settings\/members$/)
})

test("bootstrap 後管理群組出現；環境已有 admin 時維持隱藏（依 API 分支）", async ({ page, request }) => {
  const u = `set2_${unique()}`
  await register(request, u)
  const login = await request.post("/api/auth/login", {
    data: { username: u, password: "secret1234" },
  })
  const token = (await login.json()).access_token as string
  const boot = await request.post("/api/auth/bootstrap-admin", {
    headers: { Authorization: `Bearer ${token}` },
  })
  const becameAdmin = boot.status() === 200

  await loginUi(page, u)
  await page.goto("/settings")

  if (becameAdmin) {
    await expect(page.getByText("管理", { exact: true })).toBeVisible()
    await expect(page.getByText("系統尚無管理員。")).toHaveCount(0)
    await page.getByRole("link", { name: /成員管理/ }).click()
    await page.waitForURL("**/settings/members")
    await expect(page.getByRole("heading", { name: "成員管理" })).toBeVisible()
  } else {
    await expect(page.getByText("管理", { exact: true })).toHaveCount(0)
    await expect(page.getByText("系統尚無管理員。")).toBeVisible()
  }
})
