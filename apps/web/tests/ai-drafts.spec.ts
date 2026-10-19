import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

/** 1×1 PNG（辨識不需可讀內容：無 API key 時一律走失敗路徑）。 */
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

async function apiToken(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  return (await res.json()).access_token as string
}

async function loginUi(page: UiPage, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

/** 註冊＋登入（UI）＋回傳 API token（每次測試自成一戶，資料隔離）。 */
async function signIn(request: ApiCtx, page: UiPage) {
  const username = `aid_${unique()}`
  await register(request, username)
  const token = await apiToken(request, username)
  await loginUi(page, username)
  return token
}

/** 以 API 建立歷史：1 個分類（廚房用品）＋1 筆同名物品。 */
async function seedHistory(request: ApiCtx, token: string) {
  const category = await request.post("/api/categories", {
    headers: auth(token),
    data: { name: "廚房用品" },
  })
  expect(category.status()).toBe(201)
  const categoryId = (await category.json()).id as number

  const item = await request.post("/api/items", {
    headers: auth(token),
    data: { name: "咖啡濾杯", quantity: 1, category_id: categoryId },
  })
  expect(item.status()).toBe(201)
}

/** 進入佇列頁並以檔案選擇器上傳照片。 */
async function uploadPhotos(page: UiPage, names: string[]) {
  await page.goto("/items/drafts")
  await page
    .locator('input[type="file"]')
    .setInputFiles(names.map((name) => ({ name, mimeType: "image/png", buffer: PNG })))
}

const cards = (page: UiPage) => page.locator('[data-testid^="draft-card-"]')

test("無 API key：上傳→失敗→依歷史建議→手動接受入庫", async ({ page, request }) => {
  const token = await signIn(request, page)
  await seedHistory(request, token)

  // /items/new 入口卡 → 前往佇列
  await page.goto("/items/new")
  await expect(page.getByTestId("batch-entry-card")).toBeVisible()
  await page.getByRole("link", { name: "開啟草稿佇列" }).click()
  await page.waitForURL("**/items/drafts")
  await expect(page.getByRole("heading", { name: "AI 批次入庫" })).toBeVisible()
  await expect(page.getByText("改為手動新增")).toBeVisible()

  // 上傳 2 張 → 兩張卡自動辨識 → 皆失敗（無 key）
  await page
    .locator('input[type="file"]')
    .setInputFiles(["p1.png", "p2.png"].map((name) => ({ name, mimeType: "image/png", buffer: PNG })))
  await expect(cards(page)).toHaveCount(2)
  await expect(cards(page).nth(0).getByTestId("draft-status")).toContainText("辨識失敗", {
    timeout: 15_000,
  })
  await expect(cards(page).nth(1).getByTestId("draft-status")).toContainText("辨識失敗", {
    timeout: 15_000,
  })
  await expect(cards(page).nth(0).getByRole("alert")).toContainText("AI 未設定")

  // 縮圖須帶 Bearer（AuthImage）：naturalWidth > 0 證明不是破圖
  const thumb = cards(page).nth(0).locator("img")
  await expect(thumb).toBeVisible()
  expect(await thumb.evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0)

  // 第 1 張：展開手動填寫 → 命名 → 依歷史建議 → 套用分類 → 接受
  const first = cards(page).nth(0)
  await first.getByRole("button", { name: "手動填寫" }).click()
  await first.getByLabel("名稱").fill("咖啡濾杯")
  await first.getByRole("button", { name: "依歷史建議" }).click()

  await expect(first.getByTestId("draft-history-category-badge")).toContainText(
    "依歷史：廚房用品",
  )
  await expect(first.getByTestId("draft-category-select")).toContainText("廚房用品")
  await first.getByRole("button", { name: "接受" }).click()

  await expect(page.getByText("已接受「咖啡濾杯」")).toBeVisible()
  await expect(cards(page)).toHaveCount(1)

  // 入庫結果：/items 可見新物品（＋既有歷史種子共 2 筆同名），草稿不再出現在佇列
  await page.goto("/items")
  await expect(page.getByRole("link", { name: "咖啡濾杯" })).toHaveCount(2)
  await page.goto("/items/drafts")
  await expect(cards(page)).toHaveCount(1)
  await expect(page.getByText("咖啡濾杯")).toHaveCount(0)
})

test("批量丟棄：勾選後全部丟棄，回到空狀態引導", async ({ page, request }) => {
  await signIn(request, page)
  await uploadPhotos(page, ["batch.png"])

  await expect(cards(page)).toHaveCount(1)
  await expect(cards(page).first().getByTestId("draft-status")).toContainText("辨識失敗", {
    timeout: 15_000,
  })

  await page.getByRole("checkbox", { name: /選取草稿/ }).check()
  await expect(page.getByText("已選 1 筆")).toBeVisible()
  await page.getByRole("button", { name: "全部丟棄" }).click()

  await expect(page.getByText("已丟棄 1 筆草稿")).toBeVisible()
  await expect(page.getByText("尚無草稿")).toBeVisible()
  await expect(page.getByText("從上方上傳照片開始辨識")).toBeVisible()
  await expect(cards(page)).toHaveCount(0)
})

test("入口卡徽章顯示待審核數量", async ({ page, request }) => {
  await signIn(request, page)

  // 尚無草稿：無徽章
  await page.goto("/items/new")
  await expect(page.getByTestId("batch-entry-card")).toBeVisible()
  await expect(page.getByTestId("batch-entry-badge")).toHaveCount(0)

  // 建立 1 筆活動草稿（失敗仍在活動四態內）
  await uploadPhotos(page, ["badge.png"])
  await expect(cards(page).first().getByTestId("draft-status")).toContainText("辨識失敗", {
    timeout: 15_000,
  })

  await page.goto("/items/new")
  await expect(page.getByTestId("batch-entry-badge")).toContainText("1 筆待審核")
})
