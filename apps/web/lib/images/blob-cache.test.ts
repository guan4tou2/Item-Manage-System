import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import * as client from "@/lib/api/client"

import {
  acquireBlobUrl,
  clearBlobCache,
  releaseBlobUrl,
  setBlobCacheMaxSize,
  __resetBlobCacheForTests,
} from "./blob-cache"

const PNG_BYTES = new Uint8Array([0x89, 0x50, 0x4e, 0x47])

function okResponse(bytes: Uint8Array<ArrayBuffer> = PNG_BYTES): Response {
  return new Response(bytes, { status: 200, headers: { "content-type": "image/png" } })
}

let createObjectURL: ReturnType<typeof vi.fn>
let revokeObjectURL: ReturnType<typeof vi.fn>
let urlCounter: number

function mockApiFetch(response: Response | (() => Response) = () => okResponse()) {
  return vi.spyOn(client, "apiFetch").mockImplementation(() =>
    Promise.resolve(typeof response === "function" ? response() : response),
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
  __resetBlobCacheForTests()
  urlCounter = 0
  createObjectURL = vi.fn(() => `blob:mock-${++urlCounter}`)
  revokeObjectURL = vi.fn()
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL })
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL })
})

afterEach(() => {
  __resetBlobCacheForTests()
})

describe("blob-cache", () => {
  it("抓取成功並建立 blob URL", async () => {
    const fetchSpy = mockApiFetch()

    const url = await acquireBlobUrl("img-1", "jwt")

    expect(url).toBe("blob:mock-1")
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(fetchSpy).toHaveBeenCalledWith("/images/img-1", { accessToken: "jwt" })
    expect(createObjectURL).toHaveBeenCalledTimes(1)
  })

  it("併發請求同一 imageId 只發一次 fetch", async () => {
    mockApiFetch()

    const [url1, url2] = await Promise.all([
      acquireBlobUrl("img-1", "jwt"),
      acquireBlobUrl("img-1", "jwt"),
    ])

    expect(url1).toBe(url2)
    expect(client.apiFetch).toHaveBeenCalledTimes(1)
  })

  it("抓取失敗不會快取，下次可重試", async () => {
    let calls = 0
    vi.spyOn(client, "apiFetch").mockImplementation(() => {
      calls++
      if (calls === 1) return Promise.reject(new Error("network"))
      return Promise.resolve(okResponse())
    })

    await expect(acquireBlobUrl("img-1", "jwt")).rejects.toThrow("network")

    const url = await acquireBlobUrl("img-1", "jwt")
    expect(url).toBe("blob:mock-1")
    expect(client.apiFetch).toHaveBeenCalledTimes(2)
  })

  it("釋放後仍保留在快取，再次取得不重新下載", async () => {
    mockApiFetch()

    const url = await acquireBlobUrl("img-1", "jwt")
    releaseBlobUrl("img-1")

    const url2 = await acquireBlobUrl("img-1", "jwt")

    expect(url2).toBe(url)
    expect(client.apiFetch).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).not.toHaveBeenCalled()
  })

  it("超過上限時淘汰最久未用且無人使用的項目並 revoke", async () => {
    setBlobCacheMaxSize(2)
    mockApiFetch()

    const url1 = await acquireBlobUrl("img-1", "jwt")
    releaseBlobUrl("img-1")
    const url2 = await acquireBlobUrl("img-2", "jwt")
    releaseBlobUrl("img-2")

    // 加入第三筆，超過上限 2，應淘汰最久未用的 img-1
    const url3 = await acquireBlobUrl("img-3", "jwt")

    expect(url3).toBe("blob:mock-3")
    expect(revokeObjectURL).toHaveBeenCalledWith(url1)
    expect(revokeObjectURL).not.toHaveBeenCalledWith(url2)
    // img-1 已被移除，再次取得需要重新 fetch
    releaseBlobUrl("img-3")
    await acquireBlobUrl("img-1", "jwt")
    expect(client.apiFetch).toHaveBeenCalledTimes(4)
  })

  it("引用計數大於零的項目不會被淘汰", async () => {
    setBlobCacheMaxSize(1)
    mockApiFetch()

    const url1 = await acquireBlobUrl("img-1", "jwt")
    // img-1 仍被使用中，加入 img-2 時無法淘汰 img-1，快取暫時超過上限
    const url2 = await acquireBlobUrl("img-2", "jwt")

    expect(url2).toBe("blob:mock-2")
    expect(revokeObjectURL).not.toHaveBeenCalled()
    expect(createObjectURL).toHaveBeenCalledTimes(2)

    releaseBlobUrl("img-1")
    releaseBlobUrl("img-2")
    // 雖然兩者都已釋放，此測試重點是過程中沒有因超過上限而 revoke
    expect(revokeObjectURL).not.toHaveBeenCalledWith(url1)
    expect(revokeObjectURL).not.toHaveBeenCalledWith(url2)
  })

  it("清空快取會 revoke 所有已就緒的 URL", async () => {
    mockApiFetch()

    const url1 = await acquireBlobUrl("img-1", "jwt")
    const url2 = await acquireBlobUrl("img-2", "jwt")

    clearBlobCache()

    expect(revokeObjectURL).toHaveBeenCalledWith(url1)
    expect(revokeObjectURL).toHaveBeenCalledWith(url2)
  })

  it("access token 變成 null 時清空快取", async () => {
    const fetchSpy = mockApiFetch()

    useAuthStore.setState({ accessToken: "jwt" })
    const url = await acquireBlobUrl("img-1", "jwt")

    useAuthStore.setState({ accessToken: null })

    expect(revokeObjectURL).toHaveBeenCalledWith(url)
    // 清除後再次取得需重新 fetch
    await acquireBlobUrl("img-1", "jwt")
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it("access token refresh（非 null 到非 null）不清空快取", async () => {
    mockApiFetch()

    useAuthStore.setState({ accessToken: "old-jwt" })
    const url = await acquireBlobUrl("img-1", "jwt")

    useAuthStore.setState({ accessToken: "new-jwt" })

    expect(revokeObjectURL).not.toHaveBeenCalled()
    const url2 = await acquireBlobUrl("img-1", "new-jwt")
    expect(url2).toBe(url)
    expect(client.apiFetch).toHaveBeenCalledTimes(1)
  })
})
