import { afterEach, expect, it, vi } from "vitest"
import { registerOfflineSync } from "./background"

afterEach(() => { vi.restoreAllMocks(); Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: undefined }) })
it("registers the sync tag on the existing registration", async () => {
  const register = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { getRegistration: vi.fn().mockResolvedValue({ sync: { register } }) } })
  await registerOfflineSync()
  expect(register).toHaveBeenCalledWith("ims-offline-sync")
})
it("unsupported sync and failed registration are harmless", async () => {
  for (const registration of [{}, { sync: { register: vi.fn().mockRejectedValue(Error("denied")) } }]) {
    Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { getRegistration: vi.fn().mockResolvedValue(registration) } })
    await expect(registerOfflineSync()).resolves.toBeUndefined()
  }
})
it("enqueue registers background sync after successfully persisting computed requests", async () => {
  const { OfflineQueue } = await import("./queue")
  const register = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { getRegistration: vi.fn().mockResolvedValue({ sync: { register } }) } })
  const put = vi.fn().mockResolvedValue(undefined)
  const queue = new OfflineQueue({ list: async () => [], put, remove: async () => {} })
  await queue.save({ client_id: "key", owner_user_id: "owner", created_at: "today", status: "pending", attempts: 0, error_code: null, values: { name: "mine", quantity: 1, category_id: null, location_id: null, tag_names: [], custom_values: {} }, customFields: [], trackBatches: false })
  await vi.waitFor(() => expect(register).toHaveBeenCalledWith("ims-offline-sync"))
  expect(put).toHaveBeenCalledWith(expect.objectContaining({ steps: [expect.objectContaining({ method: "POST", path: "/items" })] }))
})
