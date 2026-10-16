import { execSync } from "node:child_process"
import path from "node:path"

import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

const ADMIN_USERNAME = "e2e_jobs_admin"
const ADMIN_PASSWORD = "secret1234"

/** 到期日以台北時區計算（app 的 days_left 以 Asia/Taipei 為基準）。 */
const taipeiDatePlusDays = (days: number) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(
    new Date(Date.now() + days * 86_400_000),
  )

async function register(
  request: import("@playwright/test").APIRequestContext,
  username: string,
) {
  const email = `${username}@t.io`
  const password = "secret1234"
  const reg = await request.post("/api/auth/register", {
    data: { email, username, password },
  })
  expect(reg.status()).toBe(201)
  return { username, password }
}

async function loginUi(
  page: import("@playwright/test").Page,
  username: string,
  password: string,
) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

async function loginApi(
  request: import("@playwright/test").APIRequestContext,
  username: string,
): Promise<string> {
  const login = await request.post("/api/auth/login", {
    data: { username, password: "secret1234" },
  })
  expect(login.status()).toBe(200)
  return ((await login.json()) as { access_token: string }).access_token
}

/**
 * 觸發 job 需要管理員。`bootstrap-admin` 只在系統尚無管理員時成功；e2e 資料庫
 * 是長期沿用的開發庫，先前的執行可能已建立其他管理員（409，且其密碼未知）。
 * 此時以 SQL 直接預置本測試帳號為管理員——這是測試前置狀態，非受測行為；
 * 首次在乾淨資料庫上執行會走 bootstrap 正規路徑。
 */
async function ensureAdminToken(
  request: import("@playwright/test").APIRequestContext,
): Promise<string> {
  await request.post("/api/auth/register", {
    data: {
      email: `${ADMIN_USERNAME}@t.io`,
      username: ADMIN_USERNAME,
      password: ADMIN_PASSWORD,
    },
  })
  const login = await request.post("/api/auth/login", {
    data: { username: ADMIN_USERNAME, password: ADMIN_PASSWORD },
  })
  expect(login.status()).toBe(200)
  const token = ((await login.json()) as { access_token: string }).access_token
  const headers = { Authorization: `Bearer ${token}` }

  const me = await request.get("/api/users/me", { headers })
  if (((await me.json()) as { is_admin: boolean }).is_admin) return token

  const boot = await request.post("/api/auth/bootstrap-admin", { headers })
  if (boot.status() === 200) return token

  execSync(
    `docker compose exec -T postgres psql -U ims -d ims -c ` +
      `"UPDATE users SET is_admin = true WHERE username = '${ADMIN_USERNAME}'"`,
    { cwd: path.resolve(process.cwd(), "../.."), stdio: "pipe" },
  )
  return token
}

