import { expect, test, type APIRequestContext, type Page } from "@playwright/test"

const PASSWORD = "secret1234"

async function setup(page: Page, request: APIRequestContext) {
  const username = `offline_${Date.now()}_${Math.floor(Math.random() * 10000)}`
  const registered = await request.post("/api/auth/register", {
    data: { username, email: `${username}@t.io`, password: PASSWORD },
  })
  expect(registered.status()).toBe(201)
  const login = await request.post("/api/auth/login", { data: { username, password: PASSWORD } })
  expect(login.status()).toBe(200)
  const token = (await login.json()).access_token as string
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
  // D21：先造訪清單；不依賴未曾開啟的頁面能離線啟動。
  await page.goto("/items")
  await expect(page.getByText("還沒有任何物品")).toBeVisible()
  return { Authorization: `Bearer ${token}` }
}

async function openForm(page: Page) {
  await page.getByRole("link", { name: "新增物品" }).first().click()
  await page.waitForURL("**/items/new")
  await expect(page.getByLabel("名稱")).toBeVisible()
  await expect(page.getByRole("button", { name: /^儲存$/ })).toBeEnabled()
}

for (const width of [1280, 375]) {
  test(`離線新增 → 自動同步且只有一筆（${width}px）`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 })
    const headers = await setup(page, request)
    await openForm(page)
    await page.getByLabel("名稱").fill("離線記下的備用電池")
    await page.getByLabel("數量").fill("3")
    // 必須在線上把新增頁載入完成，再模擬斷線。
    await page.context().setOffline(true)
    await expect(page.getByText("目前離線——新增的物品會先存在這台裝置")).toBeVisible()
    await expect(page.getByRole("button", { name: "上傳圖片" })).toBeDisabled()
    await expect(page.getByRole("button", { name: "使用 AI 辨識填入" })).toBeDisabled()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole("button", { name: /^儲存$/ }).click()
    await page.waitForURL("**/items")
    const pending = page.getByRole("region", { name: "1 筆待同步" })
    await expect(pending).toBeVisible()
    await pending.getByText("查看待同步物品").click()
    await expect(pending.getByText("離線記下的備用電池")).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.context().setOffline(false)
    await expect(pending).toHaveCount(0)
    await expect(page.getByRole("link", { name: "離線記下的備用電池" })).toBeVisible()
    const response = await request.get("/api/items?q=離線記下的備用電池", { headers })
    expect(response.status()).toBe(200)
    const data = await response.json()
    expect(data.total).toBe(1)
    expect(data.items[0].quantity).toBe(3)
  })
}

test("離線期間位置被刪除 → 顯示原因並確認捨棄", async ({ page, request }) => {
  const headers = await setup(page, request)
  const location = await request.post("/api/locations", { headers, data: { name: "暫存櫃" } })
  expect(location.status()).toBe(201)
  const id = (await location.json()).id as number
  // setup() 已載入過物品清單（位置樹被快取為空）；位置是之後才用 API 建立的，重新載入讓表單看得到它。
  await page.reload()
  await expect(page.getByText("還沒有任何物品")).toBeVisible()
  await openForm(page)
  await page.getByLabel("名稱").fill("待確認物品")
  await page.getByLabel("位置 1").click()
  await page.getByRole("option", { name: "暫存櫃" }).click()
  await page.context().setOffline(true)
  await page.getByRole("button", { name: /^儲存$/ }).click()
  await page.waitForURL("**/items")
  const pending = page.getByRole("region", { name: "1 筆待同步" })
  await expect(pending).toBeVisible()
  // APIRequestContext 不受瀏覽器離線狀態影響，模擬另一台裝置刪除位置。
  const deleted = await request.delete(`/api/locations/${id}`, { headers })
  expect(deleted.status()).toBe(204)
  await page.context().setOffline(false)
  await pending.getByText("查看待同步物品").click()
  await expect(pending.getByText("原位置已不存在，請編輯並重新選擇位置")).toBeVisible()
  await pending.getByRole("button", { name: "捨棄", exact: true }).click()
  await page.getByRole("alertdialog").getByRole("button", { name: "捨棄", exact: true }).click()
  await expect(pending).toHaveCount(0)
  const response = await request.get("/api/items?q=待確認物品", { headers })
  expect((await response.json()).total).toBe(0)
})
