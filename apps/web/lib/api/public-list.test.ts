import { afterEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import { getPublicList, isPublicHttpLink, PublicListError } from "./public-list"

afterEach(() => { vi.unstubAllGlobals(); useAuthStore.setState({ accessToken: null, user: null }) })

describe("公開清單的獨立請求", () => {
  it("只在標頭傳分享 token，不附登入憑證或 cookie", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ title: "清單" }) })
    vi.stubGlobal("fetch", fetcher)
    useAuthStore.setState({ accessToken: "private-jwt" })
    await getPublicList("share-secret")
    expect(fetcher).toHaveBeenCalledWith("/api/public/list", expect.objectContaining({
      credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer",
      headers: { "X-Share-Token": "share-secret" },
    }))
    expect(fetcher.mock.calls[0]![0]).not.toContain("share-secret")
  })

  it.each([401, 404, 503])("%s 不觸發 refresh 或清除登入狀態", async status => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status })
    vi.stubGlobal("fetch", fetcher)
    useAuthStore.setState({ accessToken: "private-jwt" })
    await expect(getPublicList("secret")).rejects.toMatchObject({ status })
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(useAuthStore.getState().accessToken).toBe("private-jwt")
    expect(new PublicListError(status).message).not.toContain("secret")
  })

  it.each(["javascript:alert(1)", "data:text/html,hello", "/items/1", "//example.com", " https://example.com"])("拒絕非 http(s) 連結 %s", value => {
    expect(isPublicHttpLink(value)).toBe(false)
  })
  it.each(["http://example.com", "HTTPS://example.com"])("允許 %s", value => {
    expect(isPublicHttpLink(value)).toBe(true)
  })
})
