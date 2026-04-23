# PWA 體驗設計 — v2 子專案 #9

## 目標

讓 IMS 網頁可安裝為 home-screen 應用、具備基本離線容錯（app shell 可載入、`/offline` fallback 頁），並在支援的瀏覽器顯示 install prompt。

## 範圍

**In scope：**
- `public/manifest.webmanifest`（name、short_name、theme_color、display=standalone、icons）
- 192×192 / 512×512 PNG icons（純 stdlib 生成；單色 placeholder，未來可替換）
- Root layout meta：`<link rel="manifest">`、`apple-touch-icon`、`theme-color`、`viewport`
- `public/sw.js`：vanilla service worker
  - Cache-first for `/_next/static/*`（immutable hashed assets）
  - Network-first fallback to cache for navigation
  - Navigation failure + no cache → 回傳 `/offline`
- 客戶端 `ServiceWorkerProvider` — mount 於 root layout，呼叫 `navigator.serviceWorker.register('/sw.js')`
- `InstallPwaButton` — 監聽 `beforeinstallprompt` event，掛於 user menu 裡（若支援）
- `/offline` 頁 — 獨立於 `(app)` 群組，不經過 auth 檢查
- i18n 新增鍵

**Out of scope：**
- Web Push / VAPID / FCM（另設子專案）
- Background sync（API POST while offline）
- API response caching（與 TanStack Query 的 stale 邏輯衝突）
- Workbox / Serwist / next-pwa 第三方 library（保持 vanilla SW）
- Manifest shortcuts / screenshots
- 無條件離線可編輯（require sync queue，不在範圍）

## 資料流

```
首次載入：
  browser → GET / → Next 回 app shell
         ↑
         └─ SW register 完成 → 背景 fetch /sw.js 註冊

重複載入：
  browser → GET / → SW 攔截 → cache (/_next/static/*) 命中
         └─ app.js 立即載入；API call 仍 online-only（TanStack Query 控制）

離線：
  browser → GET /items → SW fetch 失敗 → 試 cache → 若有 → 回 200（雖 API 無法用）
                                      → 若無 → 回 /offline
```

## 檔案結構

- `apps/web/public/manifest.webmanifest`
- `apps/web/public/icons/icon-192.png`
- `apps/web/public/icons/icon-512.png`
- `apps/web/public/sw.js`（vanilla JS，**不經 bundler**；直接由 Next 的 `public/` static serving 提供）
- `apps/web/app/offline/page.tsx`
- `apps/web/components/pwa/service-worker-provider.tsx`
- `apps/web/components/pwa/install-pwa-button.tsx`
- `apps/web/scripts/generate-pwa-icons.py`（Python stdlib；檔入 repo，讓 icons 可重現）
- 修改：`apps/web/app/layout.tsx`（meta tags + `ServiceWorkerProvider`）、`apps/web/components/shell/user-menu.tsx`（加入 InstallPwaButton）
- i18n：新增 `pwa.*` keys

## Service Worker（`public/sw.js`）

```js
const CACHE = "ims-v1"
const STATIC_PREFIX = "/_next/static/"
const OFFLINE_URL = "/offline"

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll([OFFLINE_URL])),
  )
  self.skipWaiting()
})

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  )
})

self.addEventListener("fetch", (event) => {
  const req = event.request
  if (req.method !== "GET") return
  const url = new URL(req.url)

  // Cache-first for immutable Next static assets
  if (url.pathname.startsWith(STATIC_PREFIX)) {
    event.respondWith(
      caches.match(req).then((cached) =>
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

  // Network-first for navigation; fall back to cache; final fallback to /offline
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(req, copy))
          return res
        })
        .catch(() =>
          caches.match(req).then((cached) => cached || caches.match(OFFLINE_URL)),
        ),
    )
    return
  }
})
```

## Manifest

```json
{
  "name": "物品管理系統 v2",
  "short_name": "IMS",
  "description": "Home item management",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
```

## Root layout 改動

加入 `<head>` meta：
```tsx
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#2563eb" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<link rel="apple-touch-icon" href="/icons/icon-192.png" />
```

以及 body 內掛 `<ServiceWorkerProvider />`。

## ServiceWorkerProvider

