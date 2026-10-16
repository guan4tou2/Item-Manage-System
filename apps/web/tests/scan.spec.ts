import { expect, test } from "@playwright/test"

/**
 * Phase 25 掃碼流程 e2e。
 *
 * 相機無法在 headless 環境使用，因此以「手動輸入」路徑驅動同一套分流邏輯；
 * 外部資料庫（Open Food Facts／Open Library）在 e2e **不依賴網路**——外查三態由
 * API 測試（provider mock）與元件測試（hook mock）覆蓋，此處僅測內查與表單流程。
 */

const EAN_A = "4710085200016"
const EAN_B = "4710085200023"

const unique = () => Date.now().toString() + Math.floor(Math.random() * 1000)

const PASSWORD = "secret1234"

async function register(
  request: import("@playwright/test").APIRequestContext,
  username: string,
) {
  const reg = await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  expect(reg.status()).toBe(201)
}

async function loginUi(
  page: import("@playwright/test").Page,
  username: string,
) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

async function loginApi(
  request: import("@playwright/test").APIRequestContext,
  username: string,
): Promise<string> {
  const login = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  expect(login.status()).toBe(200)
  return ((await login.json()) as { access_token: string }).access_token
}

async function seedItem(
  request: import("@playwright/test").APIRequestContext,
  token: string,
  body: { name: string; barcode?: string; quantity?: number },
): Promise<{ id: string; name: string }> {
  const res = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { quantity: 1, ...body },
  })
  expect(res.status()).toBe(201)
  const json = (await res.json()) as { id: string; name: string }
  return json
}

async function submitManual(
  page: import("@playwright/test").Page,
  value: string,
) {
  await page.getByRole("textbox").fill(value)
  await page.getByRole("button", { name: "前往" }).click()
}

test("內查單筆命中直接跳轉物品頁", async ({ page, request }) => {
  const username = `scan_single_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  const item = await seedItem(request, token, { name: "單筆牛奶", barcode: EAN_A })

  await loginUi(page, username)
  await page.goto("/scan")
  await submitManual(page, EAN_A)

  await page.waitForURL(`**/items/${item.id}`)
  await expect(page.getByRole("heading", { name: "單筆牛奶" })).toBeVisible()
})

test("內查多筆顯示候選列表並可點選", async ({ page, request }) => {
  const username = `scan_multi_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedItem(request, token, { name: "候選 A 牌", barcode: EAN_B })
  await seedItem(request, token, { name: "候選 B 牌", barcode: EAN_B, quantity: 3 })

  await loginUi(page, username)
  await page.goto("/scan")
  await submitManual(page, EAN_B)

  await expect(page.getByText("找到 2 件")).toBeVisible()
  await expect(page.getByRole("link", { name: /候選 A 牌/ })).toBeVisible()
  await expect(page.getByRole("link", { name: /候選 B 牌/ })).toBeVisible()

  await page.getByRole("link", { name: /候選 B 牌/ }).click()
  await page.waitForURL(/\/items\/[0-9a-f-]{36}$/)
  await expect(page.getByRole("heading", { name: "候選 B 牌" })).toBeVisible()
})

test("非條碼輸入維持名稱搜尋（QR 流程零回歸）", async ({ page, request }) => {
  const username = `scan_keyword_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedItem(request, token, { name: "洗衣精補充包" })

  await loginUi(page, username)
  await page.goto("/scan")
  await submitManual(page, "洗衣精")

  await page.waitForURL(/\/items\?q=/)
  await expect(page.getByText("洗衣精補充包")).toBeVisible()
})

test("表單以 ?barcode= 帶入並提示既有同條碼物品", async ({ page, request }) => {
  const username = `scan_form_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedItem(request, token, { name: "已有牛奶", barcode: EAN_A })

  await loginUi(page, username)
  await page.goto(`/items/new?barcode=${EAN_A}`)

  await expect(page.getByLabel("條碼", { exact: true })).toHaveValue(EAN_A)
  await expect(
    page.getByText("系統已有 1 件同條碼的物品。"),
  ).toBeVisible()
})

test("建立物品帶入條碼、詳情顯示並可用條碼搜尋", async ({ page, request }) => {
  const username = `scan_crud_${unique()}`
  await register(request, username)
  await loginUi(page, username)

  await page.goto("/items/new")
  await page.getByLabel("名稱").fill("手輸條碼物品")
  await page.getByLabel("條碼", { exact: true }).fill(EAN_B)
  await page.getByRole("button", { name: "儲存" }).click()

  await page.waitForURL(/\/items\/[0-9a-f-]{36}$/)
  await expect(page.getByText(EAN_B)).toBeVisible()
  await expect(page.getByRole("button", { name: "複製條碼" })).toBeVisible()

  await page.goto(`/items?q=${EAN_B}`)
  await expect(page.getByText("手輸條碼物品")).toBeVisible()
})

test.describe("行動版掃描 FAB（§5.7）", () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test("FAB 可見並導向掃描頁", async ({ page, request }) => {
    const username = `scan_fab_${unique()}`
    await register(request, username)
    await loginUi(page, username)

    const fab = page.getByRole("link", { name: "掃描條碼" })
    await expect(fab).toBeVisible()
    await fab.click()
    await page.waitForURL("**/scan")
  })
})

test("桌面版不顯示掃描 FAB，改用 nav 入口", async ({ page, request }) => {
  const username = `scan_desktop_${unique()}`
  await register(request, username)
  await loginUi(page, username)

  await expect(page.getByRole("link", { name: "掃描條碼" })).toBeHidden()
  await page.getByRole("link", { name: "掃碼" }).first().click()
  await page.waitForURL("**/scan")
})
