import { expect, test } from "@playwright/test"

/**
 * Phase 36 位置 QR 標籤 e2e：
 * - 位置管理頁 → 節點選單「列印標籤」→ 列印頁顯示 QR 與名稱
 * - 頁首「列印位置標籤」→ 勾選模式（一次印多個位置）
 * - 掃碼頁手動輸入位置深連結 → 導向該位置（含子孫）的物品清單
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

async function apiToken(request: ApiCtx, username: string): Promise<string> {
  const res = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  expect(res.status()).toBe(200)
  return ((await res.json()) as { access_token: string }).access_token
}

async function signIn(request: ApiCtx, page: UiPage) {
  const username = `loclbl_${unique()}`
  await register(request, username)
  const token = await apiToken(request, username)
  await loginUi(page, username)
  return token
}

async function seedLocation(
  request: ApiCtx,
  token: string,
  body: { name: string; parent_id?: number },
): Promise<number> {
  const res = await request.post("/api/locations", {
    headers: auth(token),
    data: body,
  })
  expect(res.status()).toBe(201)
  return ((await res.json()) as { id: number }).id
}

async function seedItem(
  request: ApiCtx,
  token: string,
  name: string,
  locationId: number,
): Promise<string> {
  const res = await request.post("/api/items", {
    headers: auth(token),
    data: { name, location_id: locationId },
  })
  expect(res.status()).toBe(201)
  return ((await res.json()) as { id: string }).id
}

test("位置標籤列印頁：節點選單 → 列印頁顯示 QR 與名稱", async ({ page, request }) => {
  const token = await signIn(request, page)
  const floor = await seedLocation(request, token, { name: "1F" })
  const shelf = await seedLocation(request, token, { name: "藥箱", parent_id: floor })
  await seedItem(request, token, "感冒藥", shelf)

  await page.goto("/locations")
  // 展開 1F 才能看到子節點
  await page.getByTestId(`location-node-${floor}`).getByRole("button", { name: "展開" }).click()
  const node = page.getByTestId(`location-node-${shelf}`)
  await node.getByRole("button", { name: /更多操作/ }).click()
  await page.getByRole("menuitem", { name: "列印標籤" }).click()

  await expect(page).toHaveURL(new RegExp(`/locations/labels\\?ids=${shelf}`))
  await expect(page.getByRole("heading", { name: "列印位置標籤" })).toBeVisible()
  const card = page.getByTestId(`location-label-${shelf}`)
  await expect(card).toBeVisible()
  await expect(card.getByText("藥箱", { exact: true })).toBeVisible()
  await expect(card.getByText("1F / 藥箱")).toBeVisible()
  await expect(card.getByText("1 件")).toBeVisible()
  // QR 影像實際載入（非破圖）
  const img = card.locator("img")
  await expect(img).toBeVisible()
  expect(await img.evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0)
})

test("位置標籤列印頁：頁首入口 → 勾選模式", async ({ page, request }) => {
  const token = await signIn(request, page)
  await seedLocation(request, token, { name: "書房" })

  await page.goto("/locations")
  await page.getByRole("button", { name: "列印位置標籤" }).click()
  await expect(page).toHaveURL(/\/locations\/labels$/)

  await expect(page.getByText("選擇要貼標籤的位置")).toBeVisible()
  const checkbox = page.getByRole("checkbox", { name: "書房" })
  await expect(checkbox).toBeVisible()
  await checkbox.check()
  await expect(page.locator('[data-testid^="location-label-"]')).toHaveCount(1)
})

test("掃碼頁：位置深連結 → 該位置的物品清單", async ({ page, request }) => {
  const token = await signIn(request, page)
  const floor = await seedLocation(request, token, { name: "1F" })
  const shelf = await seedLocation(request, token, { name: "藥箱", parent_id: floor })
  await seedItem(request, token, "感冒藥", shelf)

  await page.goto("/scan")
  await page.getByRole("textbox").fill(`http://localhost/items?location=${shelf}`)
  await page.getByRole("button", { name: "前往" }).click()

  await expect(page).toHaveURL(new RegExp(`/items\\?location=${shelf}`))
  await expect(page.getByRole("link", { name: "感冒藥" })).toBeVisible()
})
