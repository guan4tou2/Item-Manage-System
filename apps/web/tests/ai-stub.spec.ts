import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

/** 1×1 PNG（stub 模式不解析圖片內容，任意可讀圖片皆可）。 */
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==",
  "base64",
)

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

async function apiToken(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  return (await res.json()).access_token as string
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

/** 註冊＋登入（UI）＋回傳 API token（每次測試自成一戶，資料隔離）。 */
async function signIn(request: ApiCtx, page: UiPage) {
  const username = `stub_${unique()}`
  await register(request, username)
  const token = await apiToken(request, username)
  await loginUi(page, username)
  return { username, token }
}

/** 讀取 AI 模式；非 stub 模式 → 略過本情境（避免誤在 live stack 上假失敗）。 */
async function requireStubMode(request: ApiCtx, token: string) {
  const res = await request.get("/api/ai/status", { headers: auth(token) })
  expect(res.status()).toBe(200)
  const body = (await res.json()) as { mode: string; enabled: boolean }
  test.skip(body.mode !== "stub", "需要 AI_MODE=stub（AI 成功路徑情境）")
}

async function optIn(request: ApiCtx, token: string) {
  const res = await request.put("/api/users/me/preferences", {
    headers: auth(token),
    data: { ai_data_sharing_enabled: true },
  })
  expect(res.status()).toBe(200)
}

/** 種子：位置「廚房」＋物品「感冒藥」＋3 天內到期的批次。 */
async function seedExpiringItem(request: ApiCtx, token: string) {
  const location = await request.post("/api/locations", {
    headers: auth(token),
    data: { name: "廚房" },
  })
  expect(location.status()).toBe(201)
  const locationId = (await location.json()).id as number

  const item = await request.post("/api/items", {
    headers: auth(token),
    data: { name: "感冒藥", "quantity": 2, location_id: locationId },
  })
  expect(item.status()).toBe(201)
  const itemId = (await item.json()).id as string

  const expiry = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)
  const batch = await request.post(`/api/items/${itemId}/batches`, {
    headers: auth(token),
    data: { quantity: 2, expiry_date: expiry },
  })
  expect(batch.status()).toBe(201)

  return { locationId, itemId }
}

const cards = (page: UiPage) => page.locator('[data-testid^="draft-card-"]')

test("收據成功路徑：抽取品項 → 對帳相符 → 接受入庫", async ({ page, request }) => {
  const { token } = await signIn(request, page)
  await requireStubMode(request, token)

  await page.goto("/items/drafts")
  await page.getByRole("tab", { name: "收據" }).click()
  await page.locator('input[type="file"]').setInputFiles([
    { name: "receipt.png", mimeType: "image/png", buffer: PNG },
  ])

  // 群組標頭：商家／頁數／品項數／對帳相符
  const header = page.getByTestId("receipt-group-header")
  await expect(header).toBeVisible()
  await expect(header).toContainText("測試商店")
  await expect(header).toContainText("1 頁")
  await expect(header).toContainText("2 個品項")
  await expect(header).toContainText("與收據總額相符")
  // Phase 38：算術拆解（品項合計 140 − 折扣 10 + 稅 5 + 運費 0 = 應付 135）
  await expect(header).toContainText("算術：品項合計 NT$140 − 折扣 NT$10 + 稅 NT$5 + 運費 NT$0 = 應付 NT$135")

  // 每個品項一列 ready 草稿，且帶入名稱／數量／成本
  await expect(cards(page)).toHaveCount(2)
  const first = cards(page).first()
  await expect(first.getByTestId("draft-status")).toContainText("辨識完成")
  await expect(first.getByLabel("名稱")).toHaveValue("測試品項甲")
  await expect(first.getByPlaceholder("0.00")).toHaveValue("50.00")

  // 接受 → 入庫
  await first.getByRole("button", { name: "接受" }).click()
  await expect(page.getByText("已接受「測試品項甲」")).toBeVisible()

  await page.goto("/items")
  await expect(page.getByRole("link", { name: "測試品項甲" })).toBeVisible()
})

test("AI 搜尋成功路徑：顯示「理解為」chip 與結果", async ({ page, request }) => {
  const { token } = await signIn(request, page)
  await requireStubMode(request, token)
  await optIn(request, token)
  await seedExpiringItem(request, token)

  await page.goto("/items")
  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("廚房裡快過期的感冒藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()

  // 理解為 chip：位置／到期／關鍵字
  const chips = page.getByTestId("ai-search-chips")
  await expect(chips).toBeVisible()
  await expect(chips).toContainText("位置：廚房")
  await expect(chips).toContainText("到期：7 天內")
  await expect(chips).toContainText("關鍵字：感冒藥")

  // 結果與筆數
  await expect(page.getByText("1 筆結果")).toBeVisible()
  await expect(page.getByRole("link", { name: "感冒藥" })).toBeVisible()

  // 非 fallback（stub 模式 AI 可用）
  await expect(page.getByText("AI 未設定；已改用關鍵字搜尋")).toHaveCount(0)
})

test("物品問答成功路徑：回答附引用連結", async ({ page, request }) => {
  const { token } = await signIn(request, page)
  await requireStubMode(request, token)
  await optIn(request, token)
  const { itemId } = await seedExpiringItem(request, token)

  await page.goto("/items")
  await page.getByRole("button", { name: "AI 搜尋" }).click()
  await page.getByLabel("用一句話描述你要找的東西").fill("廚房裡快過期的感冒藥")
  await page.getByRole("button", { name: "搜尋", exact: true }).click()
  await expect(page.getByTestId("ai-ask-panel")).toBeVisible()

  await page.getByLabel("對這些物品提問").fill("還有多少？")
  await page.getByRole("button", { name: "提問" }).click()

  const panel = page.getByTestId("ai-ask-panel")
  await expect(panel).toContainText("依系統資料")
  const citation = panel.getByRole("link", { name: "感冒藥" })
  await expect(citation).toBeVisible()
  await expect(citation).toHaveAttribute("href", `/items/${itemId}`)
  await expect(panel).toContainText("回答以系統資料為限")
})

test("批次入庫成功路徑：辨識完成 → 接受入庫", async ({ page, request }) => {
  const { token } = await signIn(request, page)
  await requireStubMode(request, token)

  await page.goto("/items/drafts")
  await page.locator('input[type="file"]').setInputFiles([
    { name: "photo.png", mimeType: "image/png", buffer: PNG },
  ])

  const card = cards(page).first()
  await expect(card).toHaveCount(1)
  await expect(card.getByTestId("draft-status")).toContainText("辨識完成", {
    timeout: 15_000,
  })
  await expect(card.getByLabel("名稱")).toHaveValue("測試物品")

  await card.getByRole("button", { name: "接受" }).click()
  await expect(page.getByText("已接受「測試物品」")).toBeVisible()

  await page.goto("/items")
  await expect(page.getByRole("link", { name: "測試物品" })).toBeVisible()
})
