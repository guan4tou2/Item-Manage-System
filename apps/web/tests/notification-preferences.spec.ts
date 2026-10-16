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

test("偏好矩陣：預設摘要、切換持久化與重置流程", async ({ page, request }) => {
  const u = `pref_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  await page.goto("/settings/notifications")
  await expect(page.getByRole("heading", { name: "通知偏好" })).toBeVisible()
  await expect(page.getByText("物品提醒", { exact: true })).toBeVisible()
  await expect(page.getByText("借還與協作", { exact: true })).toBeVisible()
  await expect(page.getByText("系統與報表", { exact: true })).toBeVisible()
  await expect(page.getByTestId("preferences-defaults-banner")).toBeVisible()

  const matrix = page.getByTestId("preferences-matrix-items")
  const emailSwitch = matrix.getByRole("switch", { name: "庫存不足：Email" })
  await expect(emailSwitch).toBeChecked()
  await emailSwitch.click()
  await expect(page.getByText("偏好已更新")).toBeVisible()
  await expect(emailSwitch).not.toBeChecked()

  // reload 後覆寫仍在；摘要條與重置鈕切換為「有自訂」狀態
  await page.reload()
  await expect(page.getByTestId("preferences-defaults-banner")).toHaveCount(0)
  await expect(matrix.getByRole("switch", { name: "庫存不足：Email" })).not.toBeChecked()

  // 重置為預設
  await page.getByRole("button", { name: "重置為預設" }).click()
  await page.getByRole("alertdialog").getByRole("button", { name: "確認重置" }).click()
  await expect(page.getByText("已重置為預設")).toBeVisible()
  await expect(page.getByTestId("preferences-defaults-banner")).toBeVisible()
  await expect(matrix.getByRole("switch", { name: "庫存不足：Email" })).toBeChecked()
})

test("鎖定類型不可關閉；未綁定管道停用並連往通知管道設定", async ({ page, request }) => {
  const u = `pref2_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  await page.goto("/settings/notifications")

  const collab = page.getByTestId("preferences-matrix-collab")
  await expect(collab.getByRole("switch", { name: "群組邀請：站內" })).toBeDisabled()

  const items = page.getByTestId("preferences-matrix-items")
  await expect(items.getByRole("switch", { name: "庫存不足：LINE" })).toBeDisabled()
  await expect(items.getByRole("switch", { name: "庫存不足：站內" })).toBeEnabled()

  await items.getByRole("link", { name: "前往綁定" }).first().click()
  await expect(page).toHaveURL(/\/settings\/channels$/)
})

test("行動視窗（390）以每類型卡片佈局呈現偏好矩陣", async ({ page, request }) => {
  const u = `pref3_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)
  await page.setViewportSize({ width: 390, height: 844 })

  await page.goto("/settings/notifications")

  await expect(page.getByTestId("preferences-matrix-items")).toBeHidden()
  const cards = page.getByTestId("preferences-cards-items")
  const emailSwitch = cards.getByRole("switch", { name: "庫存不足：Email" })
  await expect(emailSwitch).toBeVisible()
  await emailSwitch.click()
  await expect(page.getByText("偏好已更新")).toBeVisible()
  await expect(emailSwitch).not.toBeChecked()
})

test("關閉站內「庫存不足」後，門檻觸發不再產生站內通知", async ({ page, request }) => {
  const u = `pref4_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  // UI 切換：庫存不足 × 站內 → 關（toast 出現代表伺服器已確認）
  await page.goto("/settings/notifications")
  await page
    .getByTestId("preferences-matrix-items")
    .getByRole("switch", { name: "庫存不足：站內" })
    .click()
  await expect(page.getByText("偏好已更新")).toBeVisible()

  // API 觸發：建立物品後跨過低庫存門檻
  const login = await request.post("/api/auth/login", { data: { username, password } })
  const token = (await login.json()).access_token
  const headers = { Authorization: `Bearer ${token}` }
  const item = await request.post("/api/items", {
    headers,
    data: { name: "偏好整合盒", quantity: 5, min_quantity: 2 },
  })
  const itemId = (await item.json()).id
  await request.patch(`/api/items/${itemId}`, { headers, data: { quantity: 1 } })

  // 通知中心：歡迎通知（鎖定類型）仍在，但不應出現庫存不足
  await page.goto("/notifications")
  await expect(page.getByText("歡迎使用 IMS")).toBeVisible()
  await expect(page.getByText(/庫存不足/)).toHaveCount(0)
})