```tsx
// apps/web/components/pwa/service-worker-provider.tsx
"use client"
import { useEffect } from "react"

export function ServiceWorkerProvider() {
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return
    if (process.env.NODE_ENV !== "production") return  // dev: don't register
    navigator.serviceWorker.register("/sw.js").catch(() => {})
  }, [])
  return null
}
```

## InstallPwaButton

```tsx
"use client"
import { useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>
}

export function InstallPwaButton() {
  const t = useTranslations()
  const [evt, setEvt] = useState<BeforeInstallPromptEvent | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault()
      setEvt(e as BeforeInstallPromptEvent)
    }
    window.addEventListener("beforeinstallprompt", handler)
    return () => window.removeEventListener("beforeinstallprompt", handler)
  }, [])

  if (!evt) return null
  return (
    <Button
      size="sm"
      variant="outline"
      onClick={async () => {
        await evt.prompt()
        setEvt(null)
      }}
    >
      {t("pwa.install")}
    </Button>
  )
}
```

## Offline 頁

`apps/web/app/offline/page.tsx`：
```tsx
import Link from "next/link"

export default function OfflinePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold">離線中</h1>
      <p className="text-muted-foreground">目前無法連線到伺服器。請檢查網路後再試。</p>
      <Link href="/" className="underline">回首頁</Link>
    </main>
  )
}
```

## Icon 生成

`apps/web/scripts/generate-pwa-icons.py` 用 Python stdlib（struct + zlib）產生單色 PNG：

```python
#!/usr/bin/env python3
"""Generate solid-color PNG placeholder icons for PWA."""
import struct
import zlib
from pathlib import Path


def write_solid_png(path: Path, size: int, rgb: tuple[int, int, int]) -> None:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * size
    raw = row * size
    idat = zlib.compress(raw)
    path.write_bytes(
        signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    out_dir = Path(__file__).parent.parent / "public" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)
    color = (37, 99, 235)  # #2563eb
    write_solid_png(out_dir / "icon-192.png", 192, color)
    write_solid_png(out_dir / "icon-512.png", 512, color)
    print(f"wrote {out_dir}/icon-192.png and icon-512.png")
```

Icons 是靜態資產，會被 check in 到 repo。腳本 committed 以便未來重新生成。

## i18n 新增鍵

```
pwa.install: "安裝至主畫面" / "Install to home screen"
pwa.offline.title: "離線中" / "You are offline"
pwa.offline.body: "目前無法連線到伺服器。請檢查網路後再試。" / "Cannot reach the server. Please check your connection."
pwa.offline.home: "回首頁" / "Back to home"
```

## 測試

### 前端 vitest（2 新測試）

- `install-pwa-button.test.tsx`：
  - 初始無 event → button 不顯示
  - 手動 dispatch `beforeinstallprompt` event → button 顯示；click → 呼叫 `prompt()`

### Build 驗證

- `pnpm build` 成功；build output 包含 `/offline` 路由
- 檢查 `apps/web/public/manifest.webmanifest`、`apps/web/public/icons/*.png`、`apps/web/public/sw.js` 存在

### 手動驗證（執行者選擇）

- Chrome DevTools → Application → Manifest：顯示正確資料與 icon 預覽
- Application → Service Workers：顯示 `/sw.js` 已啟用
- Lighthouse PWA audit：至少通過「Installable」criteria

### E2E（`apps/web/tests/pwa.spec.ts`）

- 瀏覽 `/offline`（直接 URL）→ 檢查 `離線中` 文字出現
- 註：正式 offline 行為 E2E 需要 page.context().setOffline(true)；播測可行但環境需要 sw 已裝好，跳過

## 錯誤處理

- SW 註冊失敗：`.catch(() => {})`（不影響使用）
- 離線 + 未快取路徑 → 回 `/offline`
- `beforeinstallprompt` 不觸發的瀏覽器（Safari、Firefox）→ button 不顯示
- 非 production 模式（dev）→ SW 不註冊，避免 dev 服務過 cache

## 成功指標

- Chrome/Edge 行動裝置上可見「安裝」按鈕
- 離線時直接造訪已快取頁面仍可看到 app shell
- Lighthouse PWA 分數 ≥ 80（核心項目：manifest + SW + HTTPS in prod）
- 既有測試 + build 皆綠
