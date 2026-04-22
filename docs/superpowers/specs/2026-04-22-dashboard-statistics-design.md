# #4 儀表板與統計 — 設計文件

**批准日期**: 2026-04-22
**對應 v1 功能**: `/dashboard`、`/statistics`

## 1. 目標

登入後提供「快速總覽」(`/dashboard`) 與「深入統計」(`/statistics`) 兩個頁面,讓使用者一眼看到物品分佈與近期活動。

## 2. 範圍

### 2.1 In scope

- 後端:`/api/stats/*` 五個唯讀端點 (owner-scoped、排除 soft-deleted)
- 前端:
  - `/dashboard` 頁面 — 4 張 stat cards + 最近 5 筆物品 + quick links
  - `/statistics` 頁面 — 3 張 chart cards (category doughnut、location bar、tag top-10 bar)
  - `/` landing 在已登入時自動 redirect → `/dashboard`
- 圖表:Recharts (SSR-friendly、shadcn 風格相容)
- i18n:`dashboard.*`、`stats.*` 命名空間 (zh-TW + en)
- 測試:API pytest + Web Vitest + Playwright E2E

### 2.2 Out of scope (延後)

- **到期警示 / 低庫存 / 保養提醒 / 借出統計** — 功能模型尚未實作 (#5/#7 之後)
- **可設定 widgets** (v1 的 `dashboard_widgets` JSON 欄位) — 等 #8 管理與設定
- **資料完整度** (v1 有 `with_photo / with_location / with_type` 百分比) — photo 屬於圖片上傳子專案,type 在 v2 改成 tag
- **時間序列 / 歷史趨勢** — v2 沒做 audit log,先略過
- **匯出** (CSV / Excel)

## 3. 架構

沿用 #0/#2/#3 分層:

```
FastAPI route (/api/stats/*)
 → StatsService (授權 + 彙總邏輯)
 → StatsRepository (SQL GROUP BY + JOIN)
 → SQLAlchemy async
```

Web:

```
Next.js App Router /dashboard, /statistics
 → React Query hooks (useOverview, useByCategory, ...)
 → API Client (apps/web/lib/api/stats.ts)
 → Recharts 圖表元件
```

URL-driven state 無,所有 stats 依使用者隔離、不分享連結。

## 4. API 端點

全部 `GET`,需要 Bearer token,owner-scoped,排除 `is_deleted=true`。

### 4.1 `GET /api/stats/overview`

Response `200`:

```json
{
  "total_items": 42,
  "total_quantity": 120,
  "total_categories": 5,
  "total_locations": 3,
  "total_tags": 12
}
```

實作:五個 `COUNT(*)` / `SUM(quantity)` 查詢,全部一次 `asyncio.gather`。

### 4.2 `GET /api/stats/by-category`

Response `200`:

```json
[
  {"category_id": 1, "name": "電子產品", "count": 15},
  {"category_id": null, "name": null, "count": 8}
]
```

- 含 `NULL` category (`category_id=null, name=null`) 代表未分類
- 依 `count DESC` 排序
- SQL:`SELECT category_id, name, COUNT(*) FROM items LEFT JOIN categories ... WHERE owner_id=? AND is_deleted=false GROUP BY category_id, name`

### 4.3 `GET /api/stats/by-location`

Response `200`:

```json
[
  {"location_id": 1, "label": "1F / 客廳", "count": 12},
  {"location_id": null, "label": null, "count": 5}
]
```

- `label` 組合 `floor / room / zone`,`" / "` 分隔,空欄位略過
- 依 `count DESC` 排序
- 含未定位項 (`location_id=null`)

### 4.4 `GET /api/stats/by-tag?limit=10`

Query param `limit`: 1..50,預設 10。

Response `200`:

```json
[
  {"tag_id": 3, "name": "常用", "count": 9}
]
```

- 依 `count DESC` 排序,取前 N
- 不含零使用率 tag (JOIN `item_tags` 後 GROUP BY,自然排除)

### 4.5 `GET /api/stats/recent?limit=10`

Query param `limit`: 1..20,預設 5。

Response `200`:回傳 `ItemRead[]`,依 `created_at DESC` 排序,owner-scoped、排除 soft-deleted。

**重用 `ItemsRepository.list_recent()` 方法**。

## 5. 資料模型

**無新增 migration**。所有統計從既有 `items`、`categories`、`locations`、`tags`、`item_tags` 表彙總。

## 6. Web 結構

### 6.1 頁面

| 路徑 | 元件 | 說明 |
|---|---|---|
| `/dashboard` | `DashboardPage` | 總覽 + 最近物品 |
| `/statistics` | `StatisticsPage` | 深入圖表 |
| `/` | 已登入 redirect → `/dashboard` | 未登入保留 landing |

### 6.2 Dashboard 頁面

```
┌─────────────────────────────────────┐
│  Dashboard            [+ 新增物品]   │
├─────────────────────────────────────┤
│ [物品數] [總數量] [分類] [位置]      │
├─────────────────────────────────────┤
│ 最近物品                             │
│ ─ Item 1     2026-04-22 10:00       │
│ ─ Item 2     2026-04-22 09:30       │
│ ...                                  │
│                         [查看全部]   │
├─────────────────────────────────────┤
│ [→ /items]  [→ /statistics]         │
│ [→ /settings/taxonomy]              │
└─────────────────────────────────────┘
```

Skeleton 狀態:四張 card 各自 skeleton,table skeleton。

### 6.3 Statistics 頁面

```
┌─────────────────────────────────────┐
│  Statistics                          │
├─────────────────────────────────────┤
│ ┌───────────────┐ ┌────────────────┐│
│ │ 分類分布       │ │ 位置分布       ││
│ │ (doughnut)    │ │ (bar)          ││
│ └───────────────┘ └────────────────┘│
│ ┌─────────────────────────────────┐ │
│ │ 熱門標籤 top 10 (horizontal bar)│ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

空態:每張圖獨立 `EmptyState` (「尚無資料」+ 建議動作)。

### 6.4 元件拆分

- `components/dashboard/stat-card.tsx` — 單一統計 card (label + number + icon)
- `components/dashboard/recent-items-card.tsx` — table 樣式最近物品
- `components/dashboard/quick-links.tsx` — 導向按鈕組
- `components/stats/category-chart.tsx` — Recharts `PieChart` (doughnut)
- `components/stats/location-chart.tsx` — Recharts `BarChart` (vertical)
- `components/stats/tag-chart.tsx` — Recharts `BarChart` (horizontal layout)
- `components/stats/empty-chart.tsx` — 共用空態

### 6.5 API client + hooks

- `apps/web/lib/api/stats.ts` — `getOverview`, `getByCategory`, `getByLocation`, `getByTag(limit)`, `getRecent(limit)`
- `apps/web/lib/hooks/use-stats.ts` — `useOverview`, `useByCategory`, `useByLocation`, `useByTag`, `useRecent`,`staleTime: 30_000`

### 6.6 i18n 新增 key

**`dashboard.*`**
- `title`: `Dashboard` / `儀表板`
- `overview.items`: `Items` / `物品`
- `overview.quantity`: `Total quantity` / `總數量`
- `overview.categories`: `Categories` / `分類`
- `overview.locations`: `Locations` / `位置`
- `recent.title`: `Recent items` / `最近物品`
- `recent.viewAll`: `View all` / `查看全部`
- `recent.empty`: `No items yet` / `尚無物品`
- `quickLinks.items`: `Manage items` / `管理物品`
- `quickLinks.stats`: `View statistics` / `查看統計`
- `quickLinks.taxonomy`: `Configure categories & locations` / `設定分類與位置`

**`stats.*`**
- `title`: `Statistics` / `統計`
- `byCategory.title`: `By category` / `依分類`
- `byCategory.uncategorized`: `Uncategorized` / `未分類`
- `byLocation.title`: `By location` / `依位置`
- `byLocation.unplaced`: `Unplaced` / `未定位`
- `byTag.title`: `Top tags` / `熱門標籤`
- `empty.title`: `No data yet` / `尚無資料`
- `empty.cta`: `Create some items first` / `先新增一些物品`

**`nav.statistics`**: `Statistics` / `統計` (加到既有 `nav.*`)

### 6.7 Redirect 邏輯

修改 `middleware.ts`:登入狀態下訪問 `/` 時 redirect → `/dashboard`。未登入保留 landing。

實作:讀取 `ims_token` cookie,存在則 redirect。

## 7. 測試

### 7.1 API (pytest)

- `test_stats_routes.py`:
  - `test_overview_empty`:新 user 全 0
  - `test_overview_with_data`:建 2 item + 分類/位置/tag,驗證計數
  - `test_by_category_includes_null`:未分類項出現 `null` bucket
  - `test_by_location_label_format`:樓層/房間/區域組合正確
  - `test_by_tag_limit`:limit=1 只回傳 1 筆
  - `test_by_tag_excludes_zero`:未使用 tag 不出現
  - `test_recent_order`:依 created_at desc
  - `test_cross_owner_isolation`:使用者 A 看不到 B 的統計
  - `test_excludes_soft_deleted`:刪除後不計入
  - `test_limit_validation`:limit=51 → 422

### 7.2 Web unit (Vitest)

- `stat-card.test.tsx`:label + value 正確渲染
- `recent-items-card.test.tsx`:空態 vs 有資料

### 7.3 Web E2E (Playwright)

- `dashboard.spec.ts`:
  - 登入 → 訪問 `/` → redirect 到 `/dashboard`
  - Dashboard 顯示 stat cards、最近物品
  - 點「查看全部」→ 跳 `/items`
- `statistics.spec.ts`:
  - 登入 → 訪問 `/statistics` → 三張圖可見
  - 空 DB → 顯示空態訊息

## 8. Nav 整合

加 `Statistics` 到:
- `nav-items.ts` 主導航陣列
- mobile drawer (`mobile-nav.tsx`)

圖示:Lucide `BarChart3`。

## 9. 非功能需求

- **效能**:所有 stats 端點 < 200ms @ 1k items
- **a11y**:stat cards 使用 `role="group" aria-label=...`,charts 附 `<title>` 說明
- **responsive**:dashboard grid 手機 `grid-cols-2`,桌面 `grid-cols-4`;charts 手機堆疊、桌面並排

## 10. 驗收標準

- [ ] API 五個端點全通 + owner 隔離測試
- [ ] Web dashboard 頁面渲染並通過 E2E
- [ ] Web statistics 頁面渲染並通過 E2E
- [ ] `/` 登入後 redirect → `/dashboard`
- [ ] nav 加入「統計」選項 (zh-TW/en)
- [ ] `pytest` 全綠、`pnpm test` 全綠、`pnpm e2e` 全綠
- [ ] `docs/v2-roadmap.md` 標記 #4 完成
