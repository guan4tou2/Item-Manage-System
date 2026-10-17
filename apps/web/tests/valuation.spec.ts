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

/** 檢查 el 是否在 other 之前（document order）。 */
async function isBefore(
  el: import("@playwright/test").ElementHandle,
  other: import("@playwright/test").ElementHandle,
) {
  return el.evaluate(
    (node, target) =>
      Boolean(node.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING),
    other,
  )
}

test("統計頁顯示估值摘要與兩張分布圖（含未填比例）", async ({ page, request }) => {
  const u = `val_${unique()}`
  await register(request, u)
  const token = await apiToken(request, u)

  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "咖啡豆", quantity: 2, cost: "1200.50" },
  })
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "濾紙", quantity: 1 },
  })

  await loginUi(page, u)
  await page.goto("/statistics")

  const summary = page.getByTestId("value-summary")
  await expect(summary).toHaveText("NT$2,401") // 1200.50 × 2，整數無小數
  await expect(page.getByText("已填成本 1／2 件", { exact: true })).toBeVisible()
  await expect(page.getByText("未填成本 1 件（50%）", { exact: true })).toBeVisible()
  await expect(page.getByText("依分類估值", { exact: true })).toBeVisible()
  await expect(page.getByText("依位置估值", { exact: true })).toBeVisible()

  // 估值區塊置頂：value-summary 在趨勢圖之前
  const summaryEl = await summary.elementHandle()
  const trendEl = await page.getByText("新增趨勢 (近 30 天)", { exact: true }).elementHandle()
  expect(await isBefore(summaryEl!, trendEl!)).toBe(true)
})

test("幣別偏好切 JPY：估值前綴變 ¥ 且重整後維持", async ({ page, request }) => {
  const u = `val2_${unique()}`
  await register(request, u)
  const token = await apiToken(request, u)
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "相機", quantity: 1, cost: "1200" },
  })

  await loginUi(page, u)
  await page.goto("/statistics")
  await expect(page.getByTestId("value-summary")).toHaveText("NT$1,200")

  await page.goto("/settings/preferences")
  await expect(page.getByText("幣別", { exact: true })).toBeVisible()
  await page.getByRole("combobox").nth(2).click()
  await page.getByRole("option", { name: "日圓（JPY）" }).click()
  await expect(page.getByText("偏好已儲存")).toBeVisible()

  await page.goto("/statistics")
  await expect(page.getByTestId("value-summary")).toHaveText("¥1,200") // JPY 0 位小數

  await page.reload()
  await expect(page.getByTestId("value-summary")).toHaveText("¥1,200")
})

test("物品表單成本欄：非法值行內錯誤、合法值詳情格式化顯示", async ({ page, request }) => {
  const u = `val3_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  // 非法值（3 位小數）：行內錯誤且留在表單
  await page.goto("/items/new")
  await page.getByLabel("名稱").fill("手沖壺")
  await page.getByLabel("成本").fill("1.234")
  await page.getByRole("button", { name: /^儲存$/ }).click()
  await expect(
    page.getByText("成本需為數字，最多 2 位小數（例：12.30）", { exact: true }),
  ).toBeVisible()
  await expect(page).toHaveURL(/\/items\/new$/)

  // 合法值：建立後詳情顯示格式化金額
  await page.getByLabel("成本").fill("99.50")
  await page.getByRole("button", { name: /^儲存$/ }).click()
  await page.waitForURL(/\/items\/[0-9a-f-]+$/)
  await expect(page.getByTestId("item-cost")).toHaveText("NT$99.50")
})

test("儀表板估值卡：行動卡之後、連結至統計頁", async ({ page, request }) => {
  const u = `val4_${unique()}`
  await register(request, u)
  const token = await apiToken(request, u)
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "麥克風", quantity: 1, cost: "3500" },
  })

  await loginUi(page, u)

  const card = page.getByTestId("value-card")
  await expect(card).toBeVisible()
  await expect(page.getByTestId("value-card-amount")).toHaveText("NT$3,500")

  // DOM 序：在到期卡與借出卡（皆為行動卡）之後
  const cardEl = await card.elementHandle()
  const expiryEl = await page.getByTestId("expiry-card").elementHandle()
  const loansEl = await page.getByText("目前沒有未歸還的借出", { exact: true }).elementHandle()
  expect(await isBefore(expiryEl!, cardEl!)).toBe(true)
  expect(await isBefore(loansEl!, cardEl!)).toBe(true)

  await page.getByTestId("value-card-link").click()
  await page.waitForURL("**/statistics")
})
