# Phase 28 — Webhook 管理 UI Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 28＋§5.2 設定 IA（「整合與資料 ＞ Webhooks」）、§5.4 狀態契約、§5.6 狀態不得僅以色彩表達、§5.7 響應式（deliveries 寬表格行動版卡片化）。
> 本 phase **無 migration、無 schema 變更**（純查詢端參數＋聚合）；既有資料與 API 呼叫端零破壞。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**；完成即 commit（Conventional Commits，繁中 body）。

**Goal：** 把既有 Webhook 面板（2026-06-23 已含 CRUD＋deliveries 卡＋立即重試）補齊到 Phase 28 規格：**API** 增加 deliveries 篩選（`status`／`event`）與分頁（`offset`）參數＋**統計端點**（成功率、最近成功時間）；**Web** 設定頁「整合與資料 ＞ Webhooks」擴充——deliveries 桌機表格（時間／事件／狀態／嘗試／下次重試）＋行動卡片、狀態篩選（全部／成功／失敗／待重試）、response excerpt 展開／收合、概覽（成功率、最近成功時間）、篩選空態與查詢錯誤態。

**Architecture：** 讀取端擴充。`list_deliveries` service 加條件式 where（`status`／`event`）＋`offset`；新增 `delivery_stats` 聚合（counts＋`last_success_at`）與 `WebhookDeliveryStats` schema；路由參數皆 optional（舊呼叫行為不變）。Web 端 deliveries 改用 `useInfiniteQuery`（PAGE_SIZE=20，`getNextPageParam` 以「末頁長度＝PAGE_SIZE」判斷續頁；篩選切換由 queryKey 自然重置）；桌機 `<Table>`／`md:hidden` 卡片雙渲染（同資料、共用列元件）；excerpt 以 row-local state 展開。**不新增依賴、不動 model／migration。**

**Tech Stack：** FastAPI、SQLAlchemy async（既有 index：`webhook_id`、`created_at`、`event`、`next_retry_at`——查詢足夠、不加索引）、pytest（SQLite in-memory）、React Query（`useInfiniteQuery`）、next-intl、shadcn/ui（`Table`／`Select`／`Skeleton`／`Badge`／`Alert` 既有）、Vitest、Playwright。

**關鍵既有資產（重用，勿重造）：**
- 後端：`apps/api/app/services/webhooks_service.py`——`list_deliveries`（`created_at desc`、`_ensure_owned`）、`is_success`（2xx）、`retry_delivery_now`（**手動重試＝新增 attempt 列**＋清舊列 `next_retry_at`）、`_record_attempt`、`backoff_after`（30s/2m/8m/30m、`MAX_ATTEMPTS`）
- 路由／schema：`apps/api/app/routes/webhooks.py`（deliveries／retry／process-retries）、`apps/api/app/schemas/webhook.py`（`WebhookDeliveryRead`——**不改**）
- 測試範式：`apps/api/tests/test_webhooks.py`（`auth` fixture：register→login→Bearer；httpx `AsyncClient` monkeypatch 範式）、`test_webhook_retry.py`（`db_session` 直插／斷言 attempt 列）
- Web 面板：`apps/web/components/settings/webhook-panel.tsx`（486 行；CRUD＋選取式 deliveries 卡＋重試＋process-retries）、`webhook-panel.test.tsx`（151 行；模組 mock 範式）
- Web client：`apps/web/lib/api/webhooks.ts`＋`webhooks.test.ts`（`global.fetch` mock 範式）
- UI 元件：`components/ui/table.tsx`、`select.tsx`、`skeleton.tsx`、`badge.tsx`、`alert.tsx`（**皆已存在**；無 `collapsible`——excerpt 用 state toggle）
- IA：`settings-nav.ts` integrations 群組已含 `webhooks`（`/settings/webhooks`）；i18n `settings.webhooks.*`（zh-TW／en）

