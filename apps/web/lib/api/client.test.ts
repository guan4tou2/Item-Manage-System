import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "@/lib/auth/auth-store"
import { ApiError, apiFetch, getApiErrorMessages } from "./client"

const originalFetch = global.fetch

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

type FetchMock = ReturnType<typeof vi.fn>

/** 取第 n 次 fetch 呼叫的 [url, init]。 */
function callAt(mock: FetchMock, n: number): [string, RequestInit] {
  return mock.mock.calls[n] as [string, RequestInit]
}

function authOf(call: [string, RequestInit]): string | null {
  return new Headers(call[1].headers).get("authorization")
}

describe("apiFetch 401 handling", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "jwt", user: null })
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("clears the auth store on 401 when refresh fails", async () => {
    global.fetch = vi.fn().mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json({ detail: "expired" }, 401) : json({ detail: "unauthorized" }, 401),
    )
    const err = await apiFetch("/anything", { accessToken: "jwt" }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(401)
    expect(err.body).toEqual({ detail: "unauthorized" })
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("does not touch the store or refresh when no accessToken was sent", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ detail: "unauthorized" }, 401))
    global.fetch = fetchMock
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("does not clear the store on non-401 errors", async () => {
    global.fetch = vi.fn().mockResolvedValue(json({ detail: "boom" }, 500))
    await expect(apiFetch("/anything", { accessToken: "jwt" })).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBe("jwt")
  })

  it("refreshes once on 401, retries with the new token and updates the store", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return json({ access_token: "new-jwt" })
      return new Headers(init.headers).get("authorization") === "Bearer new-jwt" ? json({ ok: true }) : json({}, 401)
    })
    global.fetch = fetchMock
    const res = await apiFetch("/items", { accessToken: "jwt", method: "POST", body: '{"a":1}' })
    expect(await res.json()).toEqual({ ok: true })
    expect(useAuthStore.getState().accessToken).toBe("new-jwt")
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const refreshCall = callAt(fetchMock, 1)
    expect(refreshCall[0]).toMatch(/\/auth\/refresh$/)
    expect(refreshCall[1].credentials).toBe("include")
    // 字串 body 重送時保持不變
    expect(callAt(fetchMock, 2)[1].body).toBe('{"a":1}')
  })

  it("shares a single in-flight refresh across concurrent 401s", async () => {
    let refreshCalls = 0
    global.fetch = vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1
        await new Promise((r) => setTimeout(r, 10))
        return json({ access_token: "new-jwt" })
      }
      return new Headers(init.headers).get("authorization") === "Bearer new-jwt" ? json({ ok: true }) : json({}, 401)
    })
    const results = await Promise.all([
      apiFetch("/a", { accessToken: "jwt" }),
      apiFetch("/b", { accessToken: "jwt" }),
      apiFetch("/c", { accessToken: "jwt" }),
    ])
    expect(results.every((r) => r.ok)).toBe(true)
    expect(refreshCalls).toBe(1)
  })

  it("does not refresh for /auth/ paths (e.g. wrong password on login)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ detail: "bad credentials" }, 401))
    global.fetch = fetchMock
    await expect(apiFetch("/auth/login", { method: "POST", accessToken: "jwt" })).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith("/auth/refresh"))).toBe(false)
  })

  it("does not loop when the retry still returns 401", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json({ access_token: "new-jwt" }) : json({ detail: "nope" }, 401),
    )
    global.fetch = fetchMock
    await expect(apiFetch("/items", { accessToken: "jwt" })).rejects.toBeInstanceOf(ApiError)
    // 原請求 + refresh + 重試，共三次
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("reuses the store token without refreshing when another request already refreshed", async () => {
    useAuthStore.setState({ accessToken: "newer-jwt", user: null })
    const fetchMock = vi.fn().mockImplementation(async (_url: string, init: RequestInit) =>
      new Headers(init.headers).get("authorization") === "Bearer newer-jwt" ? json({ ok: true }) : json({}, 401),
    )
    global.fetch = fetchMock
    const res = await apiFetch("/items", { accessToken: "stale-jwt" })
    expect(res.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(authOf(callAt(fetchMock, 1))).toBe("Bearer newer-jwt")
  })

  it("resends a FormData body on retry", async () => {
    const form = new FormData()
    form.append("file", new Blob(["x"]), "a.txt")
    const fetchMock = vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return json({ access_token: "new-jwt" })
      return new Headers(init.headers).get("authorization") === "Bearer new-jwt" ? json({ ok: true }) : json({}, 401)
    })
    global.fetch = fetchMock
    const res = await apiFetch("/upload", { accessToken: "jwt", method: "POST", body: form })
    expect(res.ok).toBe(true)
    const retry = callAt(fetchMock, 2)[1]
    expect(retry.body).toBe(form)
    expect(new Headers(retry.headers).has("content-type")).toBe(false)
  })
})

describe("getApiErrorMessages", () => {
  it("collects msg from FastAPI validation arrays and string detail", () => {
    expect(getApiErrorMessages(new ApiError(422, { detail: [{ msg: "Value error, webhook_url_not_allowed" }, { x: 1 }] })))
      .toEqual(["Value error, webhook_url_not_allowed"])
    expect(getApiErrorMessages(new ApiError(400, { detail: "boom" }))).toEqual(["boom"])
    expect(getApiErrorMessages(new Error("x"))).toEqual([])
    expect(getApiErrorMessages(new ApiError(500, null))).toEqual([])
  })
})
