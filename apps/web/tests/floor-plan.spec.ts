import { expect, test, type APIRequestContext, type Page } from "@playwright/test"

// 執行方式：playwright test tests/floor-plan.spec.ts --workers=1
// 正方形小圖需足夠的桌面高度，讓拖曳起訖點皆在 viewport 內。
test.use({ viewport: { width: 1024, height: 1000 } })
const PASSWORD = "secret1234"
const auth = (token: string) => ({ Authorization: `Bearer ${token}` })
const unique = () => `${Date.now()}${Math.floor(Math.random() * 1000)}`

async function register(request: APIRequestContext, username: string) {
  expect(
    (
      await request.post("/api/auth/register", {
        data: { username, email: `${username}@t.io`, password: PASSWORD },
      })
    ).status(),
  ).toBe(201)
  const login = await request.post("/api/auth/login", { data: { username, password: PASSWORD } })
  expect(login.status()).toBe(200)
  return (await login.json()).access_token as string
}
async function loginUi(page: Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(PASSWORD)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}
async function seed(request: APIRequestContext, token: string, placed = true) {
  const headers = auth(token)
  const location = async (name: string, parent_id?: number) => {
    const res = await request.post("/api/locations", { headers, data: { name, parent_id } })
    expect(res.status()).toBe(201)
    return (await res.json()).id as number
  }
  const floor = await location("一樓")
  const kitchen = await location("廚房", floor)
  const living = await location("客廳", floor)
  for (const [location_id, name] of [
    [kitchen, "廚房專用鍋"],
    [living, "客廳專用燈"],
  ] as const) {
    expect(
      (
        await request.post("/api/items", { headers, data: { name, location_id, quantity: 1 } })
      ).status(),
    ).toBe(201)
  }
  // 小 PNG 直接由位元組建立，不依賴檔案或外部來源。
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1kAAAAASUVORK5CYII=",
    "base64",
  )
  const image = await request.post("/api/images", {
    headers,
    multipart: { file: { name: "plan.png", mimeType: "image/png", buffer: png } },
  })
  expect(image.status()).toBe(201)
  const patch = await request.patch(`/api/locations/${floor}`, {
    headers,
    data: { floor_plan_image_id: (await image.json()).id },
  })
  expect(patch.status()).toBe(200)
  if (placed) {
    for (const [id, x] of [
      [kitchen, 0.05],
      [living, 0.55],
    ]) {
      expect(
        (
          await request.patch(`/api/locations/${id}`, {
            headers,
            data: { plan_region: { x, y: 0.1, w: 0.4, h: 0.4 } },
          })
        ).status(),
      ).toBe(200)
    }
  }
  return { floor, kitchen, living }
}

test("區域連結進入正確位置的物品清單", async ({ page, request }) => {
  const name = `plan_links_${unique()}`
  const token = await register(request, name)
  const { floor, kitchen } = await seed(request, token)
  await loginUi(page, name)
  await page.goto(`/locations/${floor}/plan`)
  await expect(page.getByRole("img", { name: "一樓的平面圖" })).toBeVisible()
  const canvas = page.getByTestId("floor-plan-canvas")
  await canvas.getByRole("link", { name: "廚房，1 件物品" }).click()
  await expect(page).toHaveURL(new RegExp(`/items\\?location=${kitchen}$`))
  await expect(page.getByText("廚房專用鍋", { exact: true })).toBeVisible()
  await expect(page.getByText("客廳專用燈", { exact: true })).toHaveCount(0)
})

test("拖曳標示後重新載入仍保留區域，手機無橫向溢出", async ({ page, request }) => {
  const name = `plan_draw_${unique()}`
  const token = await register(request, name)
  const { floor, kitchen } = await seed(request, token, false)
  await loginUi(page, name)
  await page.goto(`/locations/${floor}/plan`)
  const image = page.getByRole("img", { name: "一樓的平面圖" })
  await expect(image).toBeVisible()
  await page.getByRole("button", { name: "開始標示" }).click()
  await page.getByRole("button", { name: "選取子位置 廚房" }).click()
  const box = await image.boundingBox()
  expect(box).not.toBeNull()
  const saved = page.waitForResponse(
    (res) => res.url().endsWith(`/api/locations/${kitchen}`) && res.request().method() === "PATCH",
  )
  await page.mouse.move(box!.x + box!.width * 0.1, box!.y + box!.height * 0.1)
  await page.mouse.down()
  await page.mouse.move(box!.x + box!.width * 0.4, box!.y + box!.height * 0.5, { steps: 5 })
  await page.mouse.up()
  expect((await saved).status()).toBe(200)
  await page.reload()
  await expect(
    page.getByTestId("floor-plan-canvas").getByRole("link", { name: "廚房，1 件物品" }),
  ).toBeVisible()
  const rows = await request.get("/api/locations", { headers: auth(token) })
  const region = (await rows.json()).find((row: { id: number }) => row.id === kitchen).plan_region
  expect(region.x).toBeCloseTo(0.1, 2)
  expect(region.w).toBeCloseTo(0.3, 2)
  await page.setViewportSize({ width: 375, height: 812 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})

test("viewer 可看圖及區域但不渲染任何編輯入口", async ({ page, request }) => {
  const suffix = unique()
  const viewer = `plan_view_${suffix}`
  const viewerToken = await register(request, viewer)
  // 位置屬於帳號；先建立自己的位置，再加入別人的群組成為唯讀者。
  const { floor } = await seed(request, viewerToken)
  const ownerToken = await register(request, `plan_owner_${suffix}`)
  const group = await request.post("/api/groups", {
    headers: auth(ownerToken),
    data: { name: "平面圖測試" },
  })
  expect(group.status()).toBe(201)
  expect(
    (
      await request.post(`/api/groups/${(await group.json()).id}/members`, {
        headers: auth(ownerToken),
        data: { username: viewer, role: "viewer" },
      })
    ).status(),
  ).toBe(201)
  await loginUi(page, viewer)
  await page.goto(`/locations/${floor}/plan`)
  await expect(page.getByRole("img", { name: "一樓的平面圖" })).toBeVisible()
  await expect(
    page.getByTestId("floor-plan-canvas").getByRole("link", { name: "廚房，1 件物品" }),
  ).toBeVisible()
  for (const action of ["編輯區域", "更換平面圖", "移除平面圖", "上傳平面圖", "開始標示"])
    await expect(page.getByRole("button", { name: action })).toHaveCount(0)
})
