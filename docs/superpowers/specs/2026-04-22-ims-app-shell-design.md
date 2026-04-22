# IMS v2 #2 App Shell 與全域導航 — 設計說明書

> **Status:** Design approved 2026-04-22. Next step: 寫 implementation plan。
>
> **Subproject:** #2 資訊架構與全域導航（接續 [#1 設計系統](2026-04-22-ims-design-system-design.md)）

## 目標

建立 IMS v2 的 app shell：受保護路由殼層、共用 header（logo + nav + avatar dropdown）、手機版 Sheet drawer、四個空殼頁（`/dashboard`、`/items`、`/lists`、`/settings`）、啟用 next-intl（zh-TW / en）。完成後，#3 物品 CRUD 只需在 `/items` 下加 routes，不需再處理 header 或登入守衛。

## 範圍（窄）

- 受保護路由（middleware + client layout）
- 共用 header、mobile drawer、avatar dropdown
- 四個空殼頁面（僅頁標題 + 麵包屑 + 佔位文字）
- next-intl 啟用（僅翻譯 chrome strings）
- 登出流程（Zustand 清空 + cookie 清空 + redirect）

## 非目標（延後）

- 命令面板（⌘K）→ #3
- Sidebar 版型 → 導航項 ≥ 6 時再評估（可能 #8）
- Locale-in-URL（`/en/items`）→ 暫不需要
- Avatar 圖片上傳 → #8
- 通知鈴鐺 → #5
- 全域搜尋 input → #3

## 架構概覽

### 1. App Router 版型分層

```
apps/web/app/
├── (auth)/                    # route group，不影響 URL
│   ├── layout.tsx             # 置中卡片殼層
│   └── login/page.tsx         # 從 app/login 移過來
├── (app)/                     # route group，受保護區
│   ├── layout.tsx             # AppShell
│   ├── dashboard/page.tsx
│   ├── items/page.tsx
│   ├── lists/page.tsx
│   └── settings/page.tsx
├── __dev/                     # 既有，不動
├── layout.tsx                 # root（既有；加 NextIntlClientProvider）
├── page.tsx                   # landing（僅匿名可見，登入則 redirect）
├── globals.css                # 既有
└── providers.tsx              # 既有

apps/web/components/shell/
├── app-shell.tsx              # header + drawer + <main>{children}</main>
├── app-header.tsx             # 桌面 header
├── nav-items.ts               # 導航項資料（共用給 header + drawer）
├── mobile-nav.tsx             # Sheet drawer
├── user-menu.tsx              # avatar dropdown（含語言、主題、登出）
└── theme-menu-items.tsx       # 主題三選一子項

apps/web/middleware.ts         # 新增：未登入 + 受保護路徑 → /login

apps/web/messages/
├── zh-TW.json
└── en.json

apps/web/lib/i18n/
├── config.ts                  # locales、defaultLocale
└── request.ts                 # getRequestConfig

apps/web/lib/locale/
├── use-locale.ts              # 讀寫 locale 的 hook（API sync）
├── locale-sync.tsx            # 仿 ThemeSync，server → next-intl 同步
└── types.ts                   # Locale type re-export（可選）

apps/web/lib/auth/
└── cookie-sync.ts             # token ↔ cookie 同步（export subscribe 函式，由 use-auth.ts 呼叫）
```

### 2. 受保護路由策略（雙層）

**Edge middleware (`middleware.ts`)：**
- matcher：`/(dashboard|items|lists|settings)(.*)`
- 無 `ims_token` cookie → `NextResponse.redirect(/login)`
- 有 cookie 但值為空 → 同樣 redirect
- 不驗 JWT 簽章（edge runtime 不跑 passlib/jose，成本高）

**Client layout (`(app)/layout.tsx`)：**
- 讀 Zustand auth store；若 token 空 → `router.replace("/login")`
- 處理客戶端 SPA 導航時 middleware 未觸發的情境
- 在 token 驗證前渲染 skeleton（避免閃一下受保護內容）

**Landing 特例 (`app/page.tsx`)：**
- middleware 若偵測 cookie 存在且 pathname 為 `/` → redirect `/dashboard`
- 無 cookie → 維持 landing 畫面

**token ↔ cookie sync：**
- #0 Zustand persist 存 localStorage，middleware 看不到
- 新增 subscriber：Zustand store 寫 token 時同步 `document.cookie = "ims_token=1; Path=/; SameSite=Lax; Max-Age=604800"`
- 清空時寫 `Max-Age=0`
- cookie 僅存在性指示（value 永遠 `"1"`），真實 bearer token 仍由 Zustand 提供給 apiFetch
- **不 httpOnly**，因為需在 client-side sync；不含敏感資料（只是旗標）

### 3. next-intl 啟用

**設定：**
```ts
// apps/web/lib/i18n/config.ts
export const locales = ["zh-TW", "en"] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = "zh-TW"
```

