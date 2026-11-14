import { expect, test } from "@playwright/test"

test("分享唯讀清單給未登入者，撤銷後無法再讀取", async ({ page, request, browser }) => {
  const username = `share_${Date.now()}`
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: "secret1234" },
  })
  const login = await request.post("/api/auth/login", { data: { username, password: "secret1234" } })
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const created = await request.post("/api/lists", {
    headers, data: { kind: "shopping", title: "露營用品", budget: "5000" },
  })
  const listId = (await created.json()).id
  await request.post(`/api/lists/${listId}/entries`, { headers, data: { name: "帳篷", price: "1200" } })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
  await page.goto(`/lists/${listId}`)
  await page.getByRole("button", { name: "分享", exact: true }).click()
  await page.getByRole("button", { name: "建立分享連結" }).click()
  const url = await page.getByLabel("分享網址").inputValue()
  await page.setViewportSize({ width: 375, height: 812 })
  expect(await page.getByRole("dialog").evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(url).toMatch(/\/share#[A-Za-z0-9_-]{43}$/)

  const context = await browser.newContext({ locale: "zh-TW", viewport: { width: 375, height: 812 } })
  try {
    const guest = await context.newPage()
    const requests: string[] = []
    guest.on("request", req => requests.push(req.url()))
    await guest.goto(url)
    await expect(guest.getByRole("heading", { name: "露營用品" })).toBeVisible()
    await expect(guest.getByRole("heading", { name: "帳篷" })).toBeVisible()
    await expect(guest.getByText(/預算|價格/)).toHaveCount(0)
    await expect(guest.getByRole("checkbox")).toHaveCount(0)
    await expect(guest.locator("nav")).toHaveCount(0)
    expect(await guest.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const token = url.split("#")[1]!
    expect(requests.every(value => !value.includes(token))).toBe(true)
    expect(requests.some(value => value.includes("/auth/refresh"))).toBe(false)
    await expect(guest.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/)

    await page.getByRole("button", { name: "撤銷", exact: true }).click()
    await page.getByRole("alertdialog").getByRole("button", { name: "撤銷", exact: true }).click()
    await expect(page.getByText("尚無分享連結，請選擇效期後建立。")).toBeVisible()
    await guest.reload()
    await expect(guest.getByRole("heading", { name: "連結無效或已過期" })).toBeVisible()
  } finally { await context.close() }
})
