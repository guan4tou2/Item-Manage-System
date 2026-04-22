# IMS v2 子專案 #3: 物品 CRUD + 搜尋 設計規格

**日期:** 2026-04-22
**狀態:** Draft — 待 writing-plans 轉為實作計畫
**前置子專案:** #0 Rewrite Foundation、#1 Design System、#2 App Shell
**後續子專案:** #4 (圖片/檔案上傳,待定)、#N (自訂欄位,待定)

---

## 1. 目標

為 IMS v2 實作物品管理核心: 建立、列出、檢視、編輯、刪除物品,支援搜尋、多維度篩選、標籤、分類、位置。**單一使用者看自己的資料** — 不做分享/共用。

交付後使用者可在 v2 完整管理個人物品清單。

## 2. 範圍

### 2.1 In scope

- Items CRUD (list、detail、create、edit、soft delete)
- 搜尋 (名稱 + 描述,case-insensitive ILIKE)
- 篩選 (分類、位置、標籤)
- 標籤 (多對多,寫入時自動建立,用於 autocomplete)
- 分類 (樹狀結構,parent-child)
- 位置 (floor / room / zone 三欄位,扁平結構)
- 分類與位置的管理 UI (`/settings/taxonomy`)
- API 層 (FastAPI async + SQLAlchemy) + Alembic migration
- Web 層 (Next.js App Router,React Query,React Hook Form + Zod)
- 完整測試 (API pytest、Web Vitest + Playwright)

### 2.2 Out of scope (延後到獨立子專案)

- **圖片/附件上傳** — 需要檔案儲存基礎設施 (S3/本地),單獨立子專案
- **自訂欄位 (custom fields)** — schemaless JSON + 動態表單 + 驗證,單獨子專案
- **v1 資料匯入** — v2 為全新重寫;v1 獨立運作,日後評估匯入工具
- **物品分享/可見度/權限** — v1 的 `visibility`、`shared_with`;單一使用者模式不需要
- **借出管理** (item_loan)
- **Git-like 版本歷史** (item_version)
- **匯出** (CSV / Excel)
- **折舊、維護、保固、保固到期、使用期限**
- **數量變動歷史** (quantity_log)
- **盤點** (stocktake)
- **圖片地圖座標 / floor plan**
- **拖曳排序分類**
- **Postgres Full-Text Search** (ILIKE 對 v2 初期規模夠用)
- **Quantity 警戒 / 補貨 (SafetyStock、ReorderLevel)**
- **物品之間關聯 (related_items)**

## 3. 架構

FastAPI routes → services (授權 + 業務邏輯) → repositories (資料存取) → SQLAlchemy async models。與 #0、#2 的分層一致。

Next.js App Router: server components 處理 SEO / 初始資料載入,client components 處理互動 (表單、搜尋、篩選)。React Query 管 server state,URL query params 管 filter / pagination state 以利分享與深連結。

## 4. 資料模型

新增 Alembic migration `0003_items_taxonomy.py`。

### 4.1 `items`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | UUID (GUID type) | 主鍵,`uuid.uuid4` |
| `owner_id` | UUID FK `users.id` | 必填;index |
| `name` | `String(200)` | 必填 |
| `description` | `Text` | nullable |
| `category_id` | `Integer` FK `categories.id` | nullable;ON DELETE SET NULL |
| `location_id` | `Integer` FK `locations.id` | nullable;ON DELETE SET NULL |
| `quantity` | `Integer` | default 1,CHECK ≥ 0 |
| `notes` | `Text` | nullable |
| `is_deleted` | `Boolean` | default false,index |
| `created_at` | `DateTime(tz=true)` | default `utcnow` |
| `updated_at` | `DateTime(tz=true)` | default + onupdate `utcnow` |

複合 index: `(owner_id, is_deleted)`。

### 4.2 `categories`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | `Integer` PK | auto-increment |
| `owner_id` | UUID FK `users.id` | 必填;index |
| `name` | `String(100)` | 必填 |
| `parent_id` | `Integer` FK `categories.id` | nullable;ON DELETE SET NULL (parent 刪除時子變頂層) |

唯一約束: `(owner_id, parent_id, name)` — 同一使用者同一父層下名稱唯一。

### 4.3 `locations`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | `Integer` PK | auto-increment |
| `owner_id` | UUID FK `users.id` | 必填;index |
| `floor` | `String(50)` | 必填 |
| `room` | `String(50)` | nullable |
| `zone` | `String(50)` | nullable |

### 4.4 `tags`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | `Integer` PK | auto-increment |
| `owner_id` | UUID FK `users.id` | 必填;index |
| `name` | `String(50)` | 必填;normalised (trim + lower) |

唯一約束: `(owner_id, name)`。

### 4.5 `item_tags`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `item_id` | UUID FK `items.id` ON DELETE CASCADE | 複合 PK |
| `tag_id` | `Integer` FK `tags.id` ON DELETE CASCADE | 複合 PK |

## 5. API 規格

所有端點需要 `Authorization: Bearer <token>`。所有查詢自動加 `owner_id = current_user.id` 過濾。

### 5.1 Items