```ts
// apps/web/lib/i18n/request.ts
import { getRequestConfig } from "next-intl/server"
import { cookies, headers } from "next/headers"

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const headerStore = await headers()
  const cookieLocale = cookieStore.get("ims_locale")?.value
  const acceptLang = headerStore.get("accept-language") ?? ""
  const locale = normalizeLocale(cookieLocale ?? acceptLang)
  const messages = (await import(`../../messages/${locale}.json`)).default
  return { locale, messages }
})
```

**Provider 接入 (`app/layout.tsx`)：**
- server component 讀 `getLocale()` 和 `getMessages()`
- 傳入 `<NextIntlClientProvider locale messages>`

**語言切換：**
```ts
// apps/web/lib/locale/use-locale.ts
export function useLocale() {
  const locale = useNextIntlLocale()
  const token = useAccessToken()
  const update = useUpdatePreferences()
  const router = useRouter()

  const setLocale = (next: Locale) => {
    document.cookie = `ims_locale=${next}; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 24 * 365}`
    if (token) update.mutate({ language: next })
    router.refresh() // server messages 重讀
  }
  return { locale, setLocale, isSyncing: update.isPending }
}
```

**LocaleSync component：** 仿 `ThemeSync` — `useRef<string | null>` 以 token 為 key，避免 logout 後卡住。從 `usePreferences()` 讀 server language，若與 cookie 不同 → 寫 cookie + `router.refresh()`。

**訊息結構（扁平 key）：**
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
  "login.username": "使用者名稱",
  "login.password": "密碼",
  "login.submit": "登入",
  "landing.tagline": "家庭物品管理",
  "landing.ctaLogin": "登入",
  "landing.ctaDocs": "API 文件"
}
```

### 4. Backend preferences — language 欄位

**Schema 擴充 (`apps/api/app/schemas/preferences.py`)：**
```python
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

**為何顯式 Literal 而非靠 `extra="allow"`：** 422 保護住非法值（e.g. `language="ja"`）避免資料庫累積 garbage；前端 type narrow 更好。

### 5. Avatar Dropdown 結構

```
┌──────────────────┐
│ user@example.com │  ← 帳號 header（不可點擊）
├──────────────────┤
│ ⚙  個人設定       │  → Link /settings
├──────────────────┤
│ 🌐 語言          ►│  → submenu
│    繁體中文 (✓)   │
│    English       │
├──────────────────┤
│ 🎨 主題          ►│  → submenu
│    跟隨系統 (✓)   │
│    淺色          │
│    深色          │
├──────────────────┤
│ 🚪 登出          │  → clear + redirect /login
└──────────────────┘
```

**技術：** shadcn DropdownMenu 的 `DropdownMenuSub` + `DropdownMenuRadioGroup`（勾選指示用）。

### 6. Header 與 Mobile Drawer

**桌面 (`>= md`)：**
```
┌────────────────────────────────────────────────────┐
│ [Logo] [儀表板] [物品] [清單] [設定]     [avatar] │
└────────────────────────────────────────────────────┘
```

**手機 (`< md`)：**
```
┌──────────────────────────────────┐
│ [☰]  [Logo]              [avatar]│
└──────────────────────────────────┘
    ↓ 點 ☰
┌────────────┐
│ × 關閉      │
│ ───────────│
│ 儀表板     │
│ 物品       │
│ 清單       │
│ 設定       │
└────────────┘
```

點擊 nav item → `router.push` + drawer close。

### 7. 空殼頁面模板

每個空殼頁結構：
```tsx
<section className="space-y-4">
  <header>
    <Breadcrumb>
      <BreadcrumbItem>...</BreadcrumbItem>
    </Breadcrumb>
    <h1 className="text-2xl font-semibold">{t("nav.dashboard")}</h1>
  </header>
  <p className="text-muted-foreground">{t("placeholder.comingSoon", { n: 4 })}</p>
</section>
```

對應子專案編號：dashboard → #4；items → #3；lists → #6；settings → #8。

### 8. 資料流圖

```
[首次訪問 /dashboard]
  ↓
[middleware] 無 ims_token → redirect /login
  ↓
[使用者登入] POST /api/auth/login → Zustand setToken(jwt)
  ↓
[Zustand subscriber] document.cookie = ims_token=1
  ↓
[redirect /dashboard] middleware 放行 (cookie 存在)
  ↓
[(app)/layout] 渲染 AppShell
  ↓
[ThemeSync + LocaleSync + usePreferences] server preferences → client
```

### 9. 錯誤處理

- **middleware 認誤：** 若 cookie 存在但 token 實際已失效 → API 回 401 → apiFetch 在 401 時清空 Zustand + cookie + redirect /login
- **i18n 載入失敗：** `getRequestConfig` 嚴格型別檢查，locale 無效 fallback `zh-TW`，messages 檔缺失 → build 期就會失敗
- **cookie sync 時序：** Zustand persist hydration 可能晚於 subscriber 註冊；在 root layout 的 `<script>` 手動讀 localStorage → 寫 cookie 防止首次 SSR 後 redirect loop
- **hydration mismatch：** next-intl server + client 讀同一 locale（從 cookie）；`NextIntlClientProvider` 不會產生 mismatch

