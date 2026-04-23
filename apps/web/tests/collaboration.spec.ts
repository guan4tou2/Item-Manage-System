import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", { data: { email: `${username}@t.io`, username, password: "secret1234" } })
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("group + loan + transfer end-to-end", async ({ browser, request }) => {
  const alice = `alice_${unique()}`
  const bob = `bob_${unique()}`
  await register(request, alice)
  await register(request, bob)

  const alicePage = await (await browser.newContext()).newPage()
  await loginUi(alicePage, alice)
  const loginA = await request.post("/api/auth/login", { data: { username: alice, password: "secret1234" } })
  const tokenA = (await loginA.json()).access_token
  const itemA = await request.post("/api/items", { headers: { Authorization: `Bearer ${tokenA}` }, data: { name: "Alice 的傘" } })
  const itemId = (await itemA.json()).id

  await alicePage.goto("/collaboration")
  await alicePage.getByRole("button", { name: "新增群組" }).click()
  await alicePage.getByRole("textbox").first().fill("家人")
  await alicePage.getByRole("button", { name: "建立" }).click()
  await alicePage.waitForURL(/\/collaboration\/groups\//)
  await alicePage.getByRole("button", { name: "加入成員" }).click()
  await alicePage.getByRole("textbox").fill(bob)
  await alicePage.getByRole("button", { name: "建立" }).click()

  const bobPage = await (await browser.newContext()).newPage()
  await loginUi(bobPage, bob)
  await bobPage.goto("/items")
  await expect(bobPage.getByText("Alice 的傘")).toBeVisible()
  await bobPage.getByText("Alice 的傘").click()
  await expect(bobPage.getByText(/由 .+ 分享/)).toBeVisible()

  await alicePage.goto(`/items/${itemId}`)
  await alicePage.getByRole("button", { name: "轉移所有權" }).click()
  await alicePage.getByLabel("接收者使用者名稱").fill(bob)
  await alicePage.getByRole("button", { name: "送出請求" }).click()

  await bobPage.goto("/collaboration?tab=transfers")
  await bobPage.getByRole("button", { name: "接受" }).click()
  await expect(bobPage.getByText(/已接受/)).toBeVisible()

  await bobPage.goto(`/items/${itemId}`)
  await expect(bobPage.getByText(/由 .+ 分享/)).toHaveCount(0)
})