**盤點定案（2026-10-17，實作前一覽）：**
1. **delta 盤點**：面板已含 CRUD／deliveries（limit 50 卡列）／立即重試／process-retries（`9d35104`，2026-06-23）；Phase 28 **只做 delta**——篩選／分頁／概覽／桌機表格／excerpt 展開／查詢錯誤態。CRUD 與 process-retries 不動。
2. **deliveries 互動不重構**：維持「選取 endpoint → 下方列表」（roadmap「展開」語意由選取切換達成）；不改成每卡 disclosure（零回歸既有測試）。
3. **篩選語意（鎖定）**：`success`＝2xx；`failed`＝`status_code IS NULL OR NOT 2xx`（含網路失敗）；`pending`＝`next_retry_at IS NOT NULL`（failed 的子集；已排程重試）。
4. **分頁**：新增 `offset`（ge=0）；`limit` 維持 default 50／1..500——**回應維持裸 list**（不加 total／cursor；UI 以「回傳數＝limit」判定續頁）。「載入更多」PAGE_SIZE＝20。
5. **統計端點獨立**：`GET /api/webhooks/{id}/deliveries/stats` → `{total, succeeded, failed, pending, last_success_at}`；**全量**（不隨篩選變）；`WebhookRead` 不動。
6. **成功率語義**：counts 以**嘗試列**（attempt rows）計——手動／自動重試各產生新列；UI 端 `Math.round(succeeded / total * 100)`；`total = 0` → **不顯示**統計列。
7. **API 相容**：新參數全 optional → 既有呼叫（`limit` only）行為不變；`WebhookDeliveryRead` 欄位不變（不重生成以外無破壞）。
8. **桌機表格欄位**：時間／事件／狀態／嘗試／下次重試＋操作欄；`data-testid="deliveries-table"`（`hidden md:block`）＋行動卡 `data-testid="deliveries-cards"`（`md:hidden`）——§5.7「寬表格行動版卡片化」。
9. **excerpt 展開**：row-local `useState`（按鈕「顯示回應內容／收合」）；表格版展開列為 `<tr><td colSpan>`；`data-testid="delivery-excerpt"`。
10. **載入更多**：`useInfiniteQuery`；`getNextPageParam`＝末頁長度＝PAGE_SIZE ? `pages.length * PAGE_SIZE` : undefined；篩選切換由 queryKey（含 filter）重置。
11. **查詢錯誤態（§5.4 缺口補齊）**：webhooks list／deliveries 查詢 `isError` → 卡內 compact 錯誤＋「重試」（`refetch`）；stats 錯誤 → 靜默隱藏統計列（列表錯誤態獨立呈現，不重複炸）。
12. **篩選空態**：有篩選且 0 筆 →「沒有符合的 delivery」＋「清除篩選」（下一步動作）；無篩選 0 筆 → 既有空態不動。
13. **retry 連動**：立即重試成功後 invalidate deliveries（infinite）＋stats＋webhooks（既有）。
14. **e2e 確定性**：webhook URL 用 `http://127.0.0.1:9/hook`（connection refused 即刻失敗，不依賴外部網路）；建物品觸發**同步** dispatch（`items_service` await）→ `status_code=null` 列＋`next_retry_at` 排程；重試 → 第 2 次列。
15. **行動無障礙**：篩選 chips 與重試按鈕 tap target ≥44px（§5.7）；狀態以 icon＋文字（不單靠色彩，§5.6）。
16. **i18n**：逐鍵插入（勿整檔重寫）——`settings.webhooks.filter.*`／`stats.*`／`pagination`／`excerpt`／`errors.*`／`table.*`。
17. **不做（範圍外）**：webhook 編輯（name／url／secret／events）維持現況（僅 `is_active` toggle）；deliveries retention／清理不在本 phase；process-retries 按鈕保留現狀（維運輔助）；不改 models／migration。

