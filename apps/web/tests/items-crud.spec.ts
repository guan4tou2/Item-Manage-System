import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  const email = `${username}@t.io`
  const password = "secret1234"
  const reg = await request.post("/api/auth/register", { data: { email, username, password } })
  expect(reg.status()).toBe(201)
  return { username, password }
}

async function loginUi(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("items full CRUD lifecycle", async ({ page, request }) => {
  const u = `crud_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  await page.goto("/items")
  await expect(page.getByText("還沒有任何物品")).toBeVisible()

  await page.getByRole("link", { name: "新增物品" }).first().click()
  await page.waitForURL("**/items/new")
  await page.getByLabel("名稱").fill("燈泡")
  await page.getByLabel("描述").fill("臥室用")
  await page.getByLabel("數量").fill("3")

  const tagInput = page.getByPlaceholder("輸入後按 Enter 新增")
  await tagInput.fill("家電")
  await tagInput.press("Enter")
  await tagInput.fill("備品")
  await tagInput.press("Enter")

  await page.getByRole("button", { name: /^儲存$/ }).click()
  await expect(page.getByRole("heading", { name: "燈泡" })).toBeVisible()

  await page.goto("/items")
  await expect(page.getByRole("link", { name: "燈泡" })).toBeVisible()

  await page.getByPlaceholder("搜尋物品名稱或描述…").fill("燈")
  await expect(page.getByRole("link", { name: "燈泡" })).toBeVisible()

  await page.getByRole("link", { name: "燈泡" }).click()
  await page.getByRole("link", { name: "編輯" }).click()
  await page.getByLabel("名稱").fill("LED 燈泡")
  await page.getByRole("button", { name: /^儲存$/ }).click()
  await expect(page.getByRole("heading", { name: "LED 燈泡" })).toBeVisible()

  await page.getByRole("button", { name: "刪除" }).first().click()
  await page.getByRole("button", { name: "刪除" }).nth(1).click()
  await page.waitForURL("**/items")
  await expect(page.getByText("還沒有任何物品")).toBeVisible()
})

test("filtering by tag narrows results", async ({ page, request }) => {
  const u = `filter_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  for (const [name, tag] of [["筆記本", "文具"], ["筆", "文具"], ["杯子", "廚具"]] as const) {
    await page.goto("/items/new")
    await page.getByLabel("名稱").fill(name)
    const tagInput = page.getByPlaceholder("輸入後按 Enter 新增")
    await tagInput.fill(tag)
    await tagInput.press("Enter")
    await page.getByRole("button", { name: /^儲存$/ }).click()
    await page.waitForURL("**/items/**")
  }

  await page.goto("/items")
  await page.getByRole("button", { name: "廚具" }).click()
  await expect(page.getByRole("link", { name: "杯子" })).toBeVisible()
  await expect(page.getByRole("link", { name: "筆" })).toHaveCount(0)
})

test("cannot view another user's item", async ({ page, request }) => {
  const a = `a_${unique()}`
  const b = `b_${unique()}`
  const creds_a = await register(request, a)
  const creds_b = await register(request, b)

  const loginRes = await request.post("/api/auth/login", {
    data: { username: creds_a.username, password: creds_a.password },
  })
  const token = (await loginRes.json()).access_token
  const created = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "secret" },
  })
  expect(created.status()).toBe(201)
  const itemId = (await created.json()).id

  await loginUi(page, creds_b.username, creds_b.password)
  await page.goto(`/items/${itemId}`)
  await expect(page.getByText("找不到此物品")).toBeVisible()
})