test("到期掃描：級別補發 → 彙總通知 → deep link → 儀表板註記 → 同日不重發", async ({
  page,
  request,
}) => {
  const suffix = unique()
  const username = `rem1_${suffix}`
  const itemName = `到期奶 ${suffix}`

  const { username: u, password } = await register(request, username)
  await loginUi(page, u, password)
  const auth = { Authorization: `Bearer ${await loginApi(request, u)}` }

  // 進貨：1 件、3 天後到期（落 d30＋d7 補發窗）
  const created = await request.post("/api/items", {
    headers: auth,
    data: { name: itemName, quantity: 1 },
  })
  expect(created.status()).toBe(201)
  const item = (await created.json()) as { id: string }
  const batch = await request.post(`/api/items/${item.id}/batches`, {
    headers: auth,
    data: { quantity: 1, expiry_date: taipeiDatePlusDays(3) },
  })
  expect(batch.status()).toBe(201)

  // 管理員觸發掃描（cron 語義）
  const admin = await ensureAdminToken(request)
  const run = await request.post("/api/jobs/expiry-scan/run", {
    headers: { Authorization: `Bearer ${admin}` },
  })
  expect(run.status()).toBe(200)
  const first = (await run.json()) as {
    status: string
    processed: number
    emitted: number
  }
  expect(first.status).toBe("succeeded")
  expect(first.processed).toBeGreaterThanOrEqual(2) // d30 + d7
  expect(first.emitted).toBeGreaterThanOrEqual(1)

  // 狀態查詢：任何登入者可讀；剛跑完 → 非停跑
  const status = await request.get("/api/jobs/expiry-scan/status", {
    headers: auth,
  })
  expect(status.status()).toBe(200)
  const statusBody = (await status.json()) as {
    stale: boolean
    last_run: { status: string } | null
  }
  expect(statusBody.stale).toBe(false)
  expect(statusBody.last_run?.status).toBe("succeeded")

  // 通知中心：本使用者恰好一則彙總（含最急指引）
  await page.goto("/notifications")
  const digest = page.getByRole("listitem", { name: "1 件物品即將到期" })
  await expect(digest).toHaveCount(1)
  await expect(digest).toContainText(itemName)
  await expect(digest).toContainText("剩 3 天")

  // 點擊 → deep link 落點：到期檢視
  await digest.getByRole("button", { name: "Open notification" }).click()
  await page.waitForURL(/\/items\?sort=expiry_asc/)
  await expect(
    page.getByRole("row", { name: new RegExp(itemName) }),
  ).toContainText("剩 3 天")

  // 儀表板到期卡註記
  await page.goto("/dashboard")
  await expect(page.getByTestId("expiry-card-reminded")).toContainText(
    "今天已彙總提醒",
  )

  // 同日重跑：不重發（本使用者仍恰好一則）
  const rerun = await request.post("/api/jobs/expiry-scan/run", {
    headers: { Authorization: `Bearer ${admin}` },
  })
  expect(rerun.status()).toBe(200)
  expect(((await rerun.json()) as { status: string }).status).toBe("succeeded")
  await page.goto("/notifications")
  await expect(
    page.getByRole("listitem", { name: "1 件物品即將到期" }),
  ).toHaveCount(1)
})

test("job 觸發權限：匿名 401、非管理員 403、未知 job 404；狀態任何登入者可讀", async ({
  request,
}) => {
  const suffix = unique()
  const { username } = await register(request, `rem2_${suffix}`)
  const auth = { Authorization: `Bearer ${await loginApi(request, username)}` }

  const anon = await request.post("/api/jobs/expiry-scan/run")
  expect(anon.status()).toBe(401)

  const nonAdmin = await request.post("/api/jobs/expiry-scan/run", {
    headers: auth,
  })
  expect(nonAdmin.status()).toBe(403)

  const admin = await ensureAdminToken(request)
  const unknown = await request.post("/api/jobs/nope/run", {
    headers: { Authorization: `Bearer ${admin}` },
  })
  expect(unknown.status()).toBe(404)

  const okStatus = await request.get("/api/jobs/expiry-scan/status", {
    headers: auth,
  })
  expect(okStatus.status()).toBe(200)
  const unknownStatus = await request.get("/api/jobs/nope/status", {
    headers: auth,
  })
  expect(unknownStatus.status()).toBe(404)
})

test("設定頁提醒排程：IA 入口、門檻與上次執行（唯讀）", async ({
  page,
  request,
}) => {
  const suffix = unique()
  const { username, password } = await register(request, `rem3_${suffix}`)

  const admin = await ensureAdminToken(request)
  const run = await request.post("/api/jobs/expiry-scan/run", {
    headers: { Authorization: `Bearer ${admin}` },
  })
  expect(run.status()).toBe(200)

  await loginUi(page, username, password)
  await page.goto("/settings")
  await page.getByRole("link", { name: "提醒排程" }).click()
  await page.waitForURL("**/settings/reminders")

  await expect(page.getByRole("heading", { name: "提醒排程" })).toBeVisible()
  await expect(page.getByText("到期前 30 天提醒")).toBeVisible()
  await expect(page.getByText("到期前 7 天提醒")).toBeVisible()
  await expect(page.getByText("到期當天提醒")).toBeVisible()
  await expect(page.getByText("過期後每日提醒，至過期 14 天止")).toBeVisible()
  await expect(page.getByText("成功")).toBeVisible()
  await expect(
    page.getByText("提醒排程尚未執行過——請設定外部 cron 每日呼叫。"),
  ).toHaveCount(0)
})
