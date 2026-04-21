# IMS v2 #1 Design System — 設計說明書

> **Status:** Design approved 2026-04-22. Next step: 寫 implementation plan。
>
> **Subproject:** #1 設計系統（接續 [#0 基礎骨架](2026-04-21-ims-rewrite-foundation-design.md)）

## 目標

為 IMS v2 建立完整且可長期延用的設計系統：tokens、主題、完整 shadcn 元件、跨裝置同步的主題偏好、元件展示頁。完成後，#2–#9 的功能子專案只需取用 UI 基元，不應需回頭補強設計系統本身。

## 風格定調

- **視覺語言：** Notion / Linear 風——留白大、資訊密度中偏高、冷色調、內容優先
- **色票：** Slate 中性灰 + 深紫主色（primary）
- **字體：** Inter（Latin，`next/font/google` 載入） + 系統中文字體回退（PingFang TC / Microsoft JhengHei / Noto Sans TC）
- **圓角：** 預設 0.5rem（shadcn `--radius`）
- **陰影：** 輕量、以邊框為主的分層；暗色模式下減少陰影改用邊框對比
- **無障礙：** WCAG AA（對比 4.5:1 文字、3:1 UI 元件）、完整鍵盤操作、尊重 `prefers-reduced-motion`

## 架構概覽

### 1. Design Tokens（CSS Variables）

shadcn 慣例：`apps/web/app/globals.css` 定義 HSL 為 CSS variables，`tailwind.config.ts` 映射到 Tailwind color tokens。

**核心 token groups：**
- `--background` / `--foreground`：頁面底色與主要文字
- `--card` / `--card-foreground`
- `--popover` / `--popover-foreground`
- `--primary` / `--primary-foreground`：深紫 (`262 83% 58%` light / `263 70% 65%` dark，Linear 近似)
- `--secondary` / `--secondary-foreground`：slate 淺調
- `--muted` / `--muted-foreground`：背景色、次要文字
- `--accent` / `--accent-foreground`：hover、focus 強調色
- `--destructive` / `--destructive-foreground`：錯誤、刪除紅
- `--border`、`--input`、`--ring`
- `--radius`：`0.5rem`

**dark mode：** 透過 `html.dark` class 切換（next-themes 管理）。

### 2. Theme Provider

