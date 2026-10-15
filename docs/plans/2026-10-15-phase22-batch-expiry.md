# Phase 22 — 批次到期管理 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 22（L236–293）。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**。
> 完成任一 task 即 commit（Conventional Commits，`feat(api): …`／`feat(web): …`）。

**Goal：** 物品可開啟「追蹤批次」模式；每批有數量與到期日；支援進貨、消耗（FEFO）；儀表板顯示即將到期／已過期，並提供到期模式視圖。

**Architecture：** 維持 Next.js 15 + FastAPI 現況，新增 `item_batches` 表與 `batches_service`。**數量唯一入口**：`track_batches=true` 的物品，一切數量變動（進貨／消耗／盤點調整／模式切換）只經 `batches_service`，恆等式 `items.quantity == Σ 未耗盡批次.quantity` 由 service 層維護（roadmap 決策 1）。正確性以「**原子 UPDATE＋rowcount 檢查**」承擔——已實測 SQLAlchemy 2.0.35 對 SQLite 會**省略** `FOR UPDATE`（測試環境 no-op），PG 生產環境再以 `with_for_update()` 鎖 item 列加保險。「今天」唯一定義＝`app/clock.today_taipei()`（Asia/Taipei）。

**Tech Stack：** FastAPI、SQLAlchemy async、Alembic（migration `0016`）、pytest（SQLite in-memory：`tests/conftest.py`）、React Query、next-intl、shadcn/ui、Vitest、Playwright。

**關鍵既有資產（重用，勿重造）：**
- `QuantityLog.reason`（`apps/api/app/models/item_history.py`）＋ `item_history_service.log_quantity_change(…, reason=…)`（自帶 commit）
- nested route 慣例：`APIRouter(prefix="/api/items/{item_id}/loans", tags=["loans"])`（`apps/api/app/routes/loans.py`）
- repository 慣例：`items_repository.get_owned(session, owner_id, item_id)`
- 儀表板卡片慣例：`apps/web/components/dashboard/low-stock-card.tsx`（含 test）
- Web 資料層慣例：`lib/api/client.ts`＋`lib/api/items.ts`＋`lib/hooks/use-items.ts`（React Query keys）
- 指令：API `uv run --extra test pytest`；Web `pnpm -F @ims/web test`；型別 `pnpm -F @ims/api-types gen:types`

**執行前置（一次性）：**
- `git worktree add .claude/worktrees/phase22-batches -b claude/phase22-batches`
- 確認部署映像（python:3.13-slim 等）有 zoneinfo 資料；若無 → `cd apps/api && uv add tzdata`
- 未提交文件（roadmap／DESIGN.md 等）建議先由使用者 commit 或於首個 commit 一併帶入

**Execution Order**

1. API 基礎：migration＋model＋clock helper（無依賴）
2. `batches_service` 單一入口（最關鍵，後續全依賴）
3. schemas／routes／stats-expiry
4. 既有流程整合（`update_item` 守門、盤點、CSV）
5. api-types regen
6. Web：client/hooks → 詳情批次區塊 → 表單模式 → 列表＋到期視圖 → 儀表板卡
7. i18n／深色／a11y → Final Verification

---

## Phase 1: API 批次核心

### Task 1.1: Migration `0016`＋`ItemBatch` model＋`items.track_batches`

**Files:**
- Create: `apps/api/app/models/item_batch.py`
- Modify: `apps/api/app/models/item.py`（加 `track_batches`）
- Modify: `apps/api/app/models/__init__.py`（註冊）
- Create: `apps/api/alembic/versions/0016_item_batches.py`
- Test: `apps/api/tests/test_item_batch_model.py`

