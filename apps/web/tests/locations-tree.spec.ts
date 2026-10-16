import { expect, test } from "@playwright/test"

/**
 * Phase 26 位置樹 e2e：樹管理（建立／改名／拖放／刪除限制／鍵盤）、
 * 樹狀選擇器與篩選語義、行動版搬移，以及**真實遷移後的資料在 UI 呈現**。
 */

const unique = () => Date.now().toString() + Math.floor(Math.random() * 1000)
const PASSWORD = "secret1234"

async function register(
  request: import("@playwright/test").APIRequestContext,
  username: string,
) {
  const res = await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  expect(res.status()).toBe(201)
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

async function loginApi(
  request: import("@playwright/test").APIRequestContext,
  username: string,
): Promise<string> {
  const login = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  expect(login.status()).toBe(200)
  return ((await login.json()) as { access_token: string }).access_token
}

async function seedTree(
  request: import("@playwright/test").APIRequestContext,
  token: string,
): Promise<{ floor: number; kitchen: number; shelf: number; second: number }> {
  const headers = { Authorization: `Bearer ${token}` }
  const post = async (body: Record<string, unknown>) => {
    const res = await request.post("/api/locations", { headers, data: body })
    expect(res.status()).toBe(201)
    return (await res.json()) as { id: number }
  }
  const floor = await post({ name: "1F", kind: "floor", sort_order: 0 })
  const kitchen = await post({ name: "廚房", parent_id: floor.id, kind: "room" })
  const shelf = await post({ name: "上櫃", parent_id: kitchen.id })
  const second = await post({ name: "2F", kind: "floor", sort_order: 1 })
  return { floor: floor.id, kitchen: kitchen.id, shelf: shelf.id, second: second.id }
}

async function seedItem(
  request: import("@playwright/test").APIRequestContext,
  token: string,
  body: { name: string; location_id?: number },
) {
  const res = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { quantity: 1, ...body },
  })
  expect(res.status()).toBe(201)
  return (await res.json()) as { id: string }
}

const row = (page: import("@playwright/test").Page, name: string) =>
  page.locator('[role="treeitem"]', { hasText: name }).first()

/** 展開所有可展開節點（樹預設收合；先等樹渲染完成）。 */
async function expandAll(page: import("@playwright/test").Page) {
  await page.getByRole("treeitem").first().waitFor({ state: "visible" })
  for (let i = 0; i < 12; i += 1) {
    const button = page.getByRole("button", { name: "展開" }).first()
    if ((await button.count()) === 0) return
    await button.click()
  }
}

test("建立三層樹並可展開收合", async ({ page, request }) => {
  const username = `tree_build_${unique()}`
  await register(request, username)
  await loginUi(page, username)

  await page.goto("/locations")
  await page.getByLabel("新位置名稱").fill("1F")
  await page.getByRole("button", { name: "新增位置" }).click()

  await row(page, "1F").getByRole("button", { name: "1F 的更多操作" }).click()
  await page.getByRole("menuitem", { name: "新增子節點" }).click()
  await page.getByLabel("新增子節點").fill("廚房")
  await page.getByLabel("新增子節點").press("Enter")

  await row(page, "廚房").getByRole("button", { name: "廚房 的更多操作" }).click()
  await page.getByRole("menuitem", { name: "新增子節點" }).click()
  await page.getByLabel("新增子節點").fill("上櫃")
  await page.getByLabel("新增子節點").press("Enter")

  await expect(row(page, "上櫃")).toBeVisible()

  // 收合 1F → 子樹隱藏；再展開
  await row(page, "1F").getByRole("button", { name: "收合" }).click()
  await expect(row(page, "上櫃")).toHaveCount(0)
  await row(page, "1F").getByRole("button", { name: "展開" }).click()
  await expect(row(page, "上櫃")).toBeVisible()
})

test("改名以 F2 進行並在重新載入後保留", async ({ page, request }) => {
  const username = `tree_rename_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedTree(request, token)
  await loginUi(page, username)

  await page.goto("/locations")
  await row(page, "1F").click()
  await page.keyboard.press("F2")
  await page.getByLabel("改名").fill("一樓")
  await page.keyboard.press("Enter")
  await expect(row(page, "一樓")).toBeVisible()

  await page.reload()
  await expect(row(page, "一樓")).toBeVisible()
})

test("桌面拖放搬移節點，非法目標即時灰化", async ({ page, request }) => {
  const username = `tree_drag_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedTree(request, token)
  await loginUi(page, username)

  await page.goto("/locations")
  await expandAll(page)
  await expect(row(page, "上櫃")).toBeVisible()

  // HTML5 DnD：以合成事件驅動（Playwright 的 mouse-based drag 不觸發 dragstart）
  const dataTransfer = await page.evaluateHandle(() => new DataTransfer())

  // 非法：把 1F 拖到自己的子孫（廚房）→ 目標灰化且不搬移
  await row(page, "1F").dispatchEvent("dragstart", { dataTransfer })
  await row(page, "廚房").dispatchEvent("dragover", { dataTransfer })
  await expect(row(page, "廚房")).toHaveAttribute("data-drop-invalid", "true")
  await row(page, "廚房").dispatchEvent("drop", { dataTransfer })
  expect(await locationPath(request, token, "上櫃")).toBe("1F / 廚房 / 上櫃")

  // 合法：把 上櫃 拖到 2F → 路徑更新
  await row(page, "上櫃").dispatchEvent("dragstart", { dataTransfer })
  await row(page, "2F").dispatchEvent("dragover", { dataTransfer })
  await row(page, "2F").dispatchEvent("drop", { dataTransfer })
  await expect
    .poll(() => locationPath(request, token, "上櫃"))
    .toBe("2F / 上櫃")
})

