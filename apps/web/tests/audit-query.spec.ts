import { execSync } from "node:child_process"
import fs from "node:fs/promises"
import path from "node:path"

import { expect, test } from "@playwright/test"

/**
 * Phase 39：稽核查詢台 e2e。
 *
 * 只走既有事件：管理員停用帳號會寫入 `admin.user.set_active`（resource_type=user）。
 * 驗證篩選、關鍵字（resource_id）、CSV 匯出與非管理員守衛。
 */

const PASSWORD = "secret1234"
const ADMIN_USERNAME = "e2e_audit_admin"
const unique = () => Date.now().toString()

async function ensureAdminToken(
  request: import("@playwright/test").APIRequestContext,
): Promise<string> {
  await request.post("/api/auth/register", {
    data: {
      email: `${ADMIN_USERNAME}@t.io`,
      username: ADMIN_USERNAME,
      password: PASSWORD,
    },
  })
  const login = await request.post("/api/auth/login", {
    data: { username: ADMIN_USERNAME, password: PASSWORD },
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

async function loginUi(
  page: import("@playwright/test").Page,
  username: string,
): Promise<void> {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("admin filters, searches, and exports audit logs", async ({ page, request }) => {
  const adminToken = await ensureAdminToken(request)
  const adminHeaders = { Authorization: `Bearer ${adminToken}` }

  // 產生一筆稽核事件：停用一個新帳號
  const targetName = `e2e_audit_target_${unique()}`
  await request.post("/api/auth/register", {
    data: { email: `${targetName}@t.io`, username: targetName, password: PASSWORD },
  })
  const users = (
    await request.get("/api/admin/users", { headers: adminHeaders })
  ).json() as Promise<Array<{ id: string; username: string }>>
  const target = (await users).find((user) => user.username === targetName)
  expect(target).toBeTruthy()

  const deactivate = await request.patch(`/api/admin/users/${target!.id}`, {
    headers: adminHeaders,
    data: { is_active: false },
  })
  expect(deactivate.status()).toBe(200)

  await loginUi(page, ADMIN_USERNAME)
  await page.goto("/settings/audit")

  const table = page.getByTestId("audit-table")
  await expect(table).toBeVisible()
  await expect(table.getByText("admin.user.set_active").first()).toBeVisible()

  // 依動作篩選
  await page.getByRole("combobox", { name: "動作" }).click()
  // Phase 40：新事件（登入）不需改 UI，會自動出現在 facets 下拉
  await expect(
    page.getByRole("option", { name: "auth.login", exact: true }),
  ).toBeVisible()
  await page.getByRole("option", { name: "admin.user.set_active", exact: true }).click()
  const actionCells = table.locator("tbody tr td:nth-child(3)")
  await expect(actionCells.first()).toHaveText("admin.user.set_active")
  const filtered = await actionCells.allTextContents()
  expect(filtered.length).toBeGreaterThan(0)
  expect(filtered.every((value) => value === "admin.user.set_active")).toBe(true)

  // 清除篩選後以 resource_id 前綴搜尋（q 涵蓋 resource_id）
  await page.getByRole("button", { name: "清除篩選" }).click()
  const prefix = target!.id.slice(0, 8)
  await page.getByLabel("搜尋").fill(prefix)
  await expect(table.getByText(`user / ${prefix}`).first()).toBeVisible({ timeout: 10_000 })

  // 匯出當前篩選（CSV 需含 BOM 與表頭）
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "匯出 CSV" }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^audit-logs-\d{8}\.csv$/)
  const filePath = await download.path()
  expect(filePath).toBeTruthy()
  const content = await fs.readFile(filePath!, "utf8")
  expect(content.startsWith("\ufeff")).toBe(true)
  expect(content.split("\n")[0].replace("\ufeff", "")).toBe(
    "created_at,user_email,user_id,action,resource_type,resource_id,meta",
  )
  expect(content).toContain("admin.user.set_active")
  expect(content).toContain(target!.id)
})

test("non-admin cannot open the audit page or query the API", async ({ page, request }) => {
  const username = `e2e_audit_regular_${unique()}`
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  const login = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  expect(login.status()).toBe(200)
  const token = ((await login.json()) as { access_token: string }).access_token
  const headers = { Authorization: `Bearer ${token}` }

  const list = await request.get("/api/admin/audit-logs", { headers })
  expect(list.status()).toBe(403)
  const exported = await request.get("/api/admin/audit-logs/export.csv", { headers })
  expect(exported.status()).toBe(403)

  await loginUi(page, username)
  await page.goto("/settings/audit")
  await expect(page.getByText("此頁僅限管理員檢視。")).toBeVisible()
  await expect(page.getByTestId("audit-table")).toHaveCount(0)
})