**TODO:**
- [x] `ItemBatch`：`id`(UUID pk)、`item_id`(FK `items.id` ondelete=CASCADE)、`quantity`(int, nullable=False)、`expiry_date`(Date, nullable)、`received_at`(Date, nullable)、`note`(Text, nullable)、`is_depleted`(bool, default false, server_default false)、`created_at`/`updated_at`（比照 `item.py` 的 `_utcnow` 慣例）
- [x] 索引：`item_id`、複合 `(item_id, is_depleted)`、`expiry_date`（列表聚合、統計與 job 掃描用）
- [x] `items.track_batches`：bool、default false、server_default `false`
- [x] migration 0016：`revision="0016"`、`down_revision="0015"`；upgrade/downgrade 對稱（比照 `0015_webhook_retry.py` 風格）
- [x] smoke test：建 item＋batch、刪 item 時 cascade 清批次、`is_depleted` 預設 false

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_item_batch_model.py`
- `cd apps/api && uv run alembic upgrade head`

### Task 1.2: 台北「今天」helper

**Files:**
- Create: `apps/api/app/clock.py`
- Test: `apps/api/tests/test_clock.py`

**TODO:**
- [x] `today_taipei(now: datetime | None = None) -> date`：`datetime.now(UTC)` 轉 `ZoneInfo("Asia/Taipei")` 取 date；`now` 參數供測試注入
- [x] `days_left(expiry_date: date, *, today: date | None = None) -> int`
- [x] 常數 `EXPIRING_SOON_DAYS = 7`（列表篩選與 badge 共用；`status` 判定：`days_left < 0` → `expired`；`0 ≤ days_left ≤ 7` → `expiring`；其餘 `ok`）
- [x] 邊界測試：`2026-10-15T15:59:59Z` → 台北 `2026-10-15`（23:59:59）；`2026-10-15T16:00:00Z` → `2026-10-16`（00:00）；`days_left` 於 23:59/00:00 前後正確
- [x] 註記：本 helper 是全站「今天」唯一來源（含 Phase 24 門檻判定），其他模組不得再寫 `date.today()`

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_clock.py`

### Task 1.3: `batches_repository`＋`batches_service` 單一入口

**Files:**
- Create: `apps/api/app/repositories/batches_repository.py`
- Create: `apps/api/app/services/batches_service.py`
- Modify: `apps/api/app/repositories/items_repository.py`（`get_owned(..., for_update: bool = False)`）
- Test: `apps/api/tests/test_batches_service.py`

