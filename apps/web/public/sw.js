/* IMS service worker — cache-first static, network-first navigation, offline fallback. */
const CACHE = "ims-v3"
const STATIC_PREFIX = "/_next/static/"
const OFFLINE_URL = "/offline"
// Routes that are useless offline — skip caching and don't fall back to /offline.
const SKIP_CACHE_PATHS = ["/scan"]

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll([OFFLINE_URL])))
  // Intentionally do NOT skipWaiting here — wait for the page to send a
  // SKIP_WAITING message once the user accepts the "new version" prompt.
})

// Let the controlling page trigger activation when the user is ready.
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting()
  }
})

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener("fetch", (event) => {
  const req = event.request
  if (req.method !== "GET") return
  const url = new URL(req.url)

  if (url.pathname.startsWith(STATIC_PREFIX)) {
    event.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            const copy = res.clone()
            caches.open(CACHE).then((c) => c.put(req, copy))
            return res
          }),
      ),
    )
    return
  }

  if (req.mode === "navigate") {
    const skipCache = SKIP_CACHE_PATHS.some((p) => url.pathname.startsWith(p))
    if (skipCache) {
      // Let the browser handle these normally — no offline fallback.
      return
    }
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(req, copy))
          return res
        })
        .catch(() =>
          caches
            .match(req)
            .then((cached) => cached || caches.match(OFFLINE_URL)),
        ),
    )
  }
})

self.addEventListener("push", (event) => {
  const fallback = { title: "IMS", body: "", url: "/notifications" }
  let payload = fallback
  if (event.data) {
    try {
      payload = { ...fallback, ...event.data.json() }
    } catch {
      payload = { ...fallback, body: event.data.text() }
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title || fallback.title, {
      body: payload.body || "",
      data: { url: payload.url || fallback.url },
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
    }),
  )
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  const targetUrl = new URL(
    event.notification.data?.url || "/notifications",
    self.location.origin,
  )

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((client) => {
          const url = new URL(client.url)
          return url.origin === targetUrl.origin && url.pathname === targetUrl.pathname
        })
        if (existing) return existing.focus()
        return self.clients.openWindow(targetUrl.href)
      }),
  )
})

// The same request/state engine is used by the page and this classic worker.
// 載入失敗時只是沒有背景同步，不可讓整個 service worker 裝不起來。
try { importScripts("/offline-engine.js") } catch { /* 背景同步停用 */ }

function offlineDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("ims-offline", 1)
    request.onupgradeneeded = () => request.result.createObjectStore("pending-items", { keyPath: "client_id" })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
    request.onblocked = () => reject(new Error("offline database blocked"))
  })
}
function offlineTransaction(db, mode, action) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending-items", mode)
    const request = action(tx.objectStore("pending-items"))
    tx.oncomplete = () => resolve(request.result)
    tx.onerror = () => reject(tx.error || request.error)
    tx.onabort = () => reject(tx.error || request.error)
  })
}
async function syncOfflineItems() {
  const db = await offlineDB()
  let networkFailure = false
  try {
    const rows = (await offlineTransaction(db, "readonly", (s) => s.getAll()))
      .filter((row) => row.steps?.length && row.api_base && ["pending", "syncing"].includes(row.status))
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
    if (!rows.length) return
    const sessions = new Map()
    for (const snapshot of rows) {
      const base = snapshot.api_base
      let session = sessions.get(base)
      if (!session) {
        const refresh = await fetch(`${base}/auth/refresh`, { method: "POST", credentials: "include" })
        if (refresh.status === 401) return
        if (!refresh.ok) throw new Error("offline refresh failed")
        const { access_token: token } = await refresh.json()
        let owner
        try {
          const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")
          owner = JSON.parse(atob(payload)).sub
        } catch { return }
        if (typeof owner !== "string") return
        session = { owner, token }
        sessions.set(base, session)
      }
      const { owner, token } = session
      if (snapshot.owner_user_id !== owner) continue
      const row = await offlineTransaction(db, "readonly", (s) => s.get(snapshot.client_id))
      if (!row || row.api_base !== base || row.owner_user_id !== owner || !["pending", "syncing"].includes(row.status) || !row.steps?.length) continue
      const active = { ...row, status: "syncing" }
      await offlineTransaction(db, "readwrite", (s) => s.put(active))
      const result = await self.imsOfflineEngine.executeItem(active, async (step) => {
        const response = await fetch(`${base}${step.path}`, {
          method: step.method, credentials: "include",
          headers: { "Content-Type": "application/json", ...step.headers, Authorization: `Bearer ${token}` },
          body: step.body === undefined ? undefined : JSON.stringify(step.body),
        })
        return { status: response.status, body: await response.json().catch(() => null) }
      })
      const next = self.imsOfflineEngine.applyResult(active, result)
      await offlineTransaction(db, "readwrite", (s) => next ? s.put(next) : s.delete(row.client_id))
      if (result.type === "network" || result.network) { networkFailure = true; break }
      if (result.type === "unauthorized") break
    }
  } finally {
    db.close()
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true })
    for (const client of windows) client.postMessage({ type: "ims-offline-synced" })
  }
  if (networkFailure) throw new Error("offline network failure")
}
self.addEventListener("sync", (event) => {
  if (event.tag !== "ims-offline-sync" || !self.imsOfflineEngine) return
  event.waitUntil(self.navigator?.locks
    ? self.navigator.locks.request("ims-offline-sync", { ifAvailable: true }, (lock) => lock ? syncOfflineItems() : undefined)
    : syncOfflineItems())
})
