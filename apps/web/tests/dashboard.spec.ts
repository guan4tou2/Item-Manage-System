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

test("landing redirects to dashboard when logged in", async ({ page, request }) => {
  const u = `dash_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/")
  await page.waitForURL("**/dashboard")
  await expect(page.getByRole("heading", { name: "儀表板" })).toBeVisible()
})

test("dashboard shows stat cards and recent items", async ({ page, request }) => {
  const u = `dash2_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  await expect(page.getByRole("group", { name: "物品" })).toBeVisible()
  await expect(page.getByText("尚無物品")).toBeVisible()

  const login = await request.post("/api/auth/login", {
    data: { username: u, password: "secret1234" },
  })
  const token = login.json ? (await login.json()).access_token : ""
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "測試物品", quantity: 3 },
  })

  await page.reload()
  await expect(page.getByText("測試物品")).toBeVisible()
})

test("view all on recent card navigates to items", async ({ page, request }) => {
  const u = `dash3_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.getByRole("link", { name: "查看全部" }).click()
  await page.waitForURL("**/items")
})
