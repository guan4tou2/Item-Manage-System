import { expect, test } from "@playwright/test"

/**
 * Phase 37 標籤條碼 e2e：
 * - 物品標籤列印頁顯示 Code128 條碼圖（可被掃描器讀取）＋ 條碼數字
 * - 批量標籤頁每張都含條碼圖
 * - 不可編碼的條碼（中文）→ 標籤仍可列印（退回純文字，不報錯）
 */

const unique = () => Date.now().toString() + Math.floor(Math.random() * 1000)
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

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
  const username = `lbl_${unique()}`
  await register(request, username)
  const login = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  expect(login.status()).toBe(200)
  const token = ((await login.json()) as { access_token: string }).access_token
  await loginUi(page, username)
  return token
}

async function seedItem(
  request: ApiCtx,
  token: string,
  name: string,
  barcode?: string,
): Promise<string> {
  const res = await request.post("/api/items", {
    headers: auth(token),
    data: { name, ...(barcode ? { barcode } : {}) },
  })
  expect(res.status()).toBe(201)
  return ((await res.json()) as { id: string }).id
}

test("單張物品標籤：QR ＋ Code128 條碼圖 ＋ 條碼數字", async ({ page, request }) => {
  const token = await signIn(request, page)
  const itemId = await seedItem(request, token, "相機", "4710085200016")

  await page.goto(`/items/${itemId}/label`)

  await expect(page.getByTestId("label-barcode")).toBeVisible()
  await expect(page.getByTestId("label-barcode").locator("svg")).toBeVisible()
  await expect(page.getByText("4710085200016")).toBeVisible()
  // QR 亦在（既有行為）
  await expect(page.getByRole("img", { name: /QR code/ })).toBeVisible()
})

test("批量標籤：每張都含條碼圖", async ({ page, request }) => {
  const token = await signIn(request, page)
  const itemId = await seedItem(request, token, "路由器", "4710085200016")

  await page.goto(`/items/labels?ids=${itemId}`)

  await expect(page.getByTestId("label-barcode")).toBeVisible()
  await expect(page.getByTestId("label-barcode").locator("svg")).toBeVisible()
})

test("不可編碼的條碼：標籤仍可列印（退回純文字）", async ({ page, request }) => {
  const token = await signIn(request, page)
  const itemId = await seedItem(request, token, "中文條碼物品", "中文條碼")

  await page.goto(`/items/${itemId}/label`)

  await expect(page.getByText("中文條碼", { exact: true })).toBeVisible()
  await expect(page.getByTestId("label-barcode")).toHaveCount(0)
})
