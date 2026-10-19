import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

/** 1×1 PNG（無 API key 時一律走失敗路徑，不需可讀內容）。 */
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==",
  "base64",
)

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

async function signIn(request: ApiCtx, page: UiPage) {
  const username = `rcpt_${unique()}`
  await register(request, username)
  await loginUi(page, username)
}

const cards = (page: UiPage) => page.locator('[data-testid^="draft-card-"]')

test("收據模式：無 API key → 顯示錯誤且不產生草稿", async ({ page, request }) => {
  await signIn(request, page)
  await page.goto("/items/drafts")

  // 預設為照片模式
  await expect(page.getByTestId("draft-upload-zone").getByText("上傳照片")).toBeVisible()
  await expect(page.getByRole("button", { name: "選擇照片" })).toBeVisible()

  // 切到收據模式
  await page.getByRole("tab", { name: "收據" }).click()
  await expect(page.getByTestId("draft-upload-zone").getByText("收據辨識")).toBeVisible()
  await expect(
    page.getByText("選擇同一次採購的所有頁面；一次最多 10 頁"),
  ).toBeVisible()

  // 選 2 頁 → 上傳 → 抽取失敗（無 key）
  await page.locator('input[type="file"]').setInputFiles(
    ["page1.png", "page2.png"].map((name) => ({
      name,
      mimeType: "image/png",
      buffer: PNG,
    })),
  )

  await expect(page.getByTestId("draft-upload-zone").getByRole("alert")).toContainText(
    "AI 未設定（缺少 API 金鑰）；無法辨識收據",
    { timeout: 15_000 },
  )
  // 失敗不產生任何草稿
  await expect(cards(page)).toHaveCount(0)
  await expect(page.getByText("尚無草稿")).toBeVisible()
})

test("收據模式：抽取失敗後保留頁面並可重試", async ({ page, request }) => {
  await signIn(request, page)
  await page.goto("/items/drafts")
  await page.getByRole("tab", { name: "收據" }).click()

  await page
    .locator('input[type="file"]')
    .setInputFiles([{ name: "page1.png", mimeType: "image/png", buffer: PNG }])

  await expect(page.getByTestId("draft-upload-zone").getByRole("alert")).toContainText("無法辨識收據", {
    timeout: 15_000,
  })
  // 已上傳的頁面仍在清單中（可重試，不必重選）
  await expect(page.getByTestId("upload-file-0")).toBeVisible()
  await expect(page.getByTestId("upload-file-0")).toContainText("已上傳")

  await page.getByRole("button", { name: "重試" }).click()
  await expect(page.getByTestId("draft-upload-zone").getByRole("alert")).toContainText("無法辨識收據", {
    timeout: 15_000,
  })
  await expect(cards(page)).toHaveCount(0)
})

test("收據模式：切回照片模式後行為不變", async ({ page, request }) => {
  await signIn(request, page)
  await page.goto("/items/drafts")

  await page.getByRole("tab", { name: "收據" }).click()
  await expect(page.getByTestId("draft-upload-zone").getByText("收據辨識")).toBeVisible()

  await page.getByRole("tab", { name: "照片" }).click()
  await expect(page.getByTestId("draft-upload-zone").getByText("上傳照片")).toBeVisible()
  await expect(page.getByRole("button", { name: "選擇照片" })).toBeVisible()

  // 照片模式仍會建立草稿（無 key → 失敗態）
  await page
    .locator('input[type="file"]')
    .setInputFiles([{ name: "photo.png", mimeType: "image/png", buffer: PNG }])

  await expect(cards(page)).toHaveCount(1)
  await expect(cards(page).first().getByTestId("draft-status")).toContainText("辨識失敗", {
    timeout: 15_000,
  })
})

test("收據模式：入口徽章在失敗後仍為 0", async ({ page, request }) => {
  await signIn(request, page)
  await page.goto("/items/drafts")
  await page.getByRole("tab", { name: "收據" }).click()
  await page
    .locator('input[type="file"]')
    .setInputFiles([{ name: "page1.png", mimeType: "image/png", buffer: PNG }])
  await expect(page.getByTestId("draft-upload-zone").getByRole("alert")).toContainText("無法辨識收據", {
    timeout: 15_000,
  })

  await page.goto("/items/new")
  await expect(page.getByTestId("batch-entry-card")).toBeVisible()
  await expect(page.getByTestId("batch-entry-badge")).toHaveCount(0)
})