**TODO:**
- [x] service 模組 docstring 放 roadmap 的「數量 invariant 流」ASCII 圖（inline 圖落點之一）
- [x] 每個會動數量的 public 函式開頭：`select(Item) … .with_for_update()`（PG 鎖列；SQLite no-op 由測試證明不影響）
- [x] `create_batch(session, owner_id, item_id, body)`：首建自動 `track_batches=true`（決策 3）；`body.quantity` 省略時＝`item.quantity`（若 item.quantity=0 則必填）；`received_at` 省略時＝`today_taipei()`；寫入後 recalc＋log（`reason=f"batch:add:{batch_id}"`）
- [x] `update_batch`（數量/到期日/備註）：絕對值設定；`quantity ≥ 1`（0 走 consume/delete）；recalc＋log（`batch:update`）
- [x] `delete_batch`：硬刪（校正誤輸入；已耗盡歷史另由 `is_depleted` 保留）；recalc＋log（`batch:delete`）
- [x] `consume_from_batch(batch_id, qty)`：**原子條件 UPDATE** `SET quantity = quantity - :q, is_depleted = (quantity - :q <= 0) WHERE id=:id AND item_id=:item AND quantity >= :q AND is_depleted=false` → `rowcount == 0` → 409；recalc＋log（`batch:consume:{batch_id}`）
- [x] `consume_fefo(qty)`：讀取未耗盡批次排序（`CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END, expiry_date, received_at, created_at`；避免方言 NULLS LAST 差異）；Σ < qty → 409「庫存不足」且零變更；逐批原子扣除；recalc＋log（`batch:fefo`）
- [x] `disable_tracking(item_id)`：**合併**——刪除全部批次、`items.quantity` 維持（決策 4）、`track_batches=false`；不存在「關閉但有批次」狀態
- [x] `adjust_for_stocktake(session, owner_id, item, stocktake_id, actual_qty)`：`delta > 0` → 建批次（note=`stocktake:<id>`）；`delta < 0` → FEFO 消耗（因 invariant，Σ ≥ |delta| 恆成立）；log（`stocktake:<id>`）
- [x] recalc 以**單一 SQL**：`UPDATE items SET quantity = (SELECT COALESCE(SUM(quantity),0) FROM item_batches WHERE item_id=:id AND is_depleted=false) WHERE id=:id`；之後 `session.refresh(item)` 再回傳；commit 次序＝先批次變更＋recalc（單一 commit），後 `log_quantity_change`（沿用「log 自帶 commit」既有慣例）
- [x] 測試 helper `assert_invariant(session, item_id)`：`item.quantity == Σ 未耗盡`
- [x] 測試：FEFO 跨批次／同到期日 tie-break／剛好歸零（`is_depleted=true` 且不再計入）／超額 409 且零變更／**stale-read（取舊批次列後他人先扣，條件 UPDATE 仍安全、不得負數）**／首建沿用 `item.quantity`／disable 後批次清空且 quantity 不變／stocktake 正負差／`QuantityLog.reason` 逐值斷言

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_batches_service.py`

### Task 1.4: Schemas

**Files:**
- Create: `apps/api/app/schemas/batch.py`
- Modify: `apps/api/app/schemas/item.py`（`ItemRead` 加 `track_batches: bool`、`soonest_expiry: date | None`）
- Modify: `apps/api/app/schemas/stats.py`（`ExpiryItem`、`ExpiryStats`）
- Test: `apps/api/tests/test_batch_schemas.py`

**TODO:**
- [x] `BatchCreate`：`quantity: int | None`(≥1)、`expiry_date: date | None`、`received_at: date | None`、`note: str | None`
- [x] `BatchUpdate`：`quantity: int | None`(≥1)／`expiry_date`／`note` 皆 optional（exclude_unset 語義）
- [x] `BatchConsume`：`quantity: int`(≥1)
- [x] `BatchRead`：全欄位＋derived `days_left: int | None`、`status: Literal["ok","expiring","expired"]`（無到期日 → `days_left=None`、`status="ok"`）
- [x] `ExpiryItem`：`id`、`name`、`quantity`、`soonest_expiry`、`days_left`、`status`；`ExpiryStats`：`expired_count`、`expiring_count`、`items: list[ExpiryItem]`

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_batch_schemas.py`

### Task 1.5: Routes（nested 風格）＋掛載

**Files:**
- Create: `apps/api/app/routes/batches.py`
- Modify: `apps/api/app/main.py`（include router）
- Test: `apps/api/tests/test_batches_routes.py`

