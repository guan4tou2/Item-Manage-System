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