**執行前置：**
1. worktree：`git worktree add .claude/worktrees/phase28-webhook-ui -b claude/phase28-webhook-ui`；**無新 migration**（alembic 維持 `0021`）
2. worktree **無 `.env`**（Phase 27 教訓）：先 `cp .env .claude/worktrees/phase28-webhook-ui/.env`
3. 起堆疊：`ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx`
4. 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `cd apps/web && pnpm test -- <filter>`／`pnpm typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`；e2e `cd apps/web && pnpm exec playwright test --workers=2`

---

## Phase 1: API 參數與統計端點

### Task 1.1: deliveries 篩選／分頁參數

**Files:**
- Modify: `apps/api/app/routes/webhooks.py`、`apps/api/app/services/webhooks_service.py`
- Create: `apps/api/tests/test_webhook_deliveries_query.py`

**TODO:**
- [x] RED：新測試檔（`auth` fixture 複製 `test_webhooks.py` 範式；`db_session` 直插 `WebhookDelivery` 列——可控 `status_code`／`next_retry_at`／`created_at`／`event`）：`status=success` 僅 2xx；`status=failed` 含 `null`＋非 2xx；`status=pending` 僅 `next_retry_at` 非 null；`event=item.created`；`offset`（3 列 limit=2 → 第 1 頁 2 筆、offset=2 → 1 筆；`created_at desc` 序）；組合（status＋offset）；非法 `status=weird` → 422；跨 owner → 404
- [x] GREEN：service `list_deliveries(session, owner_id, webhook_id, *, limit=50, offset=0, status=None, event=None)`——`status`：`WebhookDelivery.status_code.between(200, 299)`／`or_(status_code.is_(None), ~between)`／`next_retry_at.is_not(None)`；`event` 精確比對；`.offset(offset)`；route 加 `offset: int = Query(0, ge=0)`、`status: Literal["success","failed","pending"] | None = Query(None)`、`event: str | None = Query(None, max_length=60)`
- [x] `limit` default 50／`ge=1, le=500` 維持（相容）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_webhook_deliveries_query.py tests/test_webhooks.py tests/test_webhook_retry.py`

### Task 1.2: `GET /api/webhooks/{id}/deliveries/stats`

**Files:**
- Modify: `apps/api/app/routes/webhooks.py`、`apps/api/app/schemas/webhook.py`、`apps/api/app/services/webhooks_service.py`
- Test: `apps/api/tests/test_webhook_deliveries_query.py`（同檔續寫）

**TODO:**
- [x] RED：直插 4 列（2 成功（不同 `created_at`）／1 失敗（`status_code=500`）／1 pending（`status_code=null`＋`next_retry_at`））→ `{total:4, succeeded:2, failed:2, pending:1, last_success_at:較新的成功列 created_at}`；全空 → `{total:0, succeeded:0, failed:0, pending:0, last_success_at:null}`；跨 owner → 404
- [x] GREEN：schema `WebhookDeliveryStats{total:int, succeeded:int, failed:int, pending:int, last_success_at:datetime|None}`；service `delivery_stats(session, owner_id, webhook_id)`——`_ensure_owned`＋counts 聚合（`func.count`＋`case()` 或分開 `select(func.count())` 條件查詢）＋`select(func.max(created_at)).where(2xx)`；route `@router.get("/{webhook_id}/deliveries/stats")`
- [x] 路由無歧義：`/deliveries/stats`（3 段）vs `/deliveries/{delivery_id}/retry`（4 段）

**Commands:**
- 同 T1.1

### Task 1.3: api-types 重生成

**Files:**
- Modify: `packages/api-types/openapi.json`、`packages/api-types/src/index.ts`

**TODO:**
- [x] `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`＋`pnpm --filter @ims/api-types gen:types`
- [x] 確認生成：`WebhookDeliveryStats`；deliveries `GET` 參數新增 `offset`／`status`／`event`
- [x] Commit（比照 Phase 27 慣例，獨立 `chore(api-types)` commit）

---

## Phase 2: Web 面板擴充

### Task 2.1: webhooks API client 擴充

**Files:**
- Modify: `apps/web/lib/api/webhooks.ts`、`apps/web/lib/api/webhooks.test.ts`

**TODO:**
- [x] RED：client 測試——`listWebhookDeliveries(id, { limit, offset, status, event }, token)` query 字串僅帶有值參數（順序無關斷言）；`getWebhookDeliveryStats(id, token)` 打 `/webhooks/{id}/deliveries/stats`；回傳型別 `WebhookDeliveryStats`
- [x] GREEN：`WebhookDeliveryParams { limit?, offset?, status?: 'success'|'failed'|'pending', event? }`；`WebhookDeliveryStats { total, succeeded, failed, pending, last_success_at: string|null }`；既有呼叫端（面板）暫不動（T2.2/T2.3 一起改）

**Commands:**
- `cd apps/web && pnpm test -- lib/api/webhooks`

### Task 2.2: deliveries 桌機表格＋行動卡片＋excerpt 展開＋列表錯誤態

**Files:**
- Modify: `apps/web/components/settings/webhook-panel.tsx`、`webhook-panel.test.tsx`

**TODO:**
- [x] RED：表格渲染——欄頭（時間／事件／狀態／嘗試／下次重試）＋列內容（`第 1 次`、日期、事件 label）；`deliveries-table` 與 `deliveries-cards` 兩容器皆存在（CSS 響應式切換，jsdom 驗 DOM）；excerpt：「顯示回應內容」點擊 → `delivery-excerpt` 出現、「收合」→ 消失；deliveries `isError` → `role="alert"`＋「重試」→ `refetch` spy
- [x] GREEN：桌機 `<Table data-testid="deliveries-table" className="hidden md:block">`（欄：時間／事件／狀態／嘗試／下次重試／操作）＋行動卡（`md:hidden`、`data-testid="deliveries-cards"`）；`DeliveryStatus`（既有 icon＋文字）／attempt／nextRetry 共用小元件；excerpt `useState` toggle；deliveries error 分支
- [x] 表格與卡片渲染同一份資料（單一 map，兩處輸出）

**Commands:**
- `cd apps/web && pnpm test -- components/settings/webhook-panel`

### Task 2.3: 狀態篩選＋載入更多＋篩選空態

**Files:**
- Modify: `apps/web/components/settings/webhook-panel.tsx`、`webhook-panel.test.tsx`

**TODO:**
- [x] RED：篩選 chips（全部／成功／失敗／待重試）——點「成功」→ `listWebhookDeliveries` 收到 `status:"success"`；「載入更多」在首頁 = PAGE_SIZE 時可見、點擊 → 收到 `offset:20`（`mockResolvedValueOnce` 兩頁）；有篩選 0 筆 →「沒有符合的 delivery」＋「清除篩選」點擊回全部；無篩選 0 筆 → 既有空態文案
- [x] GREEN：`useInfiniteQuery`（`queryKey: ["webhooks", id, "deliveries", { status }]`、PAGE_SIZE=20、`getNextPageParam` 末頁滿頁判斷）；filter state `"all"|"success"|"failed"|"pending"`；chips 用既有 `Button` variant 切換（`aria-pressed`，≥44px）
- [x] 既有測試 mock（`listWebhookDeliveries` 回陣列）改為 `mockResolvedValue([...])` 相容；分頁案例用序列 mock

**Commands:**
- 同 T2.2

### Task 2.4: 概覽統計＋webhooks 列表錯誤態＋i18n 收尾

**Files:**
- Modify: `apps/web/components/settings/webhook-panel.tsx`、`apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`、`webhook-panel.test.tsx`

**TODO:**
- [x] RED：stats 渲染——「成功率 50%（成功 1／總 2）」「最近成功：{date}」；`total=0` → 統計列不顯示；stats `isError` → 統計列不顯示（列表正常）；webhooks list `isError` → compact 錯誤＋「重試」；重試 delivery 後 stats 被 invalidate（spy）＋列表更新（既有斷言保留）
- [x] GREEN：`useQuery(["webhooks", id, "deliveries", "stats"])`；`onSuccess`／invalidate 掛載；成功率 `Math.round`；i18n 逐鍵插入兩檔：
  - `settings.webhooks.filter.all/success/failed/pending`（全部／成功／失敗／待重試）
  - `filterEmptyTitle`（沒有符合的 delivery）／`clearFilter`（清除篩選）
  - `loadMore`（載入更多）／`loadingMore`（載入中…）
  - `excerptShow`（顯示回應內容）／`excerptHide`（收合回應內容）
  - `stats.successRate`（成功率 {pct}%（成功 {succeeded}／總 {total}））／`stats.lastSuccess`（最近成功：{date}）
  - `table.time/event/status/attempt/nextRetry/actions`（時間／事件／狀態／嘗試／下次重試／操作）
  - `loadFailed`（無法載入 delivery 紀錄。）／`retryLoad`（重試）；`listLoadFailed`（無法載入 webhook 清單。）
- [x] locale 鍵集比對零差異（python flat-set 檢查）

**Commands:**
- `cd apps/web && pnpm test -- components/settings/webhook-panel && pnpm typecheck`

---

## Phase 3: e2e、文件收尾

### Task 3.1: e2e `webhooks.spec.ts`

**Files:**
- Create: `apps/web/tests/webhooks.spec.ts`

**TODO:**
- [x] ① 桌面主流程：register → login UI → API 建 webhook（`url: http://127.0.0.1:9/hook`、`events: ["item.created"]`）→ API 建物品（同步 dispatch 失敗）→ `/settings/webhooks`：deliveries 列「第 1 次」＋網路錯誤狀態＋「已排程重試」；概覽「成功率 0%（成功 0／總 1）」；篩選「成功」→「沒有符合的 delivery」＋清除篩選；「顯示回應內容」→ excerpt 出現；「立即重試」→「第 2 次」出現＋概覽總數 2
- [x] ② 行動 390＋空態：新用戶 `/settings/webhooks` →「尚無 webhook」空態；建 webhook＋觸發失敗列後：390 寬 `deliveries-table` 隱藏、`deliveries-cards` 可見（Playwright `toBeHidden`／`toBeVisible`）
- [x] 全套 e2e 回歸（57＋新增；`--workers=2`）

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx && cd apps/web && pnpm exec playwright test --workers=2`

### Task 3.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.28]`）、`docs/v2-roadmap.md`（Phase 28 ✅＋測試規模）、本計畫（勾選＋Final Verification）