/** 依節點名稱取當前路徑（樹操作結果以 API 驗證，避免依賴畫面文字）。 */
async function locationPath(
  request: import("@playwright/test").APIRequestContext,
  token: string,
  name: string,
): Promise<string> {
  const res = await request.get("/api/locations", {
    headers: { Authorization: `Bearer ${token}` },
  })
  const rows = (await res.json()) as Array<{ id: number; name: string; path: string }>
  return rows.find((entry) => entry.name === name)?.path ?? ""
}

test("刪除受限節點：先搬移物品再刪除", async ({ page, request }) => {
  const username = `tree_delete_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  const tree = await seedTree(request, token)
  await seedItem(request, token, { name: "牛奶", location_id: tree.shelf })
  await seedItem(request, token, { name: "雞蛋", location_id: tree.shelf })
  await loginUi(page, username)

  await page.goto("/locations")
  await expandAll(page)
  await row(page, "上櫃").getByRole("button", { name: "上櫃 的更多操作" }).click()
  await page.getByRole("menuitem", { name: "刪除" }).click()

  await expect(page.getByText("此位置有 2 件物品。")).toBeVisible()
  await expect(page.getByRole("button", { name: "刪除" })).toBeDisabled()

  // 先搬移物品 → 2F
  await page.getByLabel("搬移目標 1").click()
  await page.getByRole("option", { name: "2F" }).click()
  await page.getByRole("button", { name: "搬移 2 件物品" }).click()

  // 對話框關閉；再次開啟即可刪除
  await row(page, "上櫃").getByRole("button", { name: "上櫃 的更多操作" }).click()
  await page.getByRole("menuitem", { name: "刪除" }).click()
  await expect(page.getByRole("button", { name: "刪除" })).toBeEnabled()
  await page.getByRole("button", { name: "刪除" }).click()

  await expect(row(page, "上櫃")).toHaveCount(0)

  // 物品確實換了位置
  const items = await request.get("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
  })
  const listed = (await items.json()) as {
    items: Array<{ name: string; location: { path: string } | null }>
  }
  expect(listed.items.find((item) => item.name === "牛奶")?.location?.path).toBe("2F")
})

test("物品表單 cascading 選取三層，詳情顯示截斷麵包屑", async ({ page, request }) => {
  const username = `tree_form_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  await seedTree(request, token)
  await loginUi(page, username)

  await page.goto("/items/new")
  await page.getByLabel("名稱").fill("螺絲起子")
  await page.getByLabel("位置 1").click()
  await page.getByRole("option", { name: "1F" }).click()
  await page.getByLabel("位置 2").click()
  await page.getByRole("option", { name: "廚房" }).click()
  await page.getByLabel("位置 3").click()
  await page.getByRole("option", { name: "上櫃" }).click()
  await expect(page.getByTestId("location-select-path")).toHaveText("1F / 廚房 / 上櫃")
  await page.getByRole("button", { name: "儲存" }).click()

  await page.waitForURL(/\/items\/[0-9a-f-]{36}$/)
  const path = page.getByTestId("item-location-path")
  await expect(path).toHaveText("1F / 廚房 / 上櫃")
  await expect(path).toHaveAttribute("title", "1F / 廚房 / 上櫃")
})

test("篩選父節點預設含子孫，「僅此層」只留直接物品", async ({ page, request }) => {
  const username = `tree_filter_${unique()}`
  await register(request, username)
  const token = await loginApi(request, username)
  const tree = await seedTree(request, token)
  await seedItem(request, token, { name: "在樓層的物品", location_id: tree.floor })
  await seedItem(request, token, { name: "在櫃子的物品", location_id: tree.shelf })
  await loginUi(page, username)

  await page.goto(`/items?location=${tree.floor}`)
  await expect(page.getByText("在樓層的物品")).toBeVisible()
  await expect(page.getByText("在櫃子的物品")).toBeVisible()

  await page.getByRole("checkbox", { name: "僅此層" }).click()
  await page.waitForURL(/location_scope=exact/)
  await expect(page.getByText("在樓層的物品")).toBeVisible()
  await expect(page.getByText("在櫃子的物品")).toHaveCount(0)
})

test.describe("行動版搬移（390 寬）", () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test("⋯ 選單 → 搬移至 → 搜尋選父", async ({ page, request }) => {
    const username = `tree_mobile_${unique()}`
    await register(request, username)
    const token = await loginApi(request, username)
    await seedTree(request, token)
    await loginUi(page, username)

    await page.goto("/locations")
    await expandAll(page)
    await row(page, "上櫃").getByRole("button", { name: "上櫃 的更多操作" }).click()
    await page.getByRole("menuitem", { name: "搬移至…" }).click()

    await page.getByLabel("搜尋目標位置").fill("2F")
    await page.getByRole("button", { name: /^2F$/ }).first().click()

    await expect
      .poll(() => locationPath(request, token, "上櫃"))
      .toBe("2F / 上櫃")
  })
})

test("真實遷移後的位置樹在 UI 正確呈現（唯讀）", async ({ page, request }) => {
  // dev 庫的 phase26_demo：遷移前為 1F/廚房/{上櫃,冰箱}、2F/書房、3F
  await loginUi(page, "phase26_demo")
  await page.goto("/locations")
  await expandAll(page)

  await expect(row(page, "1F")).toBeVisible()
  await expect(row(page, "上櫃")).toBeVisible()
  await expect(row(page, "冰箱")).toBeVisible()
  await expect(row(page, "書房")).toBeVisible()
  await expect(row(page, "上櫃").getByText("2 件")).toBeVisible()
})
