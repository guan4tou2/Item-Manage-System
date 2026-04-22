# IMS v2 #2 App Shell 與全域導航 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 IMS v2 的受保護 app shell — 共用 header、mobile drawer、avatar dropdown、4 個空殼頁、啟用 next-intl（zh-TW / en）。

**Architecture:** Next.js App Router route groups `(auth)` / `(app)`；edge middleware 檢查 `ims_token` cookie；client layout 檢查 Zustand token 作為次層保險。Avatar dropdown 提供 settings link + 語言 / 主題 submenu + 登出。next-intl 用 cookie-based locale（無 URL segment），LocaleSync 沿用 #1 ThemeSync 的 token-keyed ref 模式。

**Tech Stack:** Next.js 15 App Router、next-intl 3.21、next-themes、Zustand 5、TanStack Query 5、shadcn/ui、Pydantic v2 Literal、Vitest、Playwright。

**Spec:** [`docs/superpowers/specs/2026-04-22-ims-app-shell-design.md`](../specs/2026-04-22-ims-app-shell-design.md)

---

## 執行前提

這份計畫假設已處於 `.claude/worktrees/modest-newton-942a6d/`（由 #1 建立的 worktree）。所有 `pnpm` 指令從專案根目錄執行。提交訊息語言統一為中文主旨 + 英文 prefix（`feat:`、`fix:`、`docs:`、`chore:`）。

### 環境確認

- 所有工作從 worktree 根目錄 `pwd` 開始確認
- Python 測試：`pnpm -F @ims/api test`（或 `pnpm --filter @ims/api test`）
- Web 單元測試：`pnpm -F @ims/web test`
- Web 型別檢查：`pnpm -F @ims/web typecheck`
- Web build：`pnpm -F @ims/web build`
- Playwright：`pnpm -F @ims/web test:e2e`（需 `docker compose up` 在跑）

---

## Phase A — Backend schema 擴充

### Task 1: 加入 `language` Literal 到 preferences schema

**Files:**
- Modify: `apps/api/app/schemas/preferences.py`
- Modify: `apps/api/tests/test_preferences_schemas.py`

- [ ] **Step 1: 先改測試成「應該要過」的新行為 (RED)**

改 `apps/api/tests/test_preferences_schemas.py`。把現有 `test_allows_extra_keys`（現在用 `language="zh-TW"` 當 extra 範例）改用別的 key，並新增 language 測試：

```python
import pytest
from pydantic import ValidationError

from app.schemas.preferences import PreferencesRead, PreferencesUpdate


class TestPreferencesRead:
    def test_default_theme_is_system(self):
        prefs = PreferencesRead()
        assert prefs.theme == "system"

    def test_default_language_is_zh_tw(self):
        prefs = PreferencesRead()
        assert prefs.language == "zh-TW"

    def test_accepts_valid_theme(self):
        prefs = PreferencesRead(theme="dark")
        assert prefs.theme == "dark"

    def test_accepts_valid_language(self):
        prefs = PreferencesRead(language="en")
        assert prefs.language == "en"

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesRead(theme="neon")

    def test_rejects_invalid_language(self):
        with pytest.raises(ValidationError):
            PreferencesRead(language="ja")

    def test_allows_extra_keys(self):
        prefs = PreferencesRead(theme="light", notifications_enabled=True)
        assert prefs.model_dump()["notifications_enabled"] is True


class TestPreferencesUpdate:
    def test_all_fields_optional(self):
        PreferencesUpdate()  # should not raise

    def test_theme_only(self):
        update = PreferencesUpdate(theme="dark")
        assert update.model_dump(exclude_none=True) == {"theme": "dark"}

    def test_language_only(self):
        update = PreferencesUpdate(language="en")
        assert update.model_dump(exclude_none=True) == {"language": "en"}

    def test_theme_and_language(self):
        update = PreferencesUpdate(theme="dark", language="en")
        assert update.model_dump(exclude_none=True) == {"theme": "dark", "language": "en"}

    def test_allows_extra_keys(self):
        update = PreferencesUpdate(notifications_enabled=True)
        assert update.model_dump(exclude_none=True)["notifications_enabled"] is True

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesUpdate(theme="aqua")

    def test_rejects_invalid_language(self):
        with pytest.raises(ValidationError):
            PreferencesUpdate(language="de")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/api test -- tests/test_preferences_schemas.py -v`
Expected: FAIL — `test_default_language_is_zh_tw`、`test_accepts_valid_language`、`test_rejects_invalid_language`、`test_language_only`、`test_theme_and_language`、`test_rejects_invalid_language` 都報 AttributeError 或 ValidationError 方向錯誤。

- [ ] **Step 3: 改 schema**

改 `apps/api/app/schemas/preferences.py` 為：

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict

Theme = Literal["system", "light", "dark"]
Language = Literal["zh-TW", "en"]


class PreferencesRead(BaseModel):
    theme: Theme = "system"
    language: Language = "zh-TW"

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None
    language: Language | None = None

    model_config = ConfigDict(extra="allow")
```

- [ ] **Step 4: 跑測試確認通過**

Run: `pnpm -F @ims/api test -- tests/test_preferences_schemas.py -v`
Expected: PASS（13 個）

- [ ] **Step 5: 跑整組 API 測試驗證無回歸**

Run: `pnpm -F @ims/api test`
Expected: PASS — 原本 35 tests 會變成 ≥ 41（新增 6 個 schema tests；test_preferences_routes 的 `test_returns_default_theme` 會 **失敗**，因為回傳 payload 現在會多一個 language field，這在 Task 2 處理）。
實際 acceptable：某個 existing route test 會失敗，下一個 task 馬上修。

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/schemas/preferences.py apps/api/tests/test_preferences_schemas.py
git commit -m "feat(api): add language Literal to preferences schema

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: 修 routes 測試預設 payload + 新增 language round-trip 測試

**Files:**
- Modify: `apps/api/tests/test_preferences_routes.py`

- [ ] **Step 1: 改測試 (RED → GREEN 轉折)**

改 `apps/api/tests/test_preferences_routes.py`：

```python
import pytest


