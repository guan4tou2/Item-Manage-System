import { afterEach, expect, it, vi } from "vitest"
import { apiFetch, ApiError, NetworkError } from "@/lib/api/client"
import { createItem } from "@/lib/api/items"
import { shouldQueue } from "./queue"

afterEach(() => vi.unstubAllGlobals())
it("createItem 帶入 key，接受 replay 的 HTTP 200", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "existing" }), { status: 200 }))
  vi.stubGlobal("fetch", fetch)
  expect(await createItem({ name: "物品", quantity: 1 }, "token", "client-id")).toEqual({ id: "existing" })
  const init = fetch.mock.calls[0]![1] as RequestInit
  expect(new Headers(init.headers).get("Idempotency-Key")).toBe("client-id")
  expect(JSON.parse(init.body as string)).toEqual({ name: "物品", quantity: 1 })
})
it("fetch 的一般例外也識別為網路錯誤，HTTP 錯誤不混入", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("傳輸中斷")))
  const error = await apiFetch("/items").catch((error: unknown) => error)
  expect(error).toBeInstanceOf(NetworkError)
  expect(shouldQueue(error, true)).toBe(true)
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })))
  const http = await apiFetch("/items").catch((error: unknown) => error)
  expect(http).toBeInstanceOf(ApiError)
  expect(shouldQueue(http, true)).toBe(false)
})
