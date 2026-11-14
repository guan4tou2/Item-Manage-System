import { afterEach, expect, it, vi } from "vitest"
import { IndexedDBStorage, OfflineStorageError } from "./storage"

afterEach(() => vi.unstubAllGlobals())
it("IndexedDB 缺少或被瀏覽器停用時拒絕，不能靜默保存", async () => {
  vi.stubGlobal("indexedDB", undefined)
  await expect(new IndexedDBStorage().list("owner")).rejects.toMatchObject({ code: "unavailable" })
  vi.stubGlobal("indexedDB", { open: () => { throw new DOMException("disabled", "SecurityError") } })
  await expect(new IndexedDBStorage().list("owner")).rejects.toBeInstanceOf(OfflineStorageError)
})
it("IndexedDB quota 例外保留可呈現的錯誤分類", async () => {
  vi.stubGlobal("indexedDB", { open: () => { throw new DOMException("full", "QuotaExceededError") } })
  await expect(new IndexedDBStorage().put({} as never)).rejects.toMatchObject({ code: "quota" })
})