**TODO:**
- [x] `APIRouter(prefix="/api/items/{item_id}/batches", tags=["batches"])`，全部 `Depends(get_current_user)`＋`get_db`（比照 `loans.py`）
- [x] `GET ""` 列表：回全部批次（含已耗盡，`is_depleted` 旗標由前端分流「歷史」折疊）；排序：未耗盡在前→到期日 asc（null 最後）→received_at
- [x] `POST ""` 進貨（201）；`PATCH "/{batch_id}"`；`DELETE "/{batch_id}"`（204）
- [x] `POST "/{batch_id}/consume"` `{quantity}`（批次內耗用）；FEFO 便捷端點 `POST /api/items/{item_id}/consume`（roadmap L253）——**不在 batches prefix 下**，於同檔另建 `item_consume_router = APIRouter(prefix="/api/items/{item_id}", tags=["batches"])`，`main.py` 兩個 router 一起掛
- [x] `POST "/disable"`（合併並關閉，回 `ItemRead`）——決策 4 配套端點，roadmap L250–253 未列，於此定案
- [x] route 測試：外部 owner 404、超額 consume 409、`quantity=0` 422、disable 後 `GET ""` 回空、FEFO 與單批消耗路徑皆通

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_batches_routes.py`

### Task 1.6: Item 整合——PATCH 守門＋列表聚合＋到期篩選（含 query count 斷言）

**Files:**
- Modify: `apps/api/app/services/items_service.py`
- Modify: `apps/api/app/repositories/items_repository.py`（列表查詢加聚合 subquery）
- Modify: `apps/api/app/schemas/item.py`（`soonest_expiry`，Task 1.4 已加欄位）
- Test: `apps/api/tests/test_items_service.py`、`apps/api/tests/test_items_routes.py`、新增 `apps/api/tests/test_items_expiry_query.py`

**TODO:**
- [x] `update_item`：`item.track_batches` 且 fields 含 `quantity` → 409（detail 明示改用批次端點）；`track_batches` 不由 `ItemUpdate` 直改（僅批次端點管理）
- [x] 列表聚合（**單一查詢**）：LEFT JOIN `(SELECT item_id, MIN(expiry_date) AS soonest FROM item_batches WHERE is_depleted=false GROUP BY item_id)`，`soonest_expiry` 回傳；不得 per-item 查詢
- [x] `GET /api/items?expiry=expired|expiring_soon`：以同一聚合 subquery 條件過濾（`expired`: soonest < today；`expiring_soon`: today ≤ soonest ≤ today+7）；`sort=expiry_asc`（soonest asc、null 最後）供到期模式視圖
- [x] **query count 斷言**（roadmap 驗收 3）：以 `event.listens_for(engine.sync_engine, "before_cursor_execute")` 計 SELECT 數；種 3 筆 vs 30 筆 tracked 物品，`GET /api/items` 的 SELECT 數相同
- [x] 回歸測試：未開啟追蹤的物品行為不變（PATCH quantity 照舊、列表欄位增補不破壞既有 schema 消費者）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_items_service.py tests/test_items_routes.py tests/test_items_expiry_query.py`

### Task 1.7: `GET /api/stats/expiry`

**Files:**
- Modify: `apps/api/app/routes/stats.py`
- Modify: `apps/api/app/services/stats_service.py`／`apps/api/app/repositories/stats_repository.py`
- Test: `apps/api/tests/test_stats_routes.py`

**TODO:**
- [x] 參數 `days: int = 30`（1–365）；回 `ExpiryStats`：`expired_count`、`expiring_count`（≤days）、`items`（soonest 最早前 10 筆，聚合單查詢；沿用既有 visibility/owner 範圍慣例，比照 `low_stock`）
- [x] 測試：空資料、僅過期、days 邊界（1／365／0 → 422）、排序正確

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_stats_routes.py`

### Task 1.8: 盤點整合（tracked 物品走批次調整）

**Files:**
- Modify: `apps/api/app/services/stocktake_service.py`
- Test: `apps/api/tests/test_stocktake.py`（追加案例）

**TODO:**
- [x] complete 流程逐列：`row.expected != actual` 時——`item.track_batches` → `batches_service.adjust_for_stocktake(...)`；否則維持現行直改路徑
- [x] 測試：正差建批次（note=`stocktake:<id>`）、負差 FEFO、完成後 invariant 成立、`QuantityLog.reason` 含 `stocktake:`、untracked 案例零回歸

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_stocktake.py`

### Task 1.9: CSV（invariant 保證＋stretch 匯出欄）

**Files:**
- Modify: `apps/api/app/services/csv_service.py`（視需要）
- Test: `apps/api/tests/test_csv_*.py`（新增或追加）