### 10. 測試策略

**API (`test_preferences_schemas.py`、`test_preferences_routes.py`):**
- `language="en"` 接受 → PUT 200 + GET 回傳 `{theme, language}`
- `language="ja"` → 422
- language + theme 同時 update → merge 皆保留

**Vitest：**
- `user-menu`：渲染三主題 + 兩語言 + 登出；點選呼叫正確 action
- `mobile-nav`：`Sheet` 開關；點 nav item 觸發 `onOpenChange(false)`
- `cookie-sync`：給定 token=null → `document.cookie` 清空；token=jwt → cookie 寫入
- `use-locale`：setLocale 寫 cookie + mutate + router.refresh

**Playwright：**
- 未登入訪問 `/dashboard` → `/login`
- 登入後 `/` → `/dashboard`
- 登入狀態訪 `/login` → `/dashboard`（UX 優化）
- 手機版（viewport 375）：漢堡 → drawer → 點「物品」→ `/items` + drawer closed
- 切換語言 en → nav 字變 "Items" 等；reload 仍為 en
- 登出 → cookie 清空 + `/login`
- 主題切換仍正常（sanity from #1）

**目標：** API 35 → 38；Vitest 6 → ~12；Playwright 5 → ~10。

### 11. 檔案清單（預計新增 / 修改）

**新增 (web)：**
- `apps/web/middleware.ts`
- `apps/web/app/(auth)/layout.tsx`
- `apps/web/app/(app)/layout.tsx`
- `apps/web/app/(app)/dashboard/page.tsx`
- `apps/web/app/(app)/items/page.tsx`
- `apps/web/app/(app)/lists/page.tsx`
- `apps/web/app/(app)/settings/page.tsx`
- `apps/web/components/shell/*.tsx`（6 個）
- `apps/web/lib/i18n/{config,request}.ts`
- `apps/web/lib/locale/{use-locale.ts,locale-sync.tsx,types.ts}`
- `apps/web/lib/auth/cookie-sync.ts`
- `apps/web/messages/{zh-TW,en}.json`
- `apps/web/tests/{navigation,locale,logout}.spec.ts`（3 個新 E2E）
- `apps/web/components/shell/*.test.tsx`（3 個 Vitest）
- `apps/web/lib/locale/use-locale.test.ts`
- `apps/web/lib/auth/cookie-sync.test.ts`

**修改 (web)：**
- `apps/web/app/layout.tsx`：加 `NextIntlClientProvider`
- `apps/web/app/page.tsx`：landing 精簡；middleware 處理 redirect
- `apps/web/app/login/page.tsx`：移到 `(auth)/login/`
- `apps/web/app/providers.tsx`：加 `LocaleSync`
- `apps/web/lib/auth/use-auth.ts`：呼叫 `cookie-sync.ts` 的 `subscribeTokenToCookie(store)`
- `apps/web/lib/api/client.ts`：401 時清空 auth store + cookie
- `apps/web/next.config.ts`（或新建）：加 `createNextIntlPlugin`
- `packages/api-types/openapi.json` + `src/index.ts`：regenerate

**修改 (api)：**
- `apps/api/app/schemas/preferences.py`：加 `language` Literal
- `apps/api/tests/test_preferences_schemas.py`：+3 tests（valid language / invalid / combined）
- `apps/api/tests/test_preferences_routes.py`：+ language round-trip test

### 12. CI 影響

- API 測試 35 → 38
- Web Vitest 6 → ~12（仍 `vitest run`）
- Playwright 5 → ~10（仍非 CI blocker）
- middleware 會增加 edge bundle；`pnpm build` 目標仍綠

### 13. 完成條件（Exit Criteria）

- [ ] 未登入用戶訪問 `/dashboard|/items|/lists|/settings` → redirect `/login`
- [ ] 登入後 `/` → `/dashboard`
- [ ] Header 顯示 logo + 4 個 nav + avatar dropdown；桌面 / 手機版型正確
- [ ] Avatar dropdown 完整 5 個區塊（email / 設定 / 語言 / 主題 / 登出）
- [ ] 語言切換：UI 立即變；重整仍為新語言；登入時 API 同步成功
- [ ] 主題行為沿用 #1（回歸測試綠）
- [ ] 登出清空 Zustand + cookie + redirect
- [ ] 四個空殼頁含麵包屑 + 中 / 英文佔位文字
- [ ] `pnpm -F @ims/api test` 38 綠
- [ ] `pnpm -F @ims/web test` ~12 綠
- [ ] `pnpm -F @ims/web typecheck` + `build` 綠
- [ ] Playwright list 顯示 ~10 tests
- [ ] Lighthouse a11y ≥ 95（隨機受保護頁）

---

## 與 #1 的關係

- 沿用 `useThemePreference`、`ThemeSync` 的 token-keyed ref 模式（避免 logout regression）
- `LocaleSync` 模仿此模式
- 所有 shadcn 元件已在 #1 安裝，此階段僅消費
