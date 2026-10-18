import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()
const PASSWORD = "secret1234"

type ApiCtx = import("@playwright/test").APIRequestContext
type UiPage = import("@playwright/test").Page

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

async function register(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: PASSWORD },
  })
  expect(res.status()).toBe(201)
}

async function apiToken(request: ApiCtx, username: string) {
  const res = await request.post("/api/auth/login", {
    data: { username, password: PASSWORD },
  })
  return (await res.json()).access_token as string
}

async function loginUi(page: UiPage, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

async function newGroup(request: ApiCtx, token: string, name: string) {
  const res = await request.post("/api/groups", { headers: auth(token), data: { name } })
  expect(res.status()).toBe(201)
  return (await res.json()).id as string
}

async function addMember(
  request: ApiCtx,
  token: string,
  groupId: string,
  username: string,
  role: "admin" | "editor" | "viewer",
) {
  const res = await request.post(`/api/groups/${groupId}/members`, {
    headers: auth(token),
    data: { username, role },
  })
  expect(res.status()).toBe(201)
  return (await res.json()).user_id as string
}

async function memberRole(request: ApiCtx, token: string, groupId: string, username: string) {
  const res = await request.get(`/api/groups/${groupId}`, { headers: auth(token) })
  const group = await res.json()
  return group.members.find((m: { username: string }) => m.username === username)?.role as
    | string
    | undefined
}

test("viewer 旅程：一次性 banner、入口不渲染、後端 403、離開群組後恢復可編輯", async ({
  browser,
  request,
}) => {
  const suffix = unique()
  const owner = `vw_own_${suffix}`
  const viewer = `vw_view_${suffix}`
  await register(request, owner)
  await register(request, viewer)
  const ownerToken = await apiToken(request, owner)
  const viewerToken = await apiToken(request, viewer)

  const created = await request.post("/api/items", {
    headers: auth(ownerToken),
    data: { name: "擁有者的帳篷" },
  })
  expect(created.status()).toBe(201)
  const itemId = (await created.json()).id as string

  // viewer 在加入群組前先擁有自己的物品（加入後仍可列印＝讀取性操作）
  const ownCreated = await request.post("/api/items", {
    headers: auth(viewerToken),
    data: { name: "檢視者的椅子" },
  })
  expect(ownCreated.status()).toBe(201)
  const ownItemId = (await ownCreated.json()).id as string
  const groupId = await newGroup(request, ownerToken, `檢視群組 ${suffix}`)
  await addMember(request, ownerToken, groupId, viewer, "viewer")

  const me = await request.get("/api/users/me", { headers: auth(viewerToken) })
  expect((await me.json()).is_read_only).toBe(true)

  const page = await (await browser.newContext()).newPage()
  await loginUi(page, viewer)

  // §5.5：一次性 banner，關閉後 reload 不再出現
  await expect(page.getByText("你是檢視者", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "我知道了" }).click()
  await expect(page.getByText("你是檢視者", { exact: true })).toHaveCount(0)
  await page.reload()
  await expect(page.getByText("你是檢視者", { exact: true })).toHaveCount(0)

  // 清單：無「新增物品」入口，仍可見群組內物品
  await page.goto("/items")
  await expect(page.getByText("擁有者的帳篷")).toBeVisible()
  await expect(page.getByRole("link", { name: "新增物品" })).toHaveCount(0)

  // 詳情：唯讀徽章＋底部固定句；列印標籤（讀取性）保留
  await page.getByText("擁有者的帳篷").click()
  await page.waitForURL(`**/items/${itemId}`)
  await expect(page.getByText(/由 .+ 分享（唯讀）/)).toBeVisible()
  await expect(
    page.getByText("你是檢視者，如需修改請聯絡群組管理員", { exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("link", { name: "編輯" })).toHaveCount(0)

  // 自己的物品：唯讀仍不可編輯，但列印標籤（讀取性）維持可用
  await page.goto(`/items/${ownItemId}`)
  await expect(page.getByRole("link", { name: "列印標籤" })).toBeVisible()
  await expect(page.getByRole("link", { name: "編輯" })).toHaveCount(0)

  // 後端防線（非依賴 UI）
  const forbidden = await request.post("/api/items", {
    headers: auth(viewerToken),
    data: { name: "不該建立" },
  })
  expect(forbidden.status()).toBe(403)

  // 離開群組 → 解除唯讀（零成員 → 可寫）
  await page.goto(`/collaboration/groups/${groupId}`)
  await page.getByRole("button", { name: "離開群組" }).click()
  await page.waitForURL("**/collaboration")
  await page.goto("/items")
  await expect(page.getByRole("link", { name: "新增物品" })).toBeVisible()

  const meAfter = await request.get("/api/users/me", { headers: auth(viewerToken) })
  expect((await meAfter.json()).is_read_only).toBe(false)
})

test("角色管理：owner 升 editor 為 admin、降回後入口消失、owner 列受保護", async ({
  browser,
  request,
}) => {
  const suffix = unique()
  const owner = `rm_own_${suffix}`
  const editor = `rm_ed_${suffix}`
  await register(request, owner)
  await register(request, editor)
  const ownerToken = await apiToken(request, owner)
  await apiToken(request, editor)

  const groupId = await newGroup(request, ownerToken, `角色群組 ${suffix}`)
  await addMember(request, ownerToken, groupId, editor, "editor")

  const ownerPage = await (await browser.newContext()).newPage()
  await loginUi(ownerPage, owner)
  await ownerPage.goto(`/collaboration/groups/${groupId}`)

  // owner 列永遠是「擁有者」徽章，不提供角色 Select
  await expect(ownerPage.getByRole("combobox", { name: `${owner} 的角色` })).toHaveCount(0)

  await ownerPage.getByRole("combobox", { name: `${editor} 的角色` }).click()
  await ownerPage.getByRole("option", { name: "管理員" }).click()
  await expect
    .poll(() => memberRole(request, ownerToken, groupId, editor))
    .toBe("admin")

  // admin 登入：可管理成員
  const editorPage = await (await browser.newContext()).newPage()
  await loginUi(editorPage, editor)
  await editorPage.goto(`/collaboration/groups/${groupId}`)
  await expect(editorPage.getByRole("button", { name: "加入成員" })).toBeVisible()
  await expect(editorPage.getByRole("combobox", { name: `${editor} 的角色` })).toBeVisible()

  // 降回 editor → 管理入口消失、角色為唯讀徽章
  await ownerPage.getByRole("combobox", { name: `${editor} 的角色` }).click()
  await ownerPage.getByRole("option", { name: "編輯者" }).click()
  await expect
    .poll(() => memberRole(request, ownerToken, groupId, editor))
    .toBe("editor")

  await editorPage.reload()
  await expect(editorPage.getByRole("button", { name: "加入成員" })).toHaveCount(0)
  await expect(editorPage.getByRole("combobox")).toHaveCount(0)
  await expect(editorPage.getByText("編輯者", { exact: true })).toBeVisible()

  // owner 自身 role 列亦不可改（409）
  const me = await request.get("/api/users/me", { headers: auth(ownerToken) })
  const ownerId = (await me.json()).id as string
  const res = await request.patch(`/api/groups/${groupId}/members/${ownerId}`, {
    headers: auth(ownerToken),
    data: { role: "viewer" },
  })
  expect(res.status()).toBe(409)
})

test("越權：editor 不得變更角色、viewer 不得建立群組", async ({ request }) => {
  const suffix = unique()
  const owner = `ab_own_${suffix}`
  const editor = `ab_ed_${suffix}`
  const viewer = `ab_vw_${suffix}`
  await register(request, owner)
  await register(request, editor)
  await register(request, viewer)
  const ownerToken = await apiToken(request, owner)
  const editorToken = await apiToken(request, editor)
  const viewerToken = await apiToken(request, viewer)

  const groupId = await newGroup(request, ownerToken, `越權群組 ${suffix}`)
  await addMember(request, ownerToken, groupId, editor, "editor")
  const viewerId = await addMember(request, ownerToken, groupId, viewer, "viewer")

  const forbidden = await request.patch(`/api/groups/${groupId}/members/${viewerId}`, {
    headers: auth(editorToken),
    data: { role: "admin" },
  })
  expect(forbidden.status()).toBe(403)

  const createAttempt = await request.post("/api/groups", {
    headers: auth(viewerToken),
    data: { name: "不該建立" },
  })
  expect(createAttempt.status()).toBe(403)
})
