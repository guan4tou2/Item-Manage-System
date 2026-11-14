import { expect, test, type APIRequestContext, type Page } from "@playwright/test"

async function setup(page: Page, request: APIRequestContext) {
  const username = `offline_edit_${Date.now()}_${Math.floor(Math.random() * 10000)}`
  const password = "secret1234"
  expect((await request.post("/api/auth/register", { data: { username, email: `${username}@t.io`, password } })).status()).toBe(201)
  const login = await request.post("/api/auth/login", { data: { username, password } })
  expect(login.status()).toBe(200)
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const response = await request.post("/api/items", { headers, data: { name: "原來的備用電池", quantity: 3 } })
  expect(response.status()).toBe(201)
  const id = (await response.json()).id as string
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
  // Visit the list/detail before disconnecting; offline browsing of unopened pages is out of scope.
  await page.goto("/items")
  await page.getByRole("link", { name: "原來的備用電池", exact: true }).click()
  await page.waitForURL(`**/items/${id}`)
  await expect(page.getByRole("heading", { name: "原來的備用電池", exact: true })).toBeVisible()
  return { id, headers }
}
async function offlineEdit(page: Page) {
  await page.getByRole("link", { name: "編輯", exact: true }).click()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("原來的備用電池")
  await expect(page.getByRole("button", { name: "儲存", exact: true })).toBeEnabled()
  await page.context().setOffline(true)
  await page.getByLabel("名稱", { exact: true }).fill("我改的備用電池")
  await expect(page.getByRole("button", { name: "上傳圖片" })).toBeDisabled()
  await expect(page.getByRole("button", { name: "使用 AI 辨識填入" })).toBeDisabled()
  await expect(page.getByRole("switch", { name: "追蹤批次" })).toBeDisabled()
  await page.getByRole("button", { name: "儲存", exact: true }).click()
  // 離線時留在表單上（導頁需要連線），表單保留我改的值。
  await expect(page.getByText("有尚未同步的修改")).toBeVisible()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("我改的備用電池")
  await page.getByRole("link", { name: "物品", exact: true }).first().click()
  const pending = page.getByRole("region", { name: "1 筆待同步" })
  await expect(pending).toBeVisible()
  return pending
}
for (const width of [1280, 375]) {
  test(`開著表單時離線修改 → 自動同步（${width}px）`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 })
    const { id, headers } = await setup(page, request)
    const pending = await offlineEdit(page)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.context().setOffline(false)
    await expect(pending).toHaveCount(0)
    await expect.poll(async () => (await (await request.get(`/api/items/${id}`, { headers })).json()).name).toBe("我改的備用電池")
  })
}
test("離線時另一台裝置改過 → 顯示衝突 → 用我的版本", async ({ page, request }) => {
  const { id, headers } = await setup(page, request)
  const pending = await offlineEdit(page)
  const changed = await request.patch(`/api/items/${id}`, { headers, data: { name: "另一台裝置改的名稱" } })
  expect(changed.status()).toBe(200)
  await page.context().setOffline(false)
  await pending.getByText("查看待同步物品").click()
  await expect(pending.getByText("這個物品在你離線期間被修改過")).toBeVisible()
  await pending.getByRole("button", { name: "用我的版本", exact: true }).click()
  await expect(pending).toHaveCount(0)
  await expect.poll(async () => (await (await request.get(`/api/items/${id}`, { headers })).json()).name).toBe("我改的備用電池")
})
test("開著詳情頁時離線刪除 → 清單隱藏 → 連線後 API 為 404", async ({ page, request }) => {
  const { id, headers } = await setup(page, request)
  await page.context().setOffline(true)
  await page.getByRole("button", { name: "刪除", exact: true }).click()
  await page.getByRole("alertdialog").getByRole("button", { name: "刪除", exact: true }).click()
  // 離線時留在詳情頁顯示已排入刪除；清單是先前載入過的頁面，離線仍可開啟。
  await expect(page.getByText("這個物品已排入刪除")).toBeVisible()
  // 導覽列的「物品」此時帶有待同步數量徽章。
  await page.getByRole("navigation").getByRole("link", { name: /^物品/ }).click()
  await page.waitForURL("**/items")
  const pending = page.getByRole("region", { name: "1 筆待同步" })
  await expect(pending).toBeVisible()
  await expect(page.getByRole("link", { name: "原來的備用電池", exact: true })).toHaveCount(0)
  await page.context().setOffline(false)
  await expect(pending).toHaveCount(0)
  await expect.poll(async () => (await request.get(`/api/items/${id}`, { headers })).status()).toBe(404)
})

test("關掉分頁後由 service worker 背景同步（以 CDP 觸發 sync 事件）", async ({ page, request }) => {
  const { id, headers } = await setup(page, request)
  await page.evaluate(() => navigator.serviceWorker.ready.then(() => undefined))
  await offlineEdit(page)
  const origin = new URL(page.url()).origin
  const context = page.context()
  // 關掉唯一的分頁：頁面端不可能再同步，只剩 service worker。
  await page.close()
  const blank = await context.newPage()
  const cdp = await context.newCDPSession(blank)
  const registrations: Array<{ registrationId: string; scopeURL: string }> = []
  cdp.on("ServiceWorker.workerRegistrationUpdated", (event) => registrations.push(...event.registrations))
  await cdp.send("ServiceWorker.enable")
  await context.setOffline(false)
  // 同源的靜態檔，不會載入 App（也就不會觸發頁面端同步）。
  await blank.goto("/offline-engine.js")
  await expect.poll(() => registrations.find((r) => r.scopeURL.startsWith(origin))?.registrationId).toBeTruthy()
  const name = async () => (await (await request.get(`/api/items/${id}`, { headers })).json()).name
  expect(await name()).toBe("原來的備用電池")
  // 測試用的 Chromium 停用了 Background Sync 的排程，改由 CDP 直接送出 sync 事件。
  await cdp.send("ServiceWorker.dispatchSyncEvent", {
    origin,
    registrationId: registrations.find((r) => r.scopeURL.startsWith(origin))!.registrationId,
    tag: "ims-offline-sync",
    lastChance: false,
  })
  await expect.poll(name).toBe("我改的備用電池")
})
