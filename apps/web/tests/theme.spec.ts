import { expect, test } from "@playwright/test"

test.describe("Theme persistence", () => {
  test("anon user switching via __dev page persists across reload", async ({
    page,
  }) => {
    await page.goto("/__dev/components")
    await expect(page.getByRole("heading", { name: "UI 元件展示" })).toBeVisible()

    const before = await page.locator("html").getAttribute("class")
    await page.getByRole("button", { name: /切換/ }).click()
    const after = await page.locator("html").getAttribute("class")
    expect(after).not.toBe(before)

    const expectedDark = after?.includes("dark") ?? false
    await page.reload()
    const reloaded = await page.locator("html").getAttribute("class")
    expect(reloaded?.includes("dark") ?? false).toBe(expectedDark)
  })

  test("authenticated user: theme loads from preferences API", async ({
    page,
    request,
  }) => {
    const suffix = Date.now().toString()
    const username = `theme_${suffix}`
    const email = `theme_${suffix}@example.com`
    const password = "secret1234"

    const reg = await request.post("/api/auth/register", {
      data: { email, username, password },
    })
    expect(reg.status()).toBe(201)

    const login = await request.post("/api/auth/login", {
      data: { username, password },
    })
    const { access_token } = await login.json()

    await request.put("/api/users/me/preferences", {
      headers: { Authorization: `Bearer ${access_token}` },
      data: { theme: "dark" },
    })

    await page.goto("/login")
    await page.getByLabel("使用者名稱").fill(username)
    await page.getByLabel("密碼").fill(password)
    await page.getByRole("button", { name: /登入/ }).click()
    await page.waitForURL("/")
    await page.goto("/__dev/components")
    await page.waitForFunction(() =>
      document.documentElement.classList.contains("dark"),
    )
    await expect(page.locator("html")).toHaveClass(/dark/)
  })

  test("authenticated user: toggling theme syncs to preferences API", async ({
    page,
    request,
  }) => {
    const suffix = Date.now().toString()
    const username = `sync_${suffix}`
    const email = `sync_${suffix}@example.com`
    const password = "secret1234"

    const reg = await request.post("/api/auth/register", {
      data: { email, username, password },
    })
    expect(reg.status()).toBe(201)

    const login = await request.post("/api/auth/login", {
      data: { username, password },
    })
    const { access_token } = await login.json()

    // UI login so the browser has a token in store
    await page.goto("/login")
    await page.getByLabel("使用者名稱").fill(username)
    await page.getByLabel("密碼").fill(password)
    await page.getByRole("button", { name: /登入/ }).click()
    await page.waitForURL("/")

    await page.goto("/__dev/components")
    const before = await page.locator("html").getAttribute("class")
    const expectingDark = !(before ?? "").includes("dark")

    // Wait for the preferences PUT after clicking the toggle
    const putResponse = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/users/me/preferences") && r.request().method() === "PUT",
    )
    await page.getByRole("button", { name: /切換/ }).click()
    await putResponse

    // Verify server-side state via fresh GET
    const fetch = await request.get("/api/users/me/preferences", {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    const body = await fetch.json()
    expect(body.theme).toBe(expectingDark ? "dark" : "light")
  })
})