**TODO:**
- [x] 確認／補上：匯入建立的新物品為 `track_batches=false`；**不得**直接改寫既有 tracked 物品的 `quantity`（若現況有 match-update 行為則改為略過＋回報列錯誤）
- [x] invariant 測試（roadmap 驗收 2）：匯入含 tracked 物品的資料集後，全部 tracked 物品恆等式成立
- [x] stretch：`GET /api/items/export.csv` 對「恰一筆未耗盡批次」的物品加 `expiry_date` 欄（完整批次匯出留待後續）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q`（CSV 測試檔名以 `ls apps/api/tests | grep csv` 為準）

### Task 1.10: api-types 重新產生

**Files:**
- Modify: `packages/api-types/openapi.json`、`packages/api-types/src/index.ts`

**TODO:**
- [x] `pnpm -F @ims/api-types gen:types`（`generate.mjs`）；確認 diff 僅含本 phase 端點與 schema
- [x] `pnpm -F @ims/web typecheck` 通過

**Commands:**
- `pnpm -F @ims/api-types gen:types && pnpm -F @ims/web typecheck`

---

## Phase 2: Web

### Task 2.1: API client＋React Query hooks

**Files:**
- Create: `apps/web/lib/api/batches.ts`（＋`batches.test.ts`）
- Modify: `apps/web/lib/api/items.ts`（`expiry`／`sort` 參數、`ItemRead` 新欄位）
- Create: `apps/web/lib/hooks/use-batches.ts`
- Modify: `apps/web/lib/hooks/use-stats.ts`（`useExpiryStats`）
- Test: `apps/web/lib/hooks/use-batches.test.tsx`（或沿用既有 hook 測試風格）

**TODO:**
- [x] client：list／create／update／delete／consume（單批）／consumeFefo／disable
- [x] query key：`["batches", itemId]`；mutation 成功後 invalidate `["batches"]`、`["items"]`、`["item", itemId]`、`["stats"]`
- [x] 測試：路徑／method／body 序列化／token 傳遞

**Commands:**
- `pnpm -F @ims/web test -- lib/api/batches.test.ts lib/hooks/use-batches.test.tsx`

### Task 2.2: 物品詳情「批次」區塊

**Files:**
- Create: `apps/web/components/items/batch-section.tsx`（＋`.test.tsx`）
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`（嵌入區塊；`track_batches` 才顯示）
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`

**TODO:**
- [x] 列表列：到期日 badge（已過期紅／≤7 天橙／其餘中性，用 §5.6 tokens）＋剩餘天數＋數量；行內「−1」**樂觀更新**（`onMutate` 改 cache、`onError` 回滾＋toast）
- [x] 「進貨／調整」以既有 sheet/dialog 元件（沿用 `item-form` 現用元件）開表單：數量、到期日、備註
- [x] 「已耗盡」折疊區：預設收起、不混入主列表（§5.4）
- [x] 「關閉追蹤」：確認對話框明示「批次將合併為單一數量，到期日資訊將刪除」→ `disable` 端點
- [x] 狀態：loading skeleton／空狀態（引導「進貨建立第一批」）／錯誤 toast
- [x] 測試：badge 顏色對應、−1 樂觀與回滾、折疊預設關、關閉對話框文案、清零後該列移入歷史

**Commands:**
- `pnpm -F @ims/web test -- components/items/batch-section.test.tsx`

### Task 2.3: 物品表單模式切換

**Files:**
- Modify: `apps/web/components/items/item-form.tsx`（＋`.test.tsx`）
- Modify: `apps/web/messages/{zh-TW,en}.json`

**TODO:**
- [x] 「追蹤批次」switch；開啟時：數量欄位隱藏／唯讀＋引導文案「建立第一批時，現有數量會併入一筆無到期日批次」（roadmap L258）
- [x] 新建：送出物品後如開啟追蹤 → `POST batches`（沿用既有數量）；編輯既有物品：開啟當下即 `POST batches`
- [x] 關閉追蹤於表單的等價入口（或導向詳情頁對話框，避免雙路徑歧義）
- [x] 測試：切換顯示邏輯、送出後兩段呼叫次序、失敗回滾（批次建立失敗 → 提示且不靜默）

**Commands:**
- `pnpm -F @ims/web test -- components/items/item-form.test.tsx`

### Task 2.4: 物品列表 badge／篩選＋到期模式視圖

**Files:**
- Modify: `apps/web/components/items/items-table.tsx`（＋`.test.tsx`）
- Modify: `apps/web/app/(app)/items/items-list-client.tsx`（＋`.test.tsx`）
- Modify: `apps/web/messages/{zh-TW,en}.json`

**TODO:**
- [x] 批次物品列：總數＋**最急到期 badge（僅一枚）**（§5.4）；未追蹤物品列零變化
- [x] 篩選 chips：到期＝全部／已過期／7 天內（`expiry=` 參數）
- [x] 「到期模式」視圖：`sort=expiry_asc`、行內 −1（樂觀）、列展開看批次、清零回饋（toast＋`aria-live`，§5.5）；deep link 落點（儀表板卡與 Phase 24 通知摘要導向此）
- [x] 測試：badge 僅一枚且取最急、篩選參數、到期模式排序與 −1、清零回饋出現

**Commands:**
- `pnpm -F @ims/web test -- components/items/items-table.test.tsx 'app/(app)/items/items-list-client.test.tsx'`

### Task 2.5: 儀表板到期行動卡

**Files:**
- Create: `apps/web/components/dashboard/expiry-card.tsx`（＋`.test.tsx`，比照 `low-stock-card`）
- Modify: `apps/web/app/(app)/dashboard/page.tsx`
- Modify: `apps/web/messages/{zh-TW,en}.json`

**TODO:**
- [x] 卡片：數字（已過期／N 天內）＋下一步 deep link（`/items?expiry=expired`／`expiring_soon`）＋狀態註記（§5.1）
- [x] 排序：已過期 ＞ 7 天內到期 ＞ 低庫存（行動卡群組）
- [x] 空狀態：無到期資料 → 卡片不渲染或顯示「無即將到期」（依 §5.1 既有空狀態慣例）
- [x] 測試：數字映射、deep link、排序位置、載入中 skeleton

**Commands:**
- `pnpm -F @ims/web test -- components/dashboard/expiry-card.test.tsx`

### Task 2.6: i18n／深色／a11y／§5.4 狀態表

**Files:**
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`（收斂新增 key，命名比照 `items.*`／`dashboard.*`）
- Modify: `docs/plans/2026-10-15-next-iteration-roadmap.md`（§5.4 補 P22 介面狀態列）

