import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: "secret1234" },
  })
}

async function apiToken(request: import("@playwright/test").APIRequestContext, username: string) {
  const login = await request.post("/api/auth/login", {
    data: { username, password: "secret1234" },
  })
  return (await login.json()).access_token as string
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

/** 指向必然連線失敗的位址（`.invalid` 保證 DNS 解析失敗，建立時合法、送出時為網路錯誤，不依賴外部網路；127.0.0.1 會被 SSRF 防護在建立時拒絕）並觸發一次 item.created，產生確定性的失敗 delivery。 */
async function seedFailedDelivery(
  request: import("@playwright/test").APIRequestContext,
  token: string,
) {
  await request.post("/api/webhooks", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "壞端點", url: "http://webhook-unreachable.invalid/hook", events: ["item.created"] },
  })
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "觸發物" },
  })
}

test("webhook deliveries：列表、概覽、篩選、展開與重試", async ({ page, request }) => {
  const u = `wh_${unique()}`
  await register(request, u)
  const token = await apiToken(request, u)
  await seedFailedDelivery(request, token)

  await loginUi(page, u)
  await page.goto("/settings/webhooks")

  // 桌機表格：欄位與列（時間／事件／狀態／嘗試／下次重試）
  const table = page.getByTestId("deliveries-table")
  await expect(table).toBeVisible()
  await expect(table.getByText("物品建立", { exact: true })).toBeVisible()
  await expect(table.getByText("網路錯誤", { exact: true })).toBeVisible()
  await expect(table.getByText("第 1 次", { exact: true })).toBeVisible()

  // 概覽：成功率、最近成功（尚未成功 → —）
  const stats = page.getByTestId("deliveries-stats")
  await expect(stats).toContainText("成功率 0%（成功 0／總 1）")
  await expect(stats).toContainText("最近成功：—")

  // response excerpt 展開／收合
  await table.getByRole("button", { name: "顯示回應內容" }).click()
  await expect(page.getByTestId("delivery-excerpt")).toContainText("error:")
  await table.getByRole("button", { name: "收合回應內容" }).click()
  await expect(page.getByTestId("delivery-excerpt")).toHaveCount(0)

  // 狀態篩選：成功 → 無符合；清除篩選 → 回到全部
  await page.getByRole("button", { name: "成功", exact: true }).click()
  await expect(page.getByText("沒有符合的 delivery", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "清除篩選", exact: true }).click()
  await expect(table.getByText("第 1 次", { exact: true })).toBeVisible()

  // 立即重試：新增第 2 次嘗試列，概覽總數即時 +1
  await table.getByRole("button", { name: "立即重試" }).click()
  await expect(table.getByText("第 2 次", { exact: true })).toBeVisible()
  await expect(stats).toContainText("成功率 0%（成功 0／總 2）")
})

test("webhooks 行動版：表格隱藏改卡片；新用戶空態", async ({ page, request }) => {
  const u = `whm_${unique()}`
  await register(request, u)

  // 新用戶：空態引導
  await loginUi(page, u)
  await page.goto("/settings/webhooks")
  await expect(page.getByText("尚無 webhook", { exact: true })).toBeVisible()

  // 建資料後以 390 寬檢視：卡片可見、表格隱藏
  const token = await apiToken(request, u)
  await seedFailedDelivery(request, token)

  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()

  const cards = page.getByTestId("deliveries-cards")
  await expect(cards).toBeVisible()
  await expect(cards.getByText("第 1 次", { exact: true })).toBeVisible()
  await expect(cards.getByText("已排程重試", { exact: true })).toBeVisible()
  await expect(page.getByTestId("deliveries-table")).toBeHidden()
})