**TODO:**
- [x] CHANGELOG alpha.28：deliveries 篩選（`status`／`event`）／分頁（`offset`）／stats 端點（成功率、最近成功時間）／Web 桌機表格＋行動卡片／狀態篩選＋載入更多／excerpt 展開／概覽／查詢錯誤態
- [x] v2-roadmap：Phase 28 row ✅＋測試規模更新
- [x] 本計畫：全任務勾選＋Final Verification（實測數字、環境註記）
- [x] 收尾視覺走查：桌機（表格＋篩選＋展開＋概覽）／行動 390（卡片）／空態／錯誤態截圖

**Commands:**
- `cd apps/web && pnpm exec playwright test --workers=2`

---

## API 契約（實作權威）

**`GET /api/webhooks/{id}/deliveries`**（既有路徑擴充）：
- Query：`limit`（default 50，1..500，**維持**）、`offset`（default 0，≥0，**新增**）、`status`（`success|failed|pending`，**新增**）、`event`（≤60 字元，**新增**）
- 回應：`[WebhookDeliveryRead]`（**不變**；`created_at desc`）
- 語意：`success`＝2xx；`failed`＝`status_code IS NULL OR NOT 2xx`；`pending`＝`next_retry_at IS NOT NULL`

**`GET /api/webhooks/{id}/deliveries/stats`**（**新增**）→ `{total: int, succeeded: int, failed: int, pending: int, last_success_at: datetime|null}`
- counts＝該 webhook 的**嘗試列**數（重試各為新列）；`last_success_at`＝2xx 列最大 `created_at`；無資料 → 全 0＋null
- 錯誤：跨 owner／不存在 → 404（`_ensure_owned`）