**TODO:**
- [ ] zh-TW＋en 全字串；無 hard-coded 文案
- [ ] 深色模式檢查（badge 紅／橙在深色下對比達標，用 §5.6 tokens）
- [ ] a11y：鍵盤可達「−1」「進貨」、`aria-live` 清零回饋、badge 有文字標籤非僅顏色
- [ ] §5.4 狀態表補上本 phase 介面列（loading／empty／error／optimistic／成功回饋）

**Commands:**
- `pnpm -F @ims/web test && pnpm -F @ims/web typecheck`

---

## 驗收對照（roadmap §六 → 本計畫）

| roadmap 驗收大綱 | 對應 task |
|---|---|
| FEFO 消耗正確性（跨批次、剛好歸零、超額拒絕） | 1.3 |
| invariant 測試（批次操作、盤點、CSV 匯入後） | 1.3、1.8、1.9 |
| 列表聚合查詢數不隨列數成長（query count 斷言） | 1.6 |
| 到期模式視圖（排序、行內 −1、樂觀更新、清零回饋） | 2.4 |
| 未開啟追蹤模式的物品行為零回歸 | 1.6、1.8、2.3 |
| 併發雙 consume → invariant 成立、無 lost update | 1.3（原子 UPDATE＋stale-read 測試） |
| 台北午夜邊界（23:59／00:00） | 1.2 |
| i18n 全字串、深色模式 | 2.6 |

## Final Verification

- [ ] `cd apps/api && uv run --extra test pytest -q`（全綠；454 既有測試零回歸）
- [ ] `pnpm -F @ims/web test`
- [ ] `pnpm -F @ims/web typecheck`
- [ ] `pnpm -F @ims/web test:e2e`（既有 11 spec 零回歸；stretch：新增 `items-batches.spec.ts`）
- [ ] `git diff --check`
- [ ] 手動流程（桌面 1280＋行動 390）：
  - `/items/[id]`：開啟追蹤、進貨、−1 連點（併發）、調整、耗盡進歷史、關閉追蹤
  - `/items/new`：模式切換引導文案、第一批建立
  - `/items`：badge、chip 篩選、到期模式視圖、清零回饋
  - `/dashboard`：到期卡數字、deep link 落點
- [ ] `CHANGELOG.md` 增 `2.0.0-alpha.22` 條目；`docs/v2-roadmap.md` Phase 表更新（§十 第 4 條）