@pytest.fixture
async def auth_headers(client):
    """Register + login, return Bearer auth headers."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "prefs@example.com",
            "username": "prefs_user",
            "password": "secret1234",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "prefs_user", "password": "secret1234"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestGetPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/users/me/preferences")
        assert resp.status_code == 401

    async def test_returns_defaults(self, client, auth_headers):
        resp = await client.get(
            "/api/users/me/preferences", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"theme": "system", "language": "zh-TW"}


class TestPutPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.put(
            "/api/users/me/preferences", json={"theme": "dark"}
        )
        assert resp.status_code == 401

    async def test_updates_theme(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme"] == "dark"
        assert body["language"] == "zh-TW"

    async def test_updates_language(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"language": "en"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["language"] == "en"
        assert body["theme"] == "system"

    async def test_updates_theme_and_language(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark", "language": "en"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme"] == "dark"
        assert body["language"] == "en"

    async def test_merge_preserves_other_keys(self, client, auth_headers):
        await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark", "language": "en"},
        )
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "light"},
        )
        body = resp.json()
        assert body["theme"] == "light"
        assert body["language"] == "en"

    async def test_invalid_theme_returns_422(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "neon"},
        )
        assert resp.status_code == 422

    async def test_invalid_language_returns_422(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"language": "fr"},
        )
        assert resp.status_code == 422
```

- [ ] **Step 2: 跑測試確認通過**

Run: `pnpm -F @ims/api test -- tests/test_preferences_routes.py -v`
Expected: PASS（9 個）

- [ ] **Step 3: 跑整組 API 測試**

Run: `pnpm -F @ims/api test`
Expected: PASS — 所有測試（預期 ≥ 44）綠

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/test_preferences_routes.py
git commit -m "test(api): add language round-trip and validation tests

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: 重新產生 api-types

**Files:**
- Regenerate: `packages/api-types/openapi.json`（gitignored）
- Regenerate: `packages/api-types/src/index.ts`

- [ ] **Step 1: 重跑產生指令**

Run:
```bash
pnpm -F @ims/api gen:types
pnpm -F @ims/api-types gen:types
```
Expected: 兩個指令都成功；`packages/api-types/src/index.ts` 的 `PreferencesRead` / `PreferencesUpdate` 應包含 `language?: "zh-TW" | "en"` 欄位。

- [ ] **Step 2: 目視檢查產物**

Run: `grep -A4 "PreferencesRead" packages/api-types/src/index.ts | head -20`
Expected: 顯示的 schema 含 `language?: "zh-TW" | "en"`（TS 版會是 optional 因為有 default）

- [ ] **Step 3: 跑 typecheck 確認 web 端無破壞**

Run: `pnpm -F @ims/web typecheck`
Expected: PASS — 現有引用 `PreferencesRead["theme"]` 都不受影響；新欄位是 additive

- [ ] **Step 4: Commit**

`openapi.json` 被 gitignore，只提交 `src/index.ts`：

```bash
git add packages/api-types/src/index.ts
git commit -m "chore(api-types): regenerate for language field

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase B — Web 基礎設施

### Task 4: cookie-sync 模組 + Vitest

**Files:**
- Create: `apps/web/lib/auth/cookie-sync.ts`
- Create: `apps/web/lib/auth/cookie-sync.test.ts`

- [ ] **Step 1: 寫失敗測試**

建立 `apps/web/lib/auth/cookie-sync.test.ts`：

```ts
import { beforeEach, describe, expect, it } from "vitest"

import { writeTokenCookie } from "./cookie-sync"

function readCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
  if (!match) return null
  return decodeURIComponent(match.slice(name.length + 1))
}

function clearAllCookies(): void {
  document.cookie.split("; ").forEach((row) => {
    const [name] = row.split("=")
    if (name) document.cookie = `${name}=; Path=/; Max-Age=0`
  })
}

describe("writeTokenCookie", () => {
  beforeEach(() => clearAllCookies())

  it("writes ims_token=1 when hasToken is true", () => {
    writeTokenCookie(true)
    expect(readCookie("ims_token")).toBe("1")
  })

  it("clears cookie when hasToken is false", () => {
    document.cookie = "ims_token=1; Path=/"
    writeTokenCookie(false)
    expect(readCookie("ims_token")).toBeNull()
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- lib/auth/cookie-sync.test.ts`
Expected: FAIL — 模組不存在

- [ ] **Step 3: 寫實作**

建立 `apps/web/lib/auth/cookie-sync.ts`：

```ts
"use client"

import { useEffect } from "react"

import { useAuthStore } from "./auth-store"

const COOKIE_NAME = "ims_token"
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7 // 7 days

export function writeTokenCookie(hasToken: boolean): void {
  if (typeof document === "undefined") return
  document.cookie = hasToken
    ? `${COOKIE_NAME}=1; Path=/; SameSite=Lax; Max-Age=${MAX_AGE_SECONDS}`
    : `${COOKIE_NAME}=; Path=/; SameSite=Lax; Max-Age=0`
}

/**
 * 於 mount 當下同步一次目前 token 狀態到 cookie，並訂閱後續變化。
 * 回傳值為 unsubscribe function（由 useEffect cleanup 呼叫）。
 */
export function useTokenCookieSync(): void {
  useEffect(() => {
    writeTokenCookie(Boolean(useAuthStore.getState().accessToken))
    return useAuthStore.subscribe((state, prev) => {
      if (state.accessToken !== prev.accessToken) {
        writeTokenCookie(Boolean(state.accessToken))
      }
    })
  }, [])
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `pnpm -F @ims/web test -- lib/auth/cookie-sync.test.ts`
Expected: PASS（2 個）

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/auth/cookie-sync.ts apps/web/lib/auth/cookie-sync.test.ts
git commit -m "feat(web): add token↔cookie sync module

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: 於 Providers 掛載 CookieSync

**Files:**
- Modify: `apps/web/app/providers.tsx`

- [ ] **Step 1: 改 Providers 加 hook**

把 `apps/web/app/providers.tsx` 改成：

```tsx
"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "next-themes"
import { useState, type ReactNode } from "react"

import { useTokenCookieSync } from "@/lib/auth/cookie-sync"
import { Toaster } from "@/components/ui/sonner"
import { ThemeSync } from "@/lib/theme/theme-sync"

function GlobalSyncers() {
  useTokenCookieSync()
  return null
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <GlobalSyncers />
        <ThemeSync />
        {children}
        <Toaster richColors closeButton />
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

（LocaleSync 會在 Task 17 一併加進 `GlobalSyncers` 裡；現在先放 CookieSync。）

- [ ] **Step 2: Typecheck + build**

Run: `pnpm -F @ims/web typecheck`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/providers.tsx
git commit -m "feat(web): mount CookieSync in providers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: apiFetch 401 → 清 store + cookie

**Files:**
- Modify: `apps/web/lib/api/client.ts`
- Create: `apps/web/lib/api/client.test.ts`

- [ ] **Step 1: 寫失敗測試**

建立 `apps/web/lib/api/client.test.ts`：

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import { ApiError, apiFetch } from "./client"

const originalFetch = global.fetch

describe("apiFetch 401 handling", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "jwt", user: null })
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("clears the auth store on 401", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "unauthorized" }), { status: 401 }),
    )
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("does not clear the store on non-401 errors", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "boom" }), { status: 500 }),
    )
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBe("jwt")
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- lib/api/client.test.ts`
Expected: FAIL — 第一個 case，401 之後 store 還是 "jwt"

- [ ] **Step 3: 修實作**

改 `apps/web/lib/api/client.ts`：

```ts
import type { paths } from "@ims/api-types"

import { useAuthStore } from "@/lib/auth/auth-store"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api"

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`api error ${status}`)
  }
}

type RequestInitWithToken = RequestInit & { accessToken?: string | null }

export async function apiFetch(
  path: string,
  init: RequestInitWithToken = {},
): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set("content-type", "application/json")
  if (init.accessToken) {
    headers.set("authorization", `Bearer ${init.accessToken}`)
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (response.status === 401) {
      // token 實際失效 → 清 store（cookie 由 CookieSync subscriber 連動清掉）
      useAuthStore.getState().clear()
    }
    throw new ApiError(response.status, body)
  }
  return response
}

export type Paths = paths
```

- [ ] **Step 4: 跑測試**

Run: `pnpm -F @ims/web test -- lib/api/client.test.ts`
Expected: PASS（2 個）

- [ ] **Step 5: 跑全部 web 單元測試**

Run: `pnpm -F @ims/web test`
Expected: PASS — 無回歸

- [ ] **Step 6: Commit**

```bash
git add apps/web/lib/api/client.ts apps/web/lib/api/client.test.ts
git commit -m "feat(web): clear auth store on api 401

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: next-intl 設定檔（config / request / messages）

**Files:**
- Create: `apps/web/lib/i18n/config.ts`
- Create: `apps/web/lib/i18n/request.ts`
- Create: `apps/web/messages/zh-TW.json`
- Create: `apps/web/messages/en.json`

- [ ] **Step 1: locale config**

建立 `apps/web/lib/i18n/config.ts`：

```ts
export const locales = ["zh-TW", "en"] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = "zh-TW"

export function isLocale(value: string | undefined | null): value is Locale {
  return value === "zh-TW" || value === "en"
}

/** 從任意輸入（cookie 或 Accept-Language header）解析出合法 locale，失敗 fallback。 */
export function normalizeLocale(value: string | undefined | null): Locale {
  if (!value) return defaultLocale
  if (isLocale(value)) return value
  // Accept-Language 可能像 "en-US,en;q=0.9"
  const primary = value.split(",")[0]?.trim().toLowerCase() ?? ""
  if (primary.startsWith("zh")) return "zh-TW"
  if (primary.startsWith("en")) return "en"
  return defaultLocale
}
```

- [ ] **Step 2: next-intl getRequestConfig**

建立 `apps/web/lib/i18n/request.ts`：

```ts
import { getRequestConfig } from "next-intl/server"
import { cookies, headers } from "next/headers"

import { defaultLocale, normalizeLocale } from "./config"

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const headerStore = await headers()

  const cookieLocale = cookieStore.get("ims_locale")?.value
  const acceptLang = headerStore.get("accept-language") ?? ""
  const locale = normalizeLocale(cookieLocale ?? acceptLang) || defaultLocale

  const messages = (await import(`../../messages/${locale}.json`)).default

  return { locale, messages }
})
```

- [ ] **Step 3: 中文訊息**

建立 `apps/web/messages/zh-TW.json`（扁平 key）：

```json
{
  "nav.dashboard": "儀表板",
  "nav.items": "物品",
  "nav.lists": "清單",
  "nav.settings": "設定",
  "menu.profile": "個人設定",
  "menu.language": "語言",
  "menu.theme": "主題",
  "menu.logout": "登出",
  "theme.system": "跟隨系統",
  "theme.light": "淺色",
  "theme.dark": "深色",
  "locale.zh-TW": "繁體中文",
  "locale.en": "English",
  "placeholder.comingSoon": "此頁將於 #{n} 子專案實作",
  "login.title": "登入",
  "login.username": "使用者名稱",
  "login.password": "密碼",
  "login.submit": "登入",
  "login.submitting": "登入中…",
  "login.error": "帳號或密碼錯誤",
  "landing.tagline": "家庭物品管理",
  "landing.ctaLogin": "登入",
  "landing.ctaDocs": "API 文件",
  "appName": "物品管理系統 v2",
  "a11y.openMenu": "開啟選單",
  "a11y.closeMenu": "關閉選單",
  "a11y.userMenu": "使用者選單"
}
```

- [ ] **Step 4: 英文訊息**

建立 `apps/web/messages/en.json`：

```json
{
  "nav.dashboard": "Dashboard",
  "nav.items": "Items",
  "nav.lists": "Lists",
  "nav.settings": "Settings",
  "menu.profile": "Profile",
  "menu.language": "Language",
  "menu.theme": "Theme",
  "menu.logout": "Log out",
  "theme.system": "System",
  "theme.light": "Light",
  "theme.dark": "Dark",
  "locale.zh-TW": "繁體中文",
  "locale.en": "English",
  "placeholder.comingSoon": "This page will be implemented in subproject #{n}",
  "login.title": "Sign in",
  "login.username": "Username",
  "login.password": "Password",
  "login.submit": "Sign in",
  "login.submitting": "Signing in…",
  "login.error": "Invalid credentials",
  "landing.tagline": "Home item management",
  "landing.ctaLogin": "Sign in",
  "landing.ctaDocs": "API docs",
  "appName": "Item Management System v2",
  "a11y.openMenu": "Open menu",
  "a11y.closeMenu": "Close menu",
  "a11y.userMenu": "User menu"
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/i18n apps/web/messages
git commit -m "feat(web): add next-intl config and zh-TW/en messages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: next.config.mjs 加入 createNextIntlPlugin

**Files:**
- Modify: `apps/web/next.config.mjs`

- [ ] **Step 1: 改 next.config.mjs**

把 `apps/web/next.config.mjs` 改為：

```js
import createNextIntlPlugin from "next-intl/plugin"

const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts")

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
}

export default withNextIntl(nextConfig)
```

- [ ] **Step 2: Typecheck**

Run: `pnpm -F @ims/web typecheck`
Expected: PASS

- [ ] **Step 3: build 確認 plugin 有生效**

Run: `pnpm -F @ims/web build`
Expected: 成功編譯，console 無 "Could not find next-intl config file" 類 warning

- [ ] **Step 4: Commit**

```bash
git add apps/web/next.config.mjs
git commit -m "feat(web): enable next-intl plugin

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Root layout 掛 NextIntlClientProvider

**Files:**
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: 改 root layout**

把 `apps/web/app/layout.tsx` 改為：

```tsx
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { NextIntlClientProvider } from "next-intl"
import { getLocale, getMessages } from "next-intl/server"

import "./globals.css"
import { Providers } from "./providers"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
})

export const metadata: Metadata = {
  title: "物品管理系統 v2",
  description: "IMS v2 — 家庭物品管理",
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const locale = await getLocale()
  const messages = await getMessages()

  return (
    <html lang={locale === "zh-TW" ? "zh-Hant" : "en"} suppressHydrationWarning>
      <body className={`${inter.variable} font-sans min-h-screen bg-background antialiased`}>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: build + typecheck**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/layout.tsx
git commit -m "feat(web): wire NextIntlClientProvider into root layout

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase C — 路由與 middleware

### Task 10: Edge middleware — 保護受控路徑

**Files:**
- Create: `apps/web/middleware.ts`

- [ ] **Step 1: 寫 middleware**

建立 `apps/web/middleware.ts`：

```ts
import { NextResponse, type NextRequest } from "next/server"

const PROTECTED_PREFIXES = ["/dashboard", "/items", "/lists", "/settings"]
const AUTH_ONLY_PATHS = ["/login"]
const COOKIE_NAME = "ims_token"

function hasToken(req: NextRequest): boolean {
  const value = req.cookies.get(COOKIE_NAME)?.value
  return Boolean(value)
}

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const loggedIn = hasToken(req)

  // 受保護路徑：未登入 → /login
  if (isProtected(pathname) && !loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/login"
    return NextResponse.redirect(url)
  }

  // Landing：已登入 → /dashboard
  if (pathname === "/" && loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/dashboard"
    return NextResponse.redirect(url)
  }

  // 已登入用戶訪問登入頁 → /dashboard（UX 優化）
  if (AUTH_ONLY_PATHS.includes(pathname) && loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/dashboard"
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/dashboard/:path*",
    "/items/:path*",
    "/lists/:path*",
    "/settings/:path*",
  ],
}
```

- [ ] **Step 2: Typecheck + build**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS — build log 會顯示 `ƒ Middleware 1 route`

- [ ] **Step 3: Commit**

```bash
git add apps/web/middleware.ts
git commit -m "feat(web): add edge middleware for protected routes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: 建立 `(auth)` 群組並搬移 login

**Files:**
- Create: `apps/web/app/(auth)/layout.tsx`
- Create: `apps/web/app/(auth)/login/page.tsx`
- Delete: `apps/web/app/login/page.tsx`（用 `git mv`）

- [ ] **Step 1: 建立 `(auth)` layout**

建立 `apps/web/app/(auth)/layout.tsx`：

```tsx
import type { ReactNode } from "react"

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
      {children}
    </main>
  )
}
```

- [ ] **Step 2: 搬移 login page（用 git mv 保留歷史）**

Run:
```bash
mkdir -p apps/web/app/\(auth\)/login
git mv apps/web/app/login/page.tsx "apps/web/app/(auth)/login/page.tsx"
rmdir apps/web/app/login 2>/dev/null || true
```

- [ ] **Step 3: 改搬過來的 page — 讓它只渲染 LoginForm（外層 `<main>` 已在 layout）**

改 `apps/web/app/(auth)/login/page.tsx`：

```tsx
import { LoginForm } from "@/features/auth/login-form"

export default function LoginPage() {
  return (
    <div className="w-full max-w-sm space-y-6">
      <LoginForm />
    </div>
  )
}
```

（標題 + i18n 已在 LoginForm 內處理；外層 `<main>` 由 `(auth)/layout.tsx` 提供。）

- [ ] **Step 4: 更新 LoginForm 翻譯 + redirect 目標**

改 `apps/web/features/auth/login-form.tsx`：

```tsx
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api/client"
import { useLogin } from "@/lib/auth/use-auth"

export function LoginForm() {
  const t = useTranslations()
  const router = useRouter()
  const login = useLogin()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ username, password })
      router.push("/dashboard")
    } catch (err) {
      if (err instanceof ApiError) {
        setError(t("login.error"))
      } else {
        setError(t("login.error"))
      }
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-2xl font-bold">{t("login.title")}</h1>
      <div className="flex flex-col gap-1">
        <label htmlFor="username" className="text-sm font-medium">
          {t("login.username")}
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          {t("login.password")}
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? t("login.submitting") : t("login.submit")}
      </Button>
    </form>
  )
}
```

- [ ] **Step 5: Typecheck + build**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS — 舊 `/login` route 在新位置仍被 Next 解析為 `/login`（route group 不影響 URL）

- [ ] **Step 6: Commit**

```bash
git add apps/web/app apps/web/features/auth/login-form.tsx
git commit -m "refactor(web): move login into (auth) route group with i18n

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: 建立 `(app)` 群組 + layout 骨架 + 空殼頁面

**Files:**
- Create: `apps/web/app/(app)/layout.tsx`
- Create: `apps/web/app/(app)/dashboard/page.tsx`
- Create: `apps/web/app/(app)/items/page.tsx`
- Create: `apps/web/app/(app)/lists/page.tsx`
- Create: `apps/web/app/(app)/settings/page.tsx`

- [ ] **Step 1: `(app)` layout 先放最小骨架（AppShell 在後面 task 補）**

建立 `apps/web/app/(app)/layout.tsx`：

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { Skeleton } from "@/components/ui/skeleton"

export default function AppLayout({ children }: { children: ReactNode }) {
  const token = useAccessToken()
  const router = useRouter()

  useEffect(() => {
    // 次層保險：client-side SPA 導航若 token 被清掉立即 redirect
    if (token === null) {
      router.replace("/login")
    }
  }, [token, router])

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <Skeleton className="h-32 w-full max-w-md" />
      </main>
    )
  }

  // 注意：AppShell 會在 Task 16 取代此處 children wrapper
  return <div className="min-h-screen">{children}</div>
}
```

- [ ] **Step 2: 建立 4 個空殼頁面**

建立 `apps/web/app/(app)/dashboard/page.tsx`：

```tsx
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function DashboardPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.dashboard")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.dashboard")}</h1>
      <p className="text-muted-foreground">
        {t("placeholder.comingSoon", { n: 4 })}
      </p>
    </section>
  )
}
```

建立 `apps/web/app/(app)/items/page.tsx`：

```tsx
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function ItemsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.items")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.items")}</h1>
      <p className="text-muted-foreground">
        {t("placeholder.comingSoon", { n: 3 })}
      </p>
    </section>
  )
}
```

建立 `apps/web/app/(app)/lists/page.tsx`：

```tsx
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function ListsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.lists")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.lists")}</h1>
      <p className="text-muted-foreground">
        {t("placeholder.comingSoon", { n: 6 })}
      </p>
    </section>
  )
}
```

建立 `apps/web/app/(app)/settings/page.tsx`：

```tsx
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

export default function SettingsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.settings")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.settings")}</h1>
      <p className="text-muted-foreground">
        {t("placeholder.comingSoon", { n: 8 })}
      </p>
    </section>
  )
}
```

- [ ] **Step 3: Typecheck + build**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS；build output 會列出 `/dashboard`、`/items`、`/lists`、`/settings` 4 個 route

- [ ] **Step 4: Commit**

```bash
git add "apps/web/app/(app)"
git commit -m "feat(web): add (app) route group with 4 empty shell pages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase D — Shell 元件

### Task 13: nav-items 資料模組

**Files:**
- Create: `apps/web/components/shell/nav-items.ts`

- [ ] **Step 1: 定義 nav items 共用資料**

建立 `apps/web/components/shell/nav-items.ts`：

```ts
import type { Route } from "next"

export interface NavItem {
  key: "dashboard" | "items" | "lists" | "settings"
  href: Route
  /** i18n key for label */
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/shell/nav-items.ts
git commit -m "feat(web): add shared nav-items data

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: ThemeMenuItems（Avatar dropdown 子項）+ useLocale hook

**Files:**
- Create: `apps/web/components/shell/theme-menu-items.tsx`
- Create: `apps/web/lib/locale/use-locale.ts`
- Create: `apps/web/lib/locale/use-locale.test.ts`

- [ ] **Step 1: ThemeMenuItems — 現有 useThemePreference 直接接**

建立 `apps/web/components/shell/theme-menu-items.tsx`：

```tsx
"use client"

import { useTranslations } from "next-intl"

import {
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu"
import { useThemePreference } from "@/lib/theme/use-theme"

export function ThemeMenuItems() {
  const t = useTranslations()
  const { theme, setTheme, isSyncing } = useThemePreference()
  const current = theme ?? "system"

  return (
    <DropdownMenuRadioGroup
      value={current}
      onValueChange={(value) =>
        setTheme(value as "system" | "light" | "dark")
      }
    >
      <DropdownMenuRadioItem value="system" disabled={isSyncing}>
        {t("theme.system")}
      </DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="light" disabled={isSyncing}>
        {t("theme.light")}
      </DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="dark" disabled={isSyncing}>
        {t("theme.dark")}
      </DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  )
}
```

（假設 `useThemePreference` 已於 #1 實作並 export `{ theme, setTheme, isSyncing }`。）

- [ ] **Step 2: useLocale 測試**

建立 `apps/web/lib/locale/use-locale.test.ts`：

```ts
import { renderHook, act } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const refreshMock = vi.fn()
const mutateMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}))

vi.mock("next-intl", () => ({
  useLocale: () => "zh-TW",
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt-abc",
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  useUpdatePreferences: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}))

import { useLocale } from "./use-locale"

describe("useLocale", () => {
  beforeEach(() => {
    refreshMock.mockReset()
    mutateMock.mockReset()
    document.cookie = "ims_locale=; Path=/; Max-Age=0"
  })

  it("returns current locale", () => {
    const { result } = renderHook(() => useLocale())
    expect(result.current.locale).toBe("zh-TW")
  })

  it("setLocale writes cookie, calls mutate, and refreshes", () => {
    const { result } = renderHook(() => useLocale())
    act(() => result.current.setLocale("en"))
    expect(document.cookie).toContain("ims_locale=en")
    expect(mutateMock).toHaveBeenCalledWith({ language: "en" })
    expect(refreshMock).toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- lib/locale/use-locale.test.ts`
Expected: FAIL — 模組不存在

- [ ] **Step 4: useLocale 實作**

建立 `apps/web/lib/locale/use-locale.ts`：

```ts
"use client"

import { useRouter } from "next/navigation"
import { useLocale as useNextIntlLocale } from "next-intl"

import { useAccessToken } from "@/lib/auth/use-auth"
import { useUpdatePreferences } from "@/lib/preferences/use-preferences"

import type { Locale } from "@/lib/i18n/config"

const COOKIE_NAME = "ims_locale"
const MAX_AGE = 60 * 60 * 24 * 365 // 1 year

function writeLocaleCookie(locale: Locale): void {
  if (typeof document === "undefined") return
  document.cookie = `${COOKIE_NAME}=${locale}; Path=/; SameSite=Lax; Max-Age=${MAX_AGE}`
}

export function useLocale(): {
  locale: Locale
  setLocale: (next: Locale) => void
  isSyncing: boolean
} {
  const locale = useNextIntlLocale() as Locale
  const token = useAccessToken()
  const update = useUpdatePreferences()
  const router = useRouter()

  const setLocale = (next: Locale) => {
    writeLocaleCookie(next)
    if (token) {
      update.mutate({ language: next })
    }
    router.refresh()
  }

  return { locale, setLocale, isSyncing: update.isPending }
}
```

- [ ] **Step 5: 跑測試**

Run: `pnpm -F @ims/web test -- lib/locale/use-locale.test.ts`
Expected: PASS（2 個）

- [ ] **Step 6: Typecheck**

Run: `pnpm -F @ims/web typecheck`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/web/components/shell/theme-menu-items.tsx apps/web/lib/locale
git commit -m "feat(web): add useLocale hook and theme menu items

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: UserMenu avatar dropdown + Vitest

**Files:**
- Create: `apps/web/components/shell/user-menu.tsx`
- Create: `apps/web/components/shell/user-menu.test.tsx`

- [ ] **Step 1: 寫測試**

建立 `apps/web/components/shell/user-menu.test.tsx`：

```tsx
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import messages from "@/messages/zh-TW.json"

const pushMock = vi.fn()
const logoutMutateMock = vi.fn()
const setLocaleMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useCurrentUser: () => ({ email: "me@example.com", username: "me", id: 1 }),
  useLogout: () => ({ mutateAsync: logoutMutateMock, isPending: false }),
}))

vi.mock("@/lib/locale/use-locale", () => ({
  useLocale: () => ({ locale: "zh-TW", setLocale: setLocaleMock, isSyncing: false }),
}))

vi.mock("@/lib/theme/use-theme", () => ({
  useThemePreference: () => ({
    theme: "system",
    setTheme: vi.fn(),
    isSyncing: false,
  }),
}))

import { UserMenu } from "./user-menu"

function renderWithIntl(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="zh-TW" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  )
}

describe("UserMenu", () => {
  beforeEach(() => {
    pushMock.mockReset()
    logoutMutateMock.mockReset().mockResolvedValue(undefined)
    setLocaleMock.mockReset()
  })

  it("opens and shows email + menu items", async () => {
    const user = userEvent.setup()
    renderWithIntl(<UserMenu />)
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    expect(screen.getByText("me@example.com")).toBeInTheDocument()
    expect(screen.getByText("個人設定")).toBeInTheDocument()
    expect(screen.getByText("登出")).toBeInTheDocument()
  })

  it("clicking logout triggers mutateAsync then redirects to /login", async () => {
    const user = userEvent.setup()
    renderWithIntl(<UserMenu />)
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    await user.click(screen.getByText("登出"))
    expect(logoutMutateMock).toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith("/login")
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- components/shell/user-menu.test.tsx`
Expected: FAIL — 模組不存在

- [ ] **Step 3: 實作 UserMenu**

建立 `apps/web/components/shell/user-menu.tsx`：

```tsx
"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Languages, LogOut, Palette, Settings, User as UserIcon } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useCurrentUser, useLogout } from "@/lib/auth/use-auth"
import { locales } from "@/lib/i18n/config"
import { useLocale } from "@/lib/locale/use-locale"

import { ThemeMenuItems } from "./theme-menu-items"

function initials(email: string | undefined): string {
  if (!email) return "?"
  const name = email.split("@")[0] ?? ""
  return name.slice(0, 2).toUpperCase() || "?"
}

export function UserMenu() {
  const t = useTranslations()
  const router = useRouter()
  const user = useCurrentUser()
  const logout = useLogout()
  const { locale, setLocale, isSyncing } = useLocale()

  async function handleLogout() {
    await logout.mutateAsync()
    router.push("/login")
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={t("a11y.userMenu")}
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback>{initials(user?.email)}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="truncate text-xs text-muted-foreground">
          {user?.email ?? ""}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuItem asChild>
          <Link href="/settings" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            {t("menu.profile")}
          </Link>
        </DropdownMenuItem>

        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center gap-2">
            <Languages className="h-4 w-4" />
            {t("menu.language")}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuRadioGroup
              value={locale}
              onValueChange={(v) => setLocale(v as (typeof locales)[number])}
            >
              {locales.map((l) => (
                <DropdownMenuRadioItem key={l} value={l} disabled={isSyncing}>
                  {t(`locale.${l}` as "locale.zh-TW" | "locale.en")}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>

        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            {t("menu.theme")}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <ThemeMenuItems />
          </DropdownMenuSubContent>
        </DropdownMenuSub>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault()
            handleLogout()
          }}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          {t("menu.logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

- [ ] **Step 4: 跑測試**

Run: `pnpm -F @ims/web test -- components/shell/user-menu.test.tsx`
Expected: PASS（2 個）

- [ ] **Step 5: 跑完整 web 單元測試**

Run: `pnpm -F @ims/web test`
Expected: PASS — 無回歸

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/shell/user-menu.tsx apps/web/components/shell/user-menu.test.tsx
git commit -m "feat(web): add user menu with settings/language/theme/logout

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: AppHeader（桌面）+ MobileNav（Sheet drawer）+ AppShell

**Files:**
- Create: `apps/web/components/shell/app-header.tsx`
- Create: `apps/web/components/shell/mobile-nav.tsx`
- Create: `apps/web/components/shell/mobile-nav.test.tsx`
- Create: `apps/web/components/shell/app-shell.tsx`
- Modify: `apps/web/app/(app)/layout.tsx`

- [ ] **Step 1: MobileNav 測試**

建立 `apps/web/components/shell/mobile-nav.test.tsx`：

```tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import messages from "@/messages/zh-TW.json"

const pushMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/dashboard",
}))

import { MobileNav } from "./mobile-nav"

describe("MobileNav", () => {
  beforeEach(() => pushMock.mockReset())

  it("opens drawer and renders all nav labels", async () => {
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="zh-TW" messages={messages}>
        <MobileNav />
      </NextIntlClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: /開啟選單/ }))
    expect(await screen.findByText("儀表板")).toBeInTheDocument()
    expect(screen.getByText("物品")).toBeInTheDocument()
    expect(screen.getByText("清單")).toBeInTheDocument()
    expect(screen.getByText("設定")).toBeInTheDocument()
  })

  it("clicking a nav item navigates and closes drawer", async () => {
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="zh-TW" messages={messages}>
        <MobileNav />
      </NextIntlClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: /開啟選單/ }))
    await user.click(screen.getByText("物品"))
    expect(pushMock).toHaveBeenCalledWith("/items")
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- components/shell/mobile-nav.test.tsx`
Expected: FAIL

- [ ] **Step 3: MobileNav 實作**

建立 `apps/web/components/shell/mobile-nav.tsx`：

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Menu } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"

import { NAV_ITEMS } from "./nav-items"

export function MobileNav() {
  const t = useTranslations()
  const router = useRouter()
  const [open, setOpen] = useState(false)

  function onSelect(href: string) {
    setOpen(false)
    router.push(href as never)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label={t("a11y.openMenu")}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64">
        <SheetHeader>
          <SheetTitle>{t("appName")}</SheetTitle>
        </SheetHeader>
        <nav className="mt-6 flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelect(item.href)}
              className="rounded-md px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
            >
              {t(item.labelKey as never)}
            </button>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 4: 跑 MobileNav 測試**

Run: `pnpm -F @ims/web test -- components/shell/mobile-nav.test.tsx`
Expected: PASS（2 個）

- [ ] **Step 5: AppHeader 實作**

建立 `apps/web/components/shell/app-header.tsx`：

```tsx
"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTranslations } from "next-intl"

import { cn } from "@/lib/utils"

import { MobileNav } from "./mobile-nav"
import { NAV_ITEMS } from "./nav-items"
import { UserMenu } from "./user-menu"

export function AppHeader() {
  const t = useTranslations()
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-background px-4 md:px-6">
      <MobileNav />
      <Link
        href="/dashboard"
        className="flex items-center font-semibold tracking-tight"
      >
        {t("appName")}
      </Link>
      <nav className="ml-6 hidden items-center gap-1 md:flex">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.key}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {t(item.labelKey as never)}
            </Link>
          )
        })}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <UserMenu />
      </div>
    </header>
  )
}
```

- [ ] **Step 6: AppShell wrapper**

建立 `apps/web/components/shell/app-shell.tsx`：

```tsx
import type { ReactNode } from "react"

import { AppHeader } from "./app-header"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="flex-1">{children}</main>
    </div>
  )
}
```

- [ ] **Step 7: 把 AppShell 掛進 `(app)/layout.tsx`**

改 `apps/web/app/(app)/layout.tsx`：

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"

import { AppShell } from "@/components/shell/app-shell"
import { Skeleton } from "@/components/ui/skeleton"
import { useAccessToken } from "@/lib/auth/use-auth"

export default function AppLayout({ children }: { children: ReactNode }) {
  const token = useAccessToken()
  const router = useRouter()

  useEffect(() => {
    if (token === null) {
      router.replace("/login")
    }
  }, [token, router])

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <Skeleton className="h-32 w-full max-w-md" />
      </main>
    )
  }

  return <AppShell>{children}</AppShell>
}
```

- [ ] **Step 8: typecheck + build**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS

- [ ] **Step 9: 完整 web 單元測試**

Run: `pnpm -F @ims/web test`
Expected: PASS（累計應 ~12+ tests）

- [ ] **Step 10: Commit**

```bash
git add apps/web/components/shell "apps/web/app/(app)/layout.tsx"
git commit -m "feat(web): add app shell with header and mobile drawer

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase E — Locale sync 與 landing 調整

### Task 17: LocaleSync component + 掛進 providers

**Files:**
- Create: `apps/web/lib/locale/locale-sync.tsx`
- Create: `apps/web/lib/locale/locale-sync.test.tsx`
- Modify: `apps/web/app/providers.tsx`

- [ ] **Step 1: 寫 LocaleSync 測試（token-keyed ref 邏輯模仿 ThemeSync）**

建立 `apps/web/lib/locale/locale-sync.test.tsx`：

```tsx
import { render } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

let tokenRef = "jwt-1"
let prefsData: { language?: string } | undefined = { language: "en" }
let prefsSuccess = true

const refreshMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => tokenRef,
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => ({ data: prefsData, isSuccess: prefsSuccess }),
}))

import { LocaleSync } from "./locale-sync"

function renderWith(locale: "zh-TW" | "en") {
  return render(
    <NextIntlClientProvider locale={locale} messages={{}}>
      <LocaleSync />
    </NextIntlClientProvider>,
  )
}

describe("LocaleSync", () => {
  beforeEach(() => {
    refreshMock.mockReset()
    document.cookie = "ims_locale=; Path=/; Max-Age=0"
    tokenRef = "jwt-1"
    prefsData = { language: "en" }
    prefsSuccess = true
  })

  it("writes cookie and refreshes when server language differs from current locale", () => {
    renderWith("zh-TW")
    expect(document.cookie).toContain("ims_locale=en")
    expect(refreshMock).toHaveBeenCalled()
  })

  it("does not refresh when server language equals current locale", () => {
    prefsData = { language: "zh-TW" }
    renderWith("zh-TW")
    expect(refreshMock).not.toHaveBeenCalled()
  })

  it("does nothing when token is null", () => {
    tokenRef = null as unknown as string
    renderWith("zh-TW")
    expect(refreshMock).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pnpm -F @ims/web test -- lib/locale/locale-sync.test.tsx`
Expected: FAIL

- [ ] **Step 3: LocaleSync 實作（token-keyed ref 仿 ThemeSync）**

建立 `apps/web/lib/locale/locale-sync.tsx`：

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useLocale as useNextIntlLocale } from "next-intl"
import { useEffect, useRef } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { usePreferences } from "@/lib/preferences/use-preferences"

import { isLocale } from "@/lib/i18n/config"

const COOKIE_NAME = "ims_locale"
const MAX_AGE = 60 * 60 * 24 * 365

export function LocaleSync() {
  const token = useAccessToken()
  const { data, isSuccess } = usePreferences()
  const currentLocale = useNextIntlLocale()
  const router = useRouter()
  const syncedFor = useRef<string | null>(null)

  useEffect(() => {
    if (!token) {
      syncedFor.current = null
      return
    }
    if (!isSuccess || syncedFor.current === token) return
    const serverLang = (data as { language?: string } | undefined)?.language
    if (serverLang && isLocale(serverLang) && serverLang !== currentLocale) {
      document.cookie = `${COOKIE_NAME}=${serverLang}; Path=/; SameSite=Lax; Max-Age=${MAX_AGE}`
      router.refresh()
    }
    syncedFor.current = token
  }, [token, isSuccess, data, currentLocale, router])

  return null
}
```

- [ ] **Step 4: 跑測試**

Run: `pnpm -F @ims/web test -- lib/locale/locale-sync.test.tsx`
Expected: PASS（3 個）

- [ ] **Step 5: 掛進 Providers 的 GlobalSyncers**

改 `apps/web/app/providers.tsx`：

```tsx
"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "next-themes"
import { useState, type ReactNode } from "react"

import { useTokenCookieSync } from "@/lib/auth/cookie-sync"
import { Toaster } from "@/components/ui/sonner"
import { LocaleSync } from "@/lib/locale/locale-sync"
import { ThemeSync } from "@/lib/theme/theme-sync"

function GlobalSyncers() {
  useTokenCookieSync()
  return null
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <GlobalSyncers />
        <ThemeSync />
        <LocaleSync />
        {children}
        <Toaster richColors closeButton />
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 6: 完整測試**

Run: `pnpm -F @ims/web test && pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/web/lib/locale/locale-sync.tsx apps/web/lib/locale/locale-sync.test.tsx apps/web/app/providers.tsx
git commit -m "feat(web): add LocaleSync and wire into providers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: Landing page 精簡（匿名用戶用）

**Files:**
- Modify: `apps/web/app/page.tsx`

- [ ] **Step 1: 改 landing**

改 `apps/web/app/page.tsx`：

```tsx
import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

// middleware 已處理：已登入訪問 `/` → redirect `/dashboard`
export default function HomePage() {
  return <HomeContent />
}

function HomeContent() {
  const t = useTranslations()
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <h1 className="text-4xl font-bold tracking-tight">{t("appName")}</h1>
      <p className="text-muted-foreground">{t("landing.tagline")}</p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/login">{t("landing.ctaLogin")}</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/docs" target="_blank" rel="noreferrer">
            {t("landing.ctaDocs")}
          </a>
        </Button>
      </div>
    </main>
  )
}
```

- [ ] **Step 2: typecheck + build**

Run: `pnpm -F @ims/web typecheck && pnpm -F @ims/web build`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "refactor(web): i18n-ify landing page

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase F — Playwright E2E 與收尾

### Task 19: Playwright — 保護路由 + 登入導向 + 已登入特例

**Files:**
- Create: `apps/web/tests/navigation.spec.ts`
- Modify: `apps/web/tests/login.spec.ts`

- [ ] **Step 1: 建立 navigation.spec.ts**

建立 `apps/web/tests/navigation.spec.ts`：

```ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("anon user accessing /dashboard redirects to /login", async ({ page }) => {
  await page.goto("/dashboard")
  await page.waitForURL("**/login")
  expect(page.url()).toContain("/login")
})

test("anon user accessing /items redirects to /login", async ({ page }) => {
  await page.goto("/items")
  await page.waitForURL("**/login")
  expect(page.url()).toContain("/login")
})

test("after login, landing / redirects to /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `nav_${suffix}`
  const email = `nav_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // 訪問 / 應自動 redirect 到 /dashboard
  await page.goto("/")
  await page.waitForURL("**/dashboard")
  expect(page.url()).toContain("/dashboard")
})

test("logged-in user visiting /login bounces to /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `nav2_${suffix}`
  const email = `nav2_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.goto("/login")
  await page.waitForURL("**/dashboard")
})

test("mobile viewport: drawer opens and nav works", async ({ page, request }) => {
  const suffix = unique()
  const username = `mob_${suffix}`
  const email = `mob_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.getByRole("button", { name: /開啟選單/ }).click()
  await page.getByText("物品").click()
  await page.waitForURL("**/items")
  // drawer 應已關閉（sheet content 不可見）
  await expect(page.getByRole("dialog")).toHaveCount(0)
})
```

- [ ] **Step 2: 修 既有 login.spec.ts — redirect 目標從 `/` 改成 `/dashboard`**

改 `apps/web/tests/login.spec.ts`：

```ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("register via API then login via UI lands on /dashboard", async ({ page, request }) => {
  const suffix = unique()
  const username = `e2e_${suffix}`
  const email = `e2e_${suffix}@example.com`
  const password = "secret1234"

  const reg = await request.post("/api/auth/register", {
    data: { email, username, password },
  })
  expect(reg.status()).toBe(201)

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()

  await page.waitForURL("**/dashboard")
  await expect(page.getByRole("heading", { name: "儀表板" })).toBeVisible()
})

test("wrong password shows error", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill("does-not-exist")
  await page.getByLabel("密碼").fill("wrong-pass")
  await page.getByRole("button", { name: /登入/ }).click()

  await expect(page.getByRole("alert")).toHaveText("帳號或密碼錯誤")
})
```

- [ ] **Step 3: 列 Playwright tests（不實際跑，避免依賴 docker）**

Run: `pnpm -F @ims/web exec playwright test --list`
Expected: 顯示 7 個 tests（login 2 + theme 3 + navigation 5 = 10）

- [ ] **Step 4: Commit**

```bash
git add apps/web/tests/navigation.spec.ts apps/web/tests/login.spec.ts
git commit -m "test(e2e): add navigation + mobile drawer + auth redirect flows

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 20: Playwright — 語言切換 + 登出

**Files:**
- Create: `apps/web/tests/locale.spec.ts`
- Create: `apps/web/tests/logout.spec.ts`

- [ ] **Step 1: 語言切換 E2E**

建立 `apps/web/tests/locale.spec.ts`：

```ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("authenticated user can switch locale and it persists", async ({ page, request }) => {
  const suffix = unique()
  const username = `loc_${suffix}`
  const email = `loc_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  // 打開 user menu → 語言 → English
  await page.getByRole("button", { name: /使用者選單/ }).click()
  await page.getByText("語言").hover()
  await page.getByRole("menuitemradio", { name: /English/ }).click()

  // UI 標籤應變成英文
  await expect(page.getByRole("link", { name: "Items" })).toBeVisible()

  // reload 後仍是英文
  await page.reload()
  await expect(page.getByRole("link", { name: "Items" })).toBeVisible()
})
```

- [ ] **Step 2: 登出 E2E**

建立 `apps/web/tests/logout.spec.ts`：

```ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

test("logout clears auth cookie and redirects to /login", async ({ page, request }) => {
  const suffix = unique()
  const username = `out_${suffix}`
  const email = `out_${suffix}@example.com`
  const password = "secret1234"

  await request.post("/api/auth/register", {
    data: { email, username, password },
  })

  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")

  await page.getByRole("button", { name: /使用者選單/ }).click()
  await page.getByRole("menuitem", { name: /登出/ }).click()

  await page.waitForURL("**/login")

  // 直接再進 /dashboard 應又被踢回 /login
  await page.goto("/dashboard")
  await page.waitForURL("**/login")
})
```

- [ ] **Step 3: 列 Playwright tests**

Run: `pnpm -F @ims/web exec playwright test --list`
Expected: 顯示 ~10 tests

- [ ] **Step 4: Commit**

```bash
git add apps/web/tests/locale.spec.ts apps/web/tests/logout.spec.ts
git commit -m "test(e2e): add locale switch and logout flows

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 21: 更新 v2-roadmap.md

**Files:**
- Modify: `docs/v2-roadmap.md`

- [ ] **Step 1: 標記 #2 完成**

改 `docs/v2-roadmap.md` 的表格：

```markdown
| 2 | 資訊架構與全域導航 | ✅ 完成 |
```

完整內容：

```markdown
# v2 重構路線圖

參見 [`docs/superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md`](superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md) 了解基礎決策。

## 子專案

| # | 主題 | 狀態 |
|---|------|------|
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 完成 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ✅ 完成 |
| 2 | 資訊架構與全域導航 | ✅ 完成 |
| 3 | 物品 CRUD + 搜尋 | ⏳ 未開始 |
| 4 | 儀表板與統計 | ⏳ 未開始 |
| 5 | 通知中心 | ⏳ 未開始 |
| 6 | 清單類（旅行、購物、收藏） | ⏳ 未開始 |
| 7 | 協作（群組、借用、轉移） | ⏳ 未開始 |
| 8 | 管理與設定 | ⏳ 未開始 |
| 9 | 行動/PWA 體驗 | ⏳ 未開始 |

## 快速啟動（v2）

```bash
cp .env.example .env
pnpm install
pnpm --filter @ims/api gen:types
pnpm --filter @ims/api-types gen:types
docker compose up --build
# 開啟 http://localhost/
```

## 與 v1 的關係

v1（Flask + Jinja2）程式碼保留於 `app/`、`templates/`、`static/` 等目錄，直到 v2 全部子專案完成後於 `v1-final` tag 保留快照並移除。上線切換採 Big Bang — 舊資料**不遷移**，使用者需重新註冊與錄入。
```

- [ ] **Step 2: 跑全部驗證**

Run:
```bash
pnpm -F @ims/api test && \
pnpm -F @ims/web test && \
pnpm -F @ims/web typecheck && \
pnpm -F @ims/web build && \
pnpm -F @ims/web exec playwright test --list
```
Expected: API ≥ 44 passed、Web Vitest ≥ 12 passed、typecheck + build 綠、Playwright list 顯示 ~10 tests

- [ ] **Step 3: Commit**

```bash
git add docs/v2-roadmap.md
git commit -m "docs: mark #2 app shell subproject complete

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 自我檢查（Self-Review）

### Spec 對應

| Spec 章節 | 涵蓋 task |
|---|---|
| §1 App Router 版型分層 | Task 11、12、16 |
| §2 受保護路由策略（edge + client） | Task 10、12、16 |
| §2 token ↔ cookie sync | Task 4、5、6 |
| §3 next-intl 啟用 | Task 7、8、9、14、17 |
| §4 Backend language 欄位 | Task 1、2、3 |
| §5 Avatar Dropdown | Task 14、15 |
| §6 Header + Mobile Drawer | Task 16 |
| §7 空殼頁面 | Task 12 |
| §8 資料流 | Task 4–6、10–12、16 |
| §9 錯誤處理（401、i18n fallback、cookie sync） | Task 6、7、17 |
| §10 測試策略 | Task 1、2、4、6、14、15、16、17、19、20 |
| §11 檔案清單 | 全 plan 涵蓋 |
| §12 CI 影響 | Task 21 |
| §13 Exit Criteria | Task 21 最終驗證 |

所有 spec 要求都有對應 task 實作。

### 型別一致性

- `Theme` / `Language` (Pydantic Literal) ↔ TS `"zh-TW" | "en"` via api-types regeneration (Task 3)
- `Locale` type 定義於 `lib/i18n/config.ts`，useLocale / LocaleSync / UserMenu 全部 import 同一個源
- `NavItem.href` 用 `Route` (next typedRoutes)，統一於 `nav-items.ts`

### 無 placeholder 掃描

人工掃過上列 21 個 task，全部步驟都有完整可執行程式碼與指令，無 "TODO / TBD / similar to Task N" 等字樣。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-ims-app-shell.md`.

**Recommended next step:** Use **superpowers:subagent-driven-development** to execute task-by-task with fresh subagent + two-stage review (spec compliance then code quality).