**Web client**：`listWebhookDeliveries(id, { limit?, offset?, status?, event? }, token)`；`getWebhookDeliveryStats(id, token)`

### §5.4 狀態表（本 phase 介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| deliveries 列表（28） | 列骨架（表格／卡片共用） | 無篩選 → 既有空態；**有篩選 → 「沒有符合的 delivery」＋清除篩選** | **卡內 compact 錯誤＋重試** | 表格（桌機）／卡片（行動）：時間、事件、狀態（icon＋文字）、嘗試、下次重試、excerpt 展開、失敗列可重試 | 「載入更多」按鈕 loading（`loadingMore`） |
| 概覽統計（28） | 小骨架 | `total = 0` → 不顯示統計列 | 靜默隱藏（列表錯誤態獨立） | 成功率 X%（成功 A／總 B）＋最近成功時間 | 重試後即時更新（invalidate） |
| webhooks 列表（28 補） | 既有 loading 文案 | 既有空態 | **新增 compact 錯誤＋重試** | 既有卡片 | — |

### 驗收對照（roadmap §六 Phase 28）

| 驗收項 | Task |
|---|---|
| deliveries 分頁／篩選參數（status、event） | T1.1＋T2.1＋T2.3 |
| 統計端點（成功率、最近成功時間） | T1.2＋T2.1＋T2.4 |
| deliveries 表：時間／事件／狀態碼／attempt／next_retry_at | T2.2 |
| 狀態篩選（成功／失敗／待重試） | T2.3 |
| response excerpt 展開 | T2.2 |
| 手動「重試」（呼叫既有端點） | 既有＋T2.3 回歸（invalidate 擴充） |
| 概覽：成功率、最近成功時間 | T2.4 |
| UI 測試（列表、篩選、重試觸發）／空狀態／行動版佈局 | T2.2–T2.4＋T3.1 |

