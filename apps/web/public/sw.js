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
