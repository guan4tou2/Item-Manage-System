import { apiFetch } from "@/lib/api/client"
import { useAuthStore } from "@/lib/auth/auth-store"

interface ReadyEntry {
  status: "ready"
  url: string
  refCount: number
  lastUsedAt: number
}

interface PendingEntry {
  status: "pending"
  promise: Promise<string>
  refCount: number
}

type Entry = ReadyEntry | PendingEntry

interface AuthStoreSnapshot {
  accessToken: string | null
}

const cache = new Map<string, Entry>()
let maxSize = 50

function getStoreSnapshot(): AuthStoreSnapshot | null {
  const store = useAuthStore as unknown as { getState?: () => AuthStoreSnapshot }
  if (typeof store.getState === "function") {
    return store.getState()
  }
  return null
}

function subscribeToStore(callback: (state: AuthStoreSnapshot) => void): void {
  const store = useAuthStore as unknown as { subscribe?: (cb: (state: AuthStoreSnapshot) => void) => () => void }
  if (typeof store.subscribe === "function") {
    store.subscribe(callback)
  }
}

let lastKnownToken: string | null = getStoreSnapshot()?.accessToken ?? null

subscribeToStore((state) => {
  const current = state.accessToken
  if (lastKnownToken !== null && current === null) {
    clearBlobCache()
  }
  lastKnownToken = current
})

function evictIfNeeded(): void {
  if (cache.size <= maxSize) return

  // 只淘汰無人使用的項目，並以 lastUsedAt 升冪挑出最久未用者
  const candidates: Array<{ imageId: string; lastUsedAt: number; url: string }> = []
  for (const [imageId, entry] of cache) {
    if (entry.status === "ready" && entry.refCount === 0) {
      candidates.push({ imageId, lastUsedAt: entry.lastUsedAt, url: entry.url })
    }
  }
  candidates.sort((a, b) => a.lastUsedAt - b.lastUsedAt)

  let over = cache.size - maxSize
  for (const candidate of candidates) {
    if (over <= 0) break
    URL.revokeObjectURL(candidate.url)
    cache.delete(candidate.imageId)
    over--
  }
}

async function fetchBlobUrl(imageId: string, accessToken: string): Promise<string> {
  const response = await apiFetch(`/images/${imageId}`, { accessToken })
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

/**
 * 取得指定圖片的 blob URL，引用計數 +1。
 * 同一 imageId 併發請求會被合併為單次 fetch。
 */
export function acquireBlobUrl(imageId: string, accessToken: string): Promise<string> {
  const existing = cache.get(imageId)
  if (existing) {
    if (existing.status === "ready") {
      existing.refCount++
      existing.lastUsedAt = Date.now()
      return Promise.resolve(existing.url)
    }
    existing.refCount++
    return existing.promise
  }

  const promise = fetchBlobUrl(imageId, accessToken)
    .then((url) => {
      const current = cache.get(imageId)
      if (current?.status !== "pending" || current.promise !== promise) {
        // 快取已被清空或同一 key 被重新請求，撤銷這個無人管理的 URL
        URL.revokeObjectURL(url)
        throw new Error(`blob cache entry for ${imageId} was cleared during fetch`)
      }
      const ready: ReadyEntry = {
        status: "ready",
        url,
        refCount: current.refCount,
        lastUsedAt: Date.now(),
      }
      cache.set(imageId, ready)
      evictIfNeeded()
      return url
    })
    .catch((error) => {
      const current = cache.get(imageId)
      if (current?.status === "pending" && current.promise === promise) {
        cache.delete(imageId)
      }
      throw error
    })

  cache.set(imageId, { status: "pending", promise, refCount: 1 })
  return promise
}

/**
 * 釋放指定圖片的 blob URL，引用計數 -1。
 * 計數歸零的項目會留在快取中，等待 LRU 淘汰時才 revoke。
 */
export function releaseBlobUrl(imageId: string): void {
  const entry = cache.get(imageId)
  if (!entry) return
  entry.refCount = Math.max(0, entry.refCount - 1)
}

/** 清空整個快取並 revoke 所有已產生的 blob URL。 */
export function clearBlobCache(): void {
  for (const [, entry] of cache) {
    if (entry.status === "ready") {
      URL.revokeObjectURL(entry.url)
    }
  }
  cache.clear()
}

/** 設定快取上限，超過上限時會立即觸發 LRU 淘汰。 */
export function setBlobCacheMaxSize(size: number): void {
  maxSize = size
  evictIfNeeded()
}

/** 僅供測試：重置快取狀態與上限。 */
export function __resetBlobCacheForTests(): void {
  clearBlobCache()
  maxSize = 50
  lastKnownToken = getStoreSnapshot()?.accessToken ?? null
}