使用 [`next-themes`](https://github.com/pacocoursey/next-themes) 作為 client-side 切換核心。

```tsx
// apps/web/app/providers.tsx
<ThemeProvider attribute="class" defaultTheme="system" enableSystem>
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
</ThemeProvider>
```

**auth-aware hook `useTheme()` 封裝（在 `apps/web/lib/theme/use-theme.ts`）：**
- 未登入：只操作 localStorage（next-themes 預設）
- 登入時：掛載時 `GET /api/users/me/preferences` → 若 `theme` 值與本地不同，以 API 值為準；切換時 `PUT` 同步；API 失敗時 fallback 到 localStorage 並顯示 toast
- 無切換入口（#1 不暴露 UI；#2 的 header 頭像下拉接上）

### 3. Backend User Preferences

**Model (`apps/api/app/models/user.py`):**
```python
preferences: Mapped[dict] = mapped_column(
    JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False,
)
```

**Schema (`apps/api/app/schemas/preferences.py`):**
```python
class PreferencesRead(BaseModel):
    theme: Literal["system", "light", "dark"] = "system"
    # 保留擴充空間：notifications, language, density...
    model_config = ConfigDict(extra="allow")

class PreferencesUpdate(BaseModel):
    theme: Literal["system", "light", "dark"] | None = None
    model_config = ConfigDict(extra="allow")
```

**Routes (`apps/api/app/routes/users.py` — 新檔):**
- `GET /api/users/me/preferences` → `PreferencesRead`
- `PUT /api/users/me/preferences` → merge-update（只改傳入的 keys），回傳新 `PreferencesRead`

兩者皆需 `require_user` dependency。

**Alembic migration `0002_user_preferences.py`：**
- `op.add_column('users', sa.Column('preferences', JSONB, nullable=False, server_default=text("'{}'::jsonb")))`
- downgrade 刪除欄位

**為何 JSONB 而非多個 columns：** #5（通知）、#8（管理與設定）會再加一堆 user preference keys（通知頻率、語系、密度、儀表板版面…），事先保留彈性比每次 migrate 好。

### 4. 元件庫清單（shadcn/ui）

安裝 31 個元件（含 #0 已完成的 Button — 新增 30 個）：

**Forms**
- Input, Label, Textarea, Select, Checkbox, Radio Group, Switch, Slider
- Form（react-hook-form + zod 整合）

**Overlays**
- Dialog, Sheet, Popover, Dropdown Menu, Tooltip, Alert Dialog

**Feedback**
- Toast（sonner）, Alert, Badge, Skeleton, Progress

**Navigation**
- Tabs, Breadcrumb, Pagination, Command（cmdk）

**Data Display**
- Card, Table, Avatar, Separator, Accordion, Scroll Area

**安裝方式：** `pnpm dlx shadcn@latest add <name>` 逐個安裝（或用 `shadcn` CLI 批次），確保 `components.json` 設定正確（New York style、lucide icons、slate base color）。

**不安裝（或延後到需要時）：** Calendar、Date Picker、Collapsible、Context Menu、Hover Card、Menubar、Navigation Menu、Resizable、Toggle、Toggle Group、Input OTP、Chart。

### 5. 元件展示頁

**路徑：** `apps/web/app/__dev/components/page.tsx`

**可見性守衛：**
```tsx
import { notFound } from "next/navigation"
import { unstable_noStore } from "next/cache"

export default function ComponentsShowcase() {
  unstable_noStore()
  if (process.env.NODE_ENV === "production"
      && process.env.NEXT_PUBLIC_ENABLE_DEV_ROUTES !== "1") {
    notFound()
  }
  return <Showcase />
}
```

**內容：** 每個元件一個 section，標題 + 簡述 + 2–3 個典型用法 + a11y 備註。light/dark 切換按鈕（純展示頁用，不走 API）。

### 6. 資料流圖

```
[App mount]
    ↓
[next-themes 讀 localStorage or system]
    ↓
[若 useCurrentUser() 有值]
    ↓
[TanStack Query: GET /api/users/me/preferences]
    ↓
[若 server theme ≠ local theme → setTheme(server.theme)]
    ↓
[使用者切換 (將於 #2 實作 UI)]
    ↓
[useTheme hook: setTheme(next) → localStorage write]
    ↓
[若已登入 → useMutation: PUT ...preferences]
    ↓ 成功: queryClient.invalidate  /  失敗: 保留本地值 + toast('同步失敗')
```

### 7. 錯誤處理

- API 失敗（network、401、5xx）：記錄到 console、顯示 toast、保留 localStorage 值作為 source of truth
- localStorage 不可用（隱私模式）：next-themes 自動回退 in-memory
- Hydration mismatch：next-themes 在 `<script>` 層處理，已驗證與 App Router SSR 相容

### 8. 測試策略

**API (`apps/api/tests/test_preferences.py`):**
- GET 未登入 → 401
- GET 登入但從未設定過 → 空物件（或預設 `{theme: "system"}`，看實作選擇）
- PUT theme=dark → GET 回傳 `{theme: "dark"}`
- PUT 多 keys → merge 而非覆寫
- PUT 已知 key 用不在枚舉內的值 → 422

**Web (`apps/web/tests/theme.spec.ts`，Playwright E2E):**
- 未登入切換主題 → 重新整理仍為該主題（localStorage）
- 登入 → 主題從 API 還原（在裝置 A 設定 dark，登入裝置 B 應該是 dark）
- 登入狀態切換主題 → API 被呼叫且回傳一致

**Vitest（元件層級）：** 為 `use-theme` hook 寫 unit test，mock localStorage + TanStack Query。

### 9. CI 影響

- CI web job 新增：`pnpm --filter @ims/web test`（Vitest）
- Playwright 新增 `theme.spec.ts` 案例（#0 已有 login.spec.ts）
- API 測試從 16 增加到 ~20（新增 preferences 測試）

### 10. 非目標（延後）

- **Theme toggle UI 入口** → #2 header 頭像下拉
- **next-intl messages 實際內容** → #2
- **Logo / 品牌插畫 / 動畫規範** → 視需要新開 #1.5 或在 #9 PWA 時處理
- **Storybook** → 現階段以 `__dev/components` 頁面替代；若元件快速增加到 100+ 才考慮
- **Chart / DataViz 元件** → #4 儀表板時再引入 recharts 或類似
- **Date Picker** → #3 物品 CRUD 如有日期欄位時再裝

### 11. 檔案清單（預計新增 / 修改）

**新增：**
- `apps/web/lib/theme/use-theme.ts`、`theme-provider.tsx`
- `apps/web/lib/preferences/use-preferences.ts`
- `apps/web/components/ui/{input,label,textarea,select,...}.tsx`（27 個）
- `apps/web/app/__dev/components/page.tsx`
- `apps/web/app/__dev/components/sections/*.tsx`（依元件群組拆分）
- `apps/web/tests/theme.spec.ts`
- `apps/api/app/schemas/preferences.py`
- `apps/api/app/routes/users.py`
- `apps/api/app/services/preferences_service.py`
- `apps/api/app/repositories/preferences_repository.py`
- `apps/api/alembic/versions/0002_user_preferences.py`
- `apps/api/tests/test_preferences.py`

**修改：**
- `apps/web/app/globals.css`：擴充完整 light/dark tokens
- `apps/web/tailwind.config.ts`：映射新 tokens（若尚未齊全）
- `apps/web/app/providers.tsx`：加 `ThemeProvider`
- `apps/web/app/layout.tsx`：`<body>` 加 `font-sans` 套用 Inter
- `apps/web/package.json`：新增 `next-themes`、`sonner`、`cmdk`、`@hookform/resolvers`（`react-hook-form` + `zod` 於 #0 已安裝但未使用，#1 開始啟用）
- `apps/api/app/models/user.py`：加 `preferences` column
- `apps/api/app/main.py`：註冊 users router

### 12. 完成條件（Exit Criteria）

- [ ] `pnpm --filter @ims/web build` 綠（含所有新元件）
- [ ] `pnpm --filter @ims/api test` 綠（含新增的 preferences 測試）
- [ ] `pnpm --filter @ims/web test` 綠（Vitest hook 測試）
- [ ] Playwright E2E 新增的主題持久化案例通過
- [ ] 訪問 `/__dev/components`（dev 環境）可見所有 28 個元件且 light/dark 皆正常
- [ ] 生產環境訪問 `/__dev/components` → 404
- [ ] Alembic migration 在空 DB 與已有資料的 DB 上升/降級皆正常
- [ ] Lighthouse a11y score ≥ 95（在 showcase 頁與 `/login` 頁測試）

---

## 與 v1 的關係

v1 的 Jinja 樣板 + 自訂 CSS 不影響此設計；v1 CSS 維持原狀，v2 所有 UI 皆走 Tailwind + shadcn tokens。
