import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("authenticated user can switch locale and it persists", async ({ page, request }) => {
  const suffix = unique()
  const username = `loc_${suffix}`
  const email = `loc_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // 打開 user menu → 語言 → English
  await page.getByRole("button", { name: /使用者選單/ }).click()
  await page.getByText("語言").hover()
  await page.getByRole("menuitemradio", { name: /English/ }).click()

  // UI 標籤應變成英文
  await expect(page.getByRole("link", { name: "Items" })).toBeVisible()

  // reload 後仍是英文
  await page.reload()
  await expect(page.getByRole("link", { name: "Items" })).toBeVisible()
})