---

## Final Verification（收尾時填實測）

- [x] API：`uv run --extra test pytest -q` → 750 passed
- [x] Web：`pnpm test` → 430 passed（87 檔）＋`typecheck` 0 error
- [x] api-types 重生成零 diff
- [x] e2e：59 passed（含 `webhooks.spec.ts` 2 情境；`--workers=2`；於全部程式碼變更後重跑）
- [x] 視覺走查：桌機（表格／excerpt 展開／篩選空態／列表錯誤態）＋行動 390（卡片）＋空態；6 張截圖以一次性 Playwright script 對 `ims-v2` stack 產出並人工檢視

### 收尾環境註記（2026-10-17 起填）

- worktree 首次使用需先 `pnpm install`（node_modules 不存在；api-types `gen:types`／vitest／e2e 皆依賴）
- `packages/api-types/src/` 雖列於 `.gitignore`，其中 `index.ts` 為 tracked 生成檔 → 與 `openapi.json` 一併提交（比照 Phase 27 `a1341e6`）
- e2e／視覺走查跑在 worktree 自身 `ims-v2` stack（`ENABLE_DEV_ROUTES=1`、nginx port 80）；本 phase 無 migration（alembic 維持 0021）
- macOS `TMPDIR` 實際為 `/var/folders/cl/nt00k_qn5wb85gzhd5dsm4kh0000gn/T/`（env 建議的 `.../T/opencode` 路徑不存在，`mkdir` EACCES）；截圖改用 `mktemp -d`