**`GET /api/items`**

Query params:
- `q` (str, optional): 搜尋 name + description (ILIKE `%q%`)
- `category_id` (int, optional)
- `location_id` (int, optional)
- `tag_ids` (list[int], optional,可重複): 含 ANY 這些 tag 的 item
- `page` (int, default 1, min 1)
- `per_page` (int, default 20, min 1, max 100)

Response:
```json
{
  "items": [ItemRead, ...],
  "total": 123,
  "page": 1,
  "per_page": 20
}
```

`ItemRead` 包含 `id`、`name`、`description`、`quantity`、`notes`、`created_at`、`updated_at`、`category: {id, name, parent_id} | null`、`location: {id, floor, room, zone} | null`、`tags: [{id, name}]`。

**`POST /api/items`**

Body (`ItemCreate`):
```json
{
  "name": "...", "description": "...",
  "category_id": 1, "location_id": 2,
  "quantity": 1, "notes": "...",
  "tag_names": ["electronics", "gift"]
}
```

行為:
- 驗證 category / location 屬於該使用者
- `tag_names` 若不存在就建立;正規化 (trim + lower);去重

Response: 201 + `ItemRead`。

**`GET /api/items/{id}`**

Response: `ItemRead` (404 若不存在或屬他人或 `is_deleted`)。

**`PATCH /api/items/{id}`**

Body (`ItemUpdate`,所有欄位 optional):
```json
{
  "name": "...", "description": "...",
  "category_id": 1, "location_id": 2,
  "quantity": 5, "notes": "...",
  "tag_names": ["new", "tags"]
}
```

`tag_names` 語意:
- 未送 (omitted) → 不變更標籤
- 送 `[]` → 清空所有標籤
- 送 `["a", "b"]` → **取代** 為這兩個標籤 (非增量)

Response: `ItemRead` (404/403 同上)。

**`DELETE /api/items/{id}`**

行為: 設 `is_deleted = true`。

Response: 204。

### 5.2 Categories

```
GET    /api/categories           → [{id, name, parent_id, children: [...]}]  樹狀
POST   /api/categories           body: {name, parent_id?} → 201 CategoryRead
PATCH  /api/categories/{id}      body: {name?, parent_id?} → CategoryRead
DELETE /api/categories/{id}      → 204;子分類 parent_id 設 null;引用的 items.category_id 設 null
```

PATCH 禁止將 `parent_id` 設為自己或後代 (循環);違反時回 422,`detail` = `"category parent would create cycle"`。

### 5.3 Locations

```
GET    /api/locations            → [LocationRead]  按 floor, room, zone 排序
POST   /api/locations            body: {floor, room?, zone?}
PATCH  /api/locations/{id}
DELETE /api/locations/{id}       引用的 items.location_id 設 null
```

### 5.4 Tags

```
GET    /api/tags                 query: q? (前綴比對) → [TagRead]
```

無 POST/PATCH/DELETE — 標籤由 item 寫入時自動建立。清理未使用標籤列入未來維運任務 (非本子專案)。

### 5.5 錯誤格式

沿用 #0 既有 `{"detail": "..."}`。常見:
- 401 未登入 / token 無效
- 403 存取他人資源
- 404 不存在
- 422 驗證失敗 (Pydantic)

## 6. 前端設計

### 6.1 路由

```
/items                    列表 (預設頁)
/items/new                建立
/items/[id]               詳細
/items/[id]/edit          編輯
/settings/taxonomy        分類 + 位置管理 (Tabs)
```

### 6.2 列表頁 (`/items`)

- Server component 讀取 URL query 作為 initial filter
- Client component 負責:
  - 搜尋欄 (300 ms debounce → 更新 URL)
  - 篩選面板 (桌面側邊、手機 Sheet)
    - 分類: 樹狀 Checkbox (單選),可展開/收合
    - 位置: Select
    - 標籤: Command + Popover 多選,支援 autocomplete
  - 結果: 桌面 Table、手機卡片清單 (用 `@media` / Tailwind responsive)
  - 分頁: 用既有 `components/ui/pagination.tsx`
  - 空狀態: 若無結果且無 filter → 引導 CTA 連到 `/items/new`;有 filter → 顯示 "查無符合"
- URL query 形式: `?q=foo&category=1&location=2&tags=3,4&page=2`

### 6.3 建立 / 編輯表單

- React Hook Form + Zod
- 共用 `ItemForm` 元件,mode = "create" | "edit"
- 欄位:
  - `name` (必填, max 200)
  - `description` (Textarea)
  - `category_id` (TreeSelect:扁平 Select 顯示階層縮排)
  - `location_id` (Select,格式 "Floor / Room / Zone")
  - `quantity` (NumberInput, default 1, min 0)
  - `tag_names` (Command 多選,支援現場輸入新標籤)
  - `notes` (Textarea)
- 送出: 成功 toast + 導向詳細頁
- 離開前若 dirty → `beforeunload` 警告 (瀏覽器原生) + `onBeforeRouteChange` 自訂 Dialog

### 6.4 詳細頁

