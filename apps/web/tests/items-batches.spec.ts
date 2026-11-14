import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("批次追蹤與到期模式：FEFO −1 樂觀扣減並在清零時回饋", async ({ page }) => {
  const suffix = unique()
  const username = `e2e_batch_${suffix}`
  const itemName = `牛奶 ${suffix}`

  const reg = await page.request.post("/api/auth/register", {
    data: { email: `${username}@example.com`, username, password: "secret1234" },
  })
  expect(reg.status()).toBe(201)

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // UI 登入後以 API 取得 token（web 端 API 認證走 Bearer，cookie 僅為存在旗標）
  const login = await page.request.post("/api/auth/login", {
    data: { username, password: "secret1234" },
  })
  const { access_token } = (await login.json()) as { access_token: string }
  const auth = { Authorization: `Bearer ${access_token}` }

  const created = await page.request.post("/api/items", {
    headers: auth,
    data: { name: itemName, quantity: 2 },
  })
  expect(created.status()).toBe(201)
  const item = (await created.json()) as { id: string }

  // 到期日以台北時區計算（app 的 days_left 以 Asia/Taipei 為基準）
  const taipeiDatePlusDays = (days: number) =>
    new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(
      new Date(Date.now() + days * 86_400_000),
    )
  const expiry = taipeiDatePlusDays(2)
  const batch = await page.request.post(`/api/items/${item.id}/batches`, {
    headers: auth,
    data: { quantity: 2, expiry_date: expiry },
  })
  expect(batch.status()).toBe(201)

  await page.goto("/items?expiry=expiring_soon&sort=expiry_asc")
  const row = page.getByRole("row", { name: new RegExp(itemName) })
  await expect(row).toContainText("剩 2 天")
  await expect(row.getByTestId("items-table-quantity-cell")).toHaveText("2")

  await row.getByRole("button", { name: `消耗 1：${itemName}` }).click()
  await expect(row.getByTestId("items-table-quantity-cell")).toHaveText("1")

  await row.getByRole("button", { name: `消耗 1：${itemName}` }).click()
  await expect(page.getByText(`已清零：${itemName}`).first()).toBeVisible()
})

test("不同批次成本：新增與編輯單價、批次小計及統計一致", async ({ page }) => {
  const username = `e2e_batchcost_${unique()}`
  const reg = await page.request.post("/api/auth/register", {
    data: { email: `${username}@example.com`, username, password: "secret1234" },
  })
  expect(reg.status()).toBe(201)
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  const login = await page.request.post("/api/auth/login", {
    data: { username, password: "secret1234" },
  })
  const { access_token } = await login.json()
  const created = await page.request.post("/api/items", {
    headers: { Authorization: `Bearer ${access_token}` },
    data: { name: `咖啡豆 ${username}`, quantity: 2, cost: "10" },
  })
  expect(created.status()).toBe(201)
  const item = await created.json()
  const first = await page.request.post(`/api/items/${item.id}/batches`, {
    headers: { Authorization: `Bearer ${access_token}` },
    data: { quantity: 2, unit_cost: "12.50" },
  })
  expect(first.status()).toBe(201)

  await page.goto(`/items/${item.id}`)
  await expect(page.getByText("NT$12.50", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "進貨／調整" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("數量").fill("3")
  await dialog.getByLabel("單位成本（NT$）").fill("20")
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByText("NT$20", { exact: true })).toBeVisible()
  await expect(page.getByTestId("batch-valuation")).toHaveText("估值 NT$85")

  // 行動寬度檢查批次列與對話框，並驗證編輯後的估值快取會更新。
  await page.setViewportSize({ width: 375, height: 812 })
  const row = page.getByRole("listitem").filter({ has: page.getByText("剩 3", { exact: true }) })
  await row.getByRole("button", { name: "編輯", exact: true }).click()
  await expect(dialog.getByLabel("單位成本（NT$）")).toHaveValue("20.00")
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true)
  await dialog.getByLabel("單位成本（NT$）").fill("21")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByTestId("batch-valuation")).toHaveText("估值 NT$88")
  expect(await row.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true)

  await page.goto("/statistics")
  await expect(page.getByTestId("value-summary")).toHaveText("NT$88")
})
