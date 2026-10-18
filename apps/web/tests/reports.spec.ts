import { execSync } from "node:child_process"
import path from "node:path"

import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

const ADMIN_USERNAME = "e2e_jobs_admin"
const ADMIN_PASSWORD = "secret1234"

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

/** 觸發 job 需要管理員；沿用到期掃描 spec 的 bootstrap→SQL 保底流程。 */
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

async function runMonthlyReportJob(
  request: import("@playwright/test").APIRequestContext,
  token: string,
) {
  const run = await request.post("/api/jobs/report.monthly/run", {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(run.status()).toBe(200)
  const body = (await run.json()) as { status: string; processed: number }
  expect(body.status).toBe("succeeded")
  return body
}

const webPeriodLabel = (period: string) => {
  const [year, month] = period.split("-").map((part) => Number(part))
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, 1, 12)))
}

/**
 * 月報只計「上一個完整月」的動態；e2e 使用者是剛註冊的，物品 created_at 落在
 * 當月。為了驗證動態與通知路徑，把物品的 created_at 回填到該期間（測試前置
 * 狀態，非受測行為——API 無此欄位的寫入面）。
 */
function backdateItemToPeriod(itemId: string, period: string) {
  execSync(
    `docker compose exec -T postgres psql -U ims -d ims -c ` +
      `"UPDATE items SET created_at = '${period}-05T02:00:00Z' WHERE id = '${itemId}'"`,
    { cwd: path.resolve(process.cwd(), "../.."), stdio: "pipe" },
  )
}

/** 以台北時區推得「上一個完整月」（與 `report.monthly` 一致）。 */
function previousPeriodTaipei(): string {
  const current = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
  }).format(new Date()) // YYYY-MM
  const [year, month] = current.split("-").map((part) => Number(part))
  const previous = new Date(Date.UTC(year, month - 2, 1, 10))
  return previous.toISOString().slice(0, 7)
}

/** 伺服器端（通知／Email）的 zh-TW 週期標籤：`2026 年 9 月`。 */
const serverPeriodLabel = (period: string) => {
  const [year, month] = period.split("-").map((part) => Number(part))
  return `${year} 年 ${month} 月`
}

test("月報：job 生成、通知 deep link、詳情頁與冪等重跑", async ({ page, request }) => {
  const suffix = unique()
  const username = `rep1_${suffix}`
  const itemName = `月報物品 ${suffix}`

  const { username: u, password } = await register(request, username)
  await loginUi(page, u, password)
  const auth = { Authorization: `Bearer ${await loginApi(request, u)}` }

  const created = await request.post("/api/items", {
    headers: auth,
    data: { name: itemName, quantity: 2 },
  })
  expect(created.status()).toBe(201)
  const itemId = ((await created.json()) as { id: string }).id
  const expectedPeriod = previousPeriodTaipei()
  backdateItemToPeriod(itemId, expectedPeriod)

  // 管理員觸發月報 job（cron 語義）：上一個完整月
  const admin = await ensureAdminToken(request)
  const first = await runMonthlyReportJob(request, admin)
  expect(first.processed).toBeGreaterThanOrEqual(1)

  // API：只回本人、週期為 YYYY-MM
  const list = await request.get("/api/reports", { headers: auth })
  expect(list.status()).toBe(200)
  const body = (await list.json()) as {
    items: Array<{ id: string; period: string }>
    total: number
  }
  expect(body.total).toBe(1)
  const report = body.items[0]!
  expect(report.period).toBe(expectedPeriod)

  // 清單頁：週期卡＋摘要
  await page.goto("/reports")
  const card = page.getByRole("link", { name: new RegExp(webPeriodLabel(report.period)) })
  await expect(card).toBeVisible()
  await expect(page.getByTestId("report-summary").first()).toContainText("新增")

  // 站內通知：deep link 落點為詳情頁
  await page.goto("/notifications")
  const notice = page.getByRole("listitem", {
    name: `月報已生成：${serverPeriodLabel(report.period)}`,
  })
  await expect(notice).toHaveCount(1)
  await notice.getByRole("button", { name: "Open notification" }).click()
  await page.waitForURL(`**/reports/${report.id}`)
  await expect(page.getByTestId("report-inventory")).toBeVisible()
  await expect(page.getByTestId("report-valuation")).toContainText("庫存估值")

  // 冪等：同日重跑不新增列、不重發通知
  await runMonthlyReportJob(request, admin)
  const rerunList = await request.get("/api/reports", { headers: auth })
  expect(((await rerunList.json()) as { total: number }).total).toBe(1)
  await page.goto("/reports")
  await expect(page.getByTestId("report-summary")).toHaveCount(1)
  await page.goto("/notifications")
  await expect(
    page.getByRole("listitem", {
      name: `月報已生成：${serverPeriodLabel(report.period)}`,
    }),
  ).toHaveCount(1)
})

