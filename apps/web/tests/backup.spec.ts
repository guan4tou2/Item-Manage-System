import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

async function register(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  expect(res.status()).toBe(201)
}

async function apiToken(request: ApiCtx, username: string) {
  const login = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  return (await login.json()).access_token as string
}

async function loginUi(page: UiPage, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

/** 帳號 A：建分類＋2 物品（1 含 cost／barcode／標籤），回傳匯出 JSON。 */
async function seedSourceBackup(request: ApiCtx, suffix: string) {
  const username = `bk_src_${suffix}`
  await register(request, username)
  const token = await apiToken(request, username)

  const category = await request.post("/api/categories", {
    headers: auth(token),
    data: { name: "露營" },
  })
  expect(category.status()).toBe(201)
  const categoryId = (await category.json()).id as number

  const tent = await request.post("/api/items", {
    headers: auth(token),
    data: {
      name: "帳篷",
      quantity: 2,
      cost: "120.50",
      barcode: "4712345678901",
      category_id: categoryId,
      tag_names: ["重要"],
    },
  })
  expect(tent.status()).toBe(201)
  const bag = await request.post("/api/items", {
    headers: auth(token),
    data: { name: "睡袋", tag_names: ["重要"] },
  })
  expect(bag.status()).toBe(201)

  const exported = await request.get("/api/backup/export", { headers: auth(token) })
  expect(exported.status()).toBe(200)
  return { username, buffer: await exported.body() }
}

async function uploadBackup(page: UiPage, buffer: Buffer, name = "ims-backup.json") {
  await page.locator('input[type="file"]').setInputFiles({
    name,
    mimeType: "application/json",
    buffer,
  })
}

test("匯出下載＋create_only round-trip：B 匯入 A 的備份", async ({ browser, request }) => {
  const suffix = unique()
  const source = await seedSourceBackup(request, suffix)

  // A：設定 → 備份 → 下載備份（Content-Disposition 檔名）
  const pageA = await (await browser.newContext()).newPage()
  await loginUi(pageA, source.username)
  await pageA.goto("/settings/backup")
  const [download] = await Promise.all([
    pageA.waitForEvent("download"),
    pageA.getByRole("button", { name: "下載備份" }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^ims-backup-.+-\d{4}-\d{2}-\d{2}\.json$/)
  await expect(pageA.getByText("備份已開始下載")).toBeVisible()
  await pageA.context().close()

  // B：匯入（預設 create_only，選檔即 dry-run）
  const target = `bk_dst_${suffix}`
  await register(request, target)
  const pageB = await (await browser.newContext()).newPage()
  await loginUi(pageB, target)
  await pageB.goto("/settings/backup")

  await uploadBackup(pageB, source.buffer)

  // 摘要：物品列「現有 0 → 匯入後 2」「建立 2」
  const itemsRow = pageB.locator('tr:has-text("物品")').first()
  await expect(itemsRow.locator("td").nth(0)).toHaveText("物品")
  await expect(itemsRow.locator("td").nth(1)).toHaveText("0")
  await expect(itemsRow.locator("td").nth(2)).toHaveText("2")
  await expect(itemsRow.locator("td").nth(3)).toHaveText("2")

  await pageB.getByRole("button", { name: "確認匯入" }).click()
  await expect(pageB.getByRole("status")).toContainText(
    /匯入完成：建立 \d+ 筆、刪除 0 筆/,
  )

  // 物品與標籤都還原
  await pageB.goto("/items")
  await expect(pageB.getByRole("link", { name: "帳篷" })).toBeVisible()
  await expect(pageB.getByRole("link", { name: "睡袋" })).toBeVisible()
  await expect(pageB.getByRole("button", { name: "重要" })).toBeVisible()
  await pageB.context().close()
})

test("replace：確認字串把關，清空後僅剩備份內容", async ({ browser, request }) => {
  const suffix = unique()
  const source = await seedSourceBackup(request, suffix)

  const target = `bk_rep_${suffix}`
  await register(request, target)
  const token = await apiToken(request, target)
  const stale = await request.post("/api/items", {
    headers: auth(token),
    data: { name: "C 的舊物", quantity: 1 },
  })
  expect(stale.status()).toBe(201)

  const page = await (await browser.newContext()).newPage()
  await loginUi(page, target)
  await page.goto("/settings/backup")

  await page.getByRole("radio", { name: "取代全部（先清空再匯入）" }).click()
  await uploadBackup(page, source.buffer)

  // 紅警示：將刪除 >0 筆
  await expect(page.getByText(/將刪除 [1-9]\d* 筆/)).toBeVisible()

  const confirmInput = page.getByPlaceholder("REPLACE")
  const confirmButton = page.getByRole("button", { name: "確認匯入" })
  await expect(confirmButton).toBeDisabled()
  await confirmInput.fill("WRONG")
  await expect(confirmButton).toBeDisabled()
  await confirmInput.fill("REPLACE")
  await expect(confirmButton).toBeEnabled()
  await confirmButton.click()

  await expect(page.getByRole("status")).toContainText(
    /匯入完成：建立 \d+ 筆、刪除 [1-9]\d* 筆/,
  )

  // C 的舊資料消失、A 的備份完整還原
  await page.goto("/items")
  await expect(page.getByRole("link", { name: "帳篷" })).toBeVisible()
  await expect(page.getByRole("link", { name: "睡袋" })).toBeVisible()
  await expect(page.getByText("C 的舊物")).toHaveCount(0)
  await page.context().close()
})

test("錯誤態：無效 JSON 與缺 format_version 的卡內訊息", async ({ browser, request }) => {
  const username = `bk_err_${unique()}`
  await register(request, username)
  const page = await (await browser.newContext()).newPage()
  await loginUi(page, username)
  await page.goto("/settings/backup")

  await uploadBackup(page, Buffer.from("{ invalid json"), "bad.json")
  await expect(page.getByText("備份檔不是有效的 JSON")).toBeVisible()
  await expect(page.getByText("匯入預覽")).toHaveCount(0)

  await uploadBackup(page, Buffer.from("{}"), "empty.json")
  await expect(
    page.getByText("備份檔缺少有效的 format_version"),
  ).toBeVisible()

  await page.context().close()
})
