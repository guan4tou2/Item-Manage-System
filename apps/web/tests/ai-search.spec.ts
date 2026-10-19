import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

async function register(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  expect(res.status()).toBe(201)
}

async function loginUi(page: UiPage, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

async function signIn(request: ApiCtx, page: UiPage) {
  const username = `aisrch_${unique()}`
  await register(request, username)
  await loginUi(page, username)
  return username
}

async function apiToken(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  return (await res.json()).access_token as string
}

async function seedItem(request: ApiCtx, username: string, name: string) {
  const token = await apiToken(request, username)
  const res = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, quantity: 1 },
  })
  expect(res.status()).toBe(201)
}

test("未開啟資料分享：AI 搜尋顯示設定引導", async ({ page, request }) => {
  await signIn(request, page)
  await page.goto("/items")

  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("廚房裡快過期的藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()

  await expect(
    page.getByText("請先在設定開啟「AI 資料分享」才能使用 AI 搜尋"),
  ).toBeVisible()
  await expect(page.getByRole("link", { name: "前往設定" })).toHaveAttribute(
    "href",
    "/settings/preferences",
  )
})

test("已開啟資料分享但無 AI key：退回關鍵字搜尋且不報錯", async ({ page, request }) => {
  const username = await signIn(request, page)
  await seedItem(request, username, "感冒藥")

  // 開啟 AI 資料分享（設定頁開關）
  await page.goto("/settings/preferences")
  await page.getByRole("switch").click()
  await expect(page.getByRole("switch")).toBeChecked()

  await page.goto("/items")
  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("感冒藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()

  // 中性提示（非錯誤），且仍顯示關鍵字結果
  await expect(page.getByText("AI 未設定；已改用關鍵字搜尋")).toBeVisible()
  await expect(page.getByRole("link", { name: "感冒藥" })).toBeVisible()
})

test("AI 搜尋可清除理解結果並切回一般搜尋", async ({ page, request }) => {
  const username = await signIn(request, page)
  await seedItem(request, username, "感冒藥")
  await page.goto("/settings/preferences")
  await page.getByRole("switch").click()
  await expect(page.getByRole("switch")).toBeChecked()

  await page.goto("/items")
  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("感冒藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()
  await expect(page.getByText("AI 未設定；已改用關鍵字搜尋")).toBeVisible()

  await page.getByRole("button", { name: "清除" }).click()
  await expect(page.getByText("AI 未設定；已改用關鍵字搜尋")).toHaveCount(0)

  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await expect(page.getByLabel("用一句話描述你要找的東西")).toHaveCount(0)
})

test("問答在無 AI key 時顯示不可用說明", async ({ page, request }) => {
  const username = await signIn(request, page)
  await seedItem(request, username, "感冒藥")
  await page.goto("/settings/preferences")
  await page.getByRole("switch").click()
  await expect(page.getByRole("switch")).toBeChecked()

  await page.goto("/items")
  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("感冒藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()
  await expect(page.getByRole("link", { name: "感冒藥" })).toBeVisible()

  // 有結果 → 顯示問答面板
  await expect(page.getByTestId("ai-ask-panel")).toBeVisible()
  await page.getByLabel("對這些物品提問").fill("還剩多少？")
  await page.getByRole("button", { name: "提問" }).click()

  await expect(page.getByText("AI 未設定；無法使用問答")).toBeVisible()
})