test("月報：空資料使用者跳過；開關關閉不生成、重新開啟後生成", async ({
  page,
  request,
}) => {
  const suffix = unique()
  const username = `rep2_${suffix}`
  const itemName = `月報開關 ${suffix}`

  const { username: u, password } = await register(request, username)
  await loginUi(page, u, password)
  const auth = { Authorization: `Bearer ${await loginApi(request, u)}` }

  // 尚未建立任何物品 → 首月空狀態（無設定連結）
  await page.goto("/reports")
  await expect(page.getByText("還沒有月報")).toBeVisible()
  await expect(page.getByText("第一份月報將於次月 1 日生成")).toBeVisible()

  // 建立物品後關閉月報總開關
  const created = await request.post("/api/items", {
    headers: auth,
    data: { name: itemName, quantity: 1 },
  })
  expect(created.status()).toBe(201)

  await page.goto("/settings/reports")
  const toggle = page.getByRole("switch", { name: "每月報表" })
  await expect(toggle).toBeChecked()
  await toggle.click()
  await expect(page.getByText("月報已關閉")).toBeVisible()
  await expect(toggle).not.toBeChecked()

  // 關閉後：job 跳過、API 無列
  const admin = await ensureAdminToken(request)
  await runMonthlyReportJob(request, admin)
  const offList = await request.get("/api/reports", { headers: auth })
  expect(((await offList.json()) as { total: number }).total).toBe(0)

  // 清單頁：關閉說明＋設定連結
  await page.goto("/reports")
  await expect(page.getByText("已關閉月報的生成與寄送")).toBeVisible()
  await expect(page.getByRole("link", { name: "前往月報設定" })).toHaveAttribute(
    "href",
    "/settings/reports",
  )

  // 重新開啟 → 再跑 job → 報表出現
  await page.goto("/settings/reports")
  await page.getByRole("switch", { name: "每月報表" }).click()
  await expect(page.getByText("月報已開啟")).toBeVisible()

  await runMonthlyReportJob(request, admin)
  const onList = await request.get("/api/reports", { headers: auth })
  const onBody = (await onList.json()) as {
    items: Array<{ period: string }>
    total: number
  }
  expect(onBody.total).toBe(1)

  await page.goto("/reports")
  await expect(
    page.getByRole("link", {
      name: new RegExp(webPeriodLabel(onBody.items[0]!.period)),
    }),
  ).toBeVisible()
})

test("導覽：桌面統計下拉與行動二層群組皆可到達報表", async ({ page, request }) => {
  const suffix = unique()
  const username = `rep3_${suffix}`
  const { username: u, password } = await register(request, username)
  await loginUi(page, u, password)

  // 桌面：統計下拉 → 報表；觸發器 active
  await page.getByRole("button", { name: "統計" }).click()
  await page.getByRole("menuitem", { name: "報表" }).click()
  await page.waitForURL("**/reports")
  await expect(page.getByRole("button", { name: "統計" })).toHaveClass(/bg-accent/)

  // 行動：drawer 四群組、分析群組 → 報表
  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto("/dashboard")
  await page.getByRole("button", { name: /開啟選單/ }).click()
  const drawer = page.getByRole("dialog")
  await expect(drawer.getByTestId("nav-group-header-analysis")).toContainText("分析")
  await expect(drawer.getByTestId("nav-group-header-collab")).toContainText("協作")
  await expect(drawer.getByTestId("nav-group-header-system")).toContainText("系統")
  await drawer
    .getByTestId("nav-group-items-analysis")
    .getByRole("button", { name: "報表", exact: true })
    .click()
  await page.waitForURL("**/reports")
  await expect(page.getByRole("dialog")).toHaveCount(0)
})