- 顯示全部欄位 + 建立/更新時間 + 標籤 badges
- 按鈕: Edit (連到 `/items/[id]/edit`)、Delete (AlertDialog 二次確認)
- 麵包屑: 物品 / 物品名稱

### 6.5 Settings / Taxonomy

- `/settings/taxonomy` 頁含兩個 Tabs: 「分類」、「位置」
- 分類 Tab: 樹狀列表 + inline create/edit/delete;新增/編輯用 Dialog 選 parent
- 位置 Tab: 表格 + inline form 新增;編輯/刪除 inline

### 6.6 資料層

- `apps/web/lib/api/items.ts`: `listItems`、`getItem`、`createItem`、`updateItem`、`deleteItem`
- `lib/api/categories.ts`、`lib/api/locations.ts`、`lib/api/tags.ts`
- Hooks (React Query):
  - `useItems(filters)` — key `['items', filters]`
  - `useItem(id)` — key `['items', id]`
  - `useCreateItem()`、`useUpdateItem()`、`useDeleteItem()`
  - `useCategories()`、`useLocations()`、`useTagSearch(q)`
- Mutation onSuccess → `invalidateQueries` 適當 keys
- 樂觀更新僅用於 DELETE

### 6.7 導覽整合

- `components/shell/nav-items.ts` 現有的 "items" 項目保留
- 加 "settings/taxonomy" 子導覽 (展開 settings 群組)

### 6.8 i18n

- 所有 UI 字串進 `messages/zh-TW.json`、`en.json`、`ja.json`
- 命名空間: `items.*` (含 `items.list.*`、`items.form.*`、`items.detail.*`)、`taxonomy.*`

## 7. 測試策略

### 7.1 API (pytest + async SQLite)

**Repository 單元:**
- `items_repository`: CRUD + 搜尋 (`q` ILIKE) + 篩選組合 + 分頁 + 軟刪除忽略
- `categories_repository`: 樹狀查詢、循環偵測
- `locations_repository`、`tags_repository`: CRUD + normalization

**Service:**
- 授權: 他人資料取不到
- Tag 自動建立 + 取代語意
- 刪除分類時 items.category_id 變 null
- Category parent 循環保護

**Route:**
- 每個端點至少 1 個 happy path + 1 個授權失敗 + 1 個驗證失敗
- 分頁 metadata (total / page / per_page) 正確

**涵蓋率目標:** 核心 service + repository ≥ 90%,routes 不求全覆蓋但每端點都要動到。

### 7.2 Web 單元 (Vitest + jsdom)

- `ItemForm` Zod 驗證 (必填、長度、quantity ≥ 0)
- URL 狀態 ↔ filter state 雙向轉換
- 分類樹遞歸渲染
- 標籤多選 autocomplete

### 7.3 E2E (Playwright)

`apps/web/tests/items-crud.spec.ts` 新增:
1. **完整流程**: 登入 → 建立分類 → 建立位置 → 建立物品含標籤 → 回列表看到 → 搜尋找到 → 開啟詳細 → 編輯 → 儲存後看到變更 → 刪除 → 列表消失
2. **篩選**: 建立 2 筆不同分類 → 篩選只勾一個 → 只看到對應的 1 筆
3. **標籤 autocomplete**: 輸入部分名稱 → 出現既有標籤 → 選取 / 新建
4. **授權**: 直接 GET 他人 `/items/[id]` → 404

## 8. 建置順序 (initial plan hint for writing-plans)

1. Migration 0003 (5 張表)
2. Models (Item / Category / Location / Tag + 關聯表)
3. Schemas (Pydantic)
4. Repositories (items、categories、locations、tags)
5. Services (含授權、tag 處理、循環偵測)
6. Routes (items、categories、locations、tags)
7. API tests 全套
8. Frontend API client + typed paths regen
9. Frontend hooks (React Query)
10. Items 列表頁 + 搜尋/篩選
11. Items form (create + edit 共用)
12. Items 詳細頁
13. Settings / Taxonomy 頁
14. i18n 字串完備
15. Vitest 單元測試
16. Playwright E2E
17. README 更新 + v2-roadmap 標記 #3 完成

## 9. 非功能需求

- 效能: 列表頁 SSR + React Query prefetch,初次載入 < 1s (本機 dev)
- 可近用性 (A11y): 所有表單欄位有 label;Sheet / Dialog 支援 Escape + focus trap (Radix 預設)
- Responsive: 手機 / 平板 / 桌面各自最佳化 (表格 → 卡片)
- 國際化: zh-TW / en / ja 三語完整

## 10. 未解決問題 (開工前請作者自決)

無 — 所有設計問題在 brainstorming 階段已決策。若實作中發現遺漏,以當下最小合理方式處理並記錄於該任務的 commit message。

## 11. 驗收條件

- [ ] API 所有端點依規格回傳 + 授權
- [ ] Web 五個頁面完成並通過 E2E
- [ ] 中 / 英 / 日三語字串齊全
- [ ] `pytest` 全綠 (API),`pnpm test` 全綠 (web 單元),`pnpm e2e` 全綠
- [ ] `docs/v2-roadmap.md` 標記 #3 完成

---
