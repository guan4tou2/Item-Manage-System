# Phase 29 — 備份還原 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 29＋§5.2 設定 IA（「整合與資料 ＞ 備份」）、§5.4 狀態契約（備份匯入列＋dry-run 摘要補充規格）、§5.6 狀態不得僅以色彩表達、§5.7 響應式。
> 本 phase **無 migration、無 schema 變更**（純讀寫端功能＋匯出格式擴充）；既有 export 呼叫端與 API 零破壞（僅格式版本 3→4 加欄位）。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**；完成即 commit（Conventional Commits，繁中 body）。

**Goal：** 讓帳號資料可**從 JSON 備份還原**：API 新增 `POST /api/backup/import`（multipart、`dry_run`、`create_only`／`replace` 兩模式、per-entity 計數與錯誤列舉、批次對帳）＋擴充 `GET /api/backup/export` 至「當期 schema 全量」；Web 設定頁新增「整合與資料 ＞ **備份**」頁——匯出（JSON 下載，現僅 API 無 UI）＋匯入（選檔 → dry-run「現有 → 匯入後」摘要 → 確認（replace 需輸入 `REPLACE`＋先匯出提示）→ 結果報告三態）。

**Architecture：** 匯出端 `backup_service.export_full` 擴充欄位與實體（format_version 4）；匯入端**新模組** `backup_import_service.py` 採「**plan（純讀）→ apply（寫入）**」兩段式：plan 做解析／驗證／名稱匹配／id-map 建構／對帳（dry-run 即零寫入）；apply 依 plan 寫入（UUID 於 plan 階段先配發，apply 決定性）。`replace` 以**單一交易**依賴序清空後匯入，任何列級錯誤在 plan 階段即中止（零寫入），執行期例外全數 rollback。Web 端新頁 `/settings/backup`＋`backup-panel.tsx`（匯出卡＋匯入卡），client 走 `lib/api/backup.ts`（FormData 上傳＋Blob 下載）。**不新增依賴、不動 model／migration（alembic 維持 0021）。**

**Tech Stack：** FastAPI（`UploadFile`＋`Form`＋`Literal`、pydantic response_model 進 openapi）、SQLAlchemy async（bulk `delete()` 依賴序清空，不依賴 DB cascade）、pytest（SQLite in-memory）、React Query（成功匯入後 `invalidateQueries` 全站）、next-intl、shadcn/ui（既有 `Card`／`Button`／`Table`／`Alert`／`Skeleton`／`RadioGroup`／`Input`）、Vitest、Playwright（`setInputFiles` buffer）。

**關鍵既有資產（重用，勿重造）：**
- 後端：`apps/api/app/services/backup_service.py`（`export_full`、`_serialize` UUID/Decimal→字串、`_row_to_dict`）、`apps/api/app/routes/backup.py`（`GET /api/backup/export`＋`Content-Disposition`）
- 模型：`item.py`（`barcode`/`track_batches`/`cost`/`image_id`）、`item_batch.py`、`loan.py`、`item_history.py`（`QuantityLog`／`ItemVersion`）、`stocktake.py`、`webhook.py`、`notification_preference.py`、`customization.py`、`group.py`、`list.py`
- 偏好：`apps/api/app/schemas/preferences.py`（`currency_from_raw`，六幣別白名單）、`users.preferences` JSON 欄
- 稽核：`apps/api/app/services/audit_service.py`（`log()` 會自行 `commit()` → **僅可在匯入交易完成後呼叫**）
- 上傳範式：`apps/api/app/routes/items_bulk.py`（`UploadFile`）、`apps/api/tests/conftest.py`（`client`＋`db_session` fixture、SQLite in-memory、**FK 未強制 → 清空不得依賴 cascade**）
- Web：`components/settings/csv-panel.tsx`（選檔／下載／摘要 UI 範式）、`lib/api/items-bulk.ts`（Blob 下載＋FormData 上傳）、`lib/api/client.ts`（`apiFetch`／`ApiError`／`getApiErrorDetail`）、`settings-nav.ts`、`settings-page-shell.tsx`、`app/(app)/settings/data/page.tsx`
- nginx：`nginx/default.conf` `client_max_body_size 32m`（API 上限取 20 MiB，低於 nginx）

**盤點定案（2026-10-17，實作前一覽）：**
1. **Web 現況落差**：設定頁**完全沒有備份 UI**、`lib/api` 無 backup client（roadmap「匯出（既有）」實指 Phase 9 的 API dump）→ 本 phase Web 端「匯出＋匯入」皆新建；IA 依 §5.2 於「整合與資料」群組新增 `backup` 頁（`/settings/backup`，該群組達 6 頁硬上限，登錄：後續欲加頁須先重新分類）。
2. **還原範圍（當期 schema 全量盤點定案）**：
   - **可還原**：`items`（+`barcode`/`track_batches`）、`categories`、`locations`（樹）、`tags`、`warehouses`、`item_types`、`custom_fields`、`item_templates`、`item_custom_values`、`item_batches`、`loans`、`quantity_logs`、`item_versions`、`lists`（+entries）、`stocktakes`（+items）、`webhooks`（**一律停用**）、`notification_preferences`、`preferences.currency`、`groups_owned`（**僅群組殼，members 不還原**）
   - **不還原（登錄理由）**：`audit_logs`／`api_tokens`（roadmap 明文，安全）；`webhook_deliveries`（暫態投遞紀錄）；`notifications`（站內暫態）；`images`（二進位檔在磁碟 → `items.image_id` 還原為 null）；`barcode_lookups`（TTL 快取）；`expiry_alerts`（dedupe 帳本，批次重建後自然重算）；`item_transfers`（跨帳號流程狀態）；LINE／Telegram／WebPush 綁定（外部憑證，安全）；`job_run`（執行期）；`reports`（Phase 31 未實作，不適用）
   - `items.is_deleted=true` 既有 export 已排除 → 維持（軟刪除物不入備份，登錄）
3. **format_version 3 → 4**（新增可選欄位/實體＝+1）；相容矩陣：v1（初始 dump）／v2（locations 樹欄位，Phase 26）／v3（cost／budget／price，Phase 27）皆**可匯入**（缺鍵視為空、缺欄視為 null）；`>4` → 400 明確拒絕「備份檔版本高於系統支援」。
4. **兩段式 plan／apply**：dry-run＝只跑 plan（**零寫入**，含 replace 的「將刪除 N」以 COUNT 計算）；create_only 列級錯誤**容忍**（有效列照匯入 → partial）；replace **全有全無**（plan 有錯即中止、零寫入；執行期例外 rollback → 原資料完整）。
5. **create_only 名稱策略（鎖定）**：`categories`／`locations` 以「parent 鏈路徑＋name」、`tags`／`warehouses` 以 name 對**既有資料匹配 → 沿用**（reused），無匹配 → 新建；`item_types`／`custom_fields`／`item_templates` **一律新建**（無 uq，id-map 供 custom values 用）。「名稱衝突加後綴」（renamed）＝保底機制：同檔內同 scope 重名第 2 列起或無法沿用時以 `name (2)`、`name (3)`… 新建（實務多為 0，機制與計數仍在）。`lists`／`stocktakes`／`webhooks` 一律新建（名稱非唯一，不加後綴）。
6. **取代模式清空範圍（依賴序明確 DELETE，不用 cascade）**：item 子表（batches／loans／quantity_logs／versions／custom_values／item_tags）→ stocktake_items + stocktakes → list_entries + lists → webhook_deliveries + webhooks → items → categories／locations／warehouses／tags／item_types／custom_fields／item_templates → notification_preferences（自己）→ groups_owned（+其 group_members）。**不清除**：`audit_logs`、`api_tokens`、`images`、`notifications`、外部管道綁定、`item_transfers`、「我加入他人群組」的 group_members（非本帳號資料）。清空列數合計＝`deleted_total`。
7. **參照處理**：`items.category_id/location_id/warehouse_id` 經 taxonomy map 重指；指向備份內不存在者 → **設 null＋warning**（不列錯誤）。`loans.borrower_user_id`／`quantity_logs.user_id`／`item_versions.user_id`：該 user 仍存在 → 保留，否則 → null（loan 若因此兩欄皆空 → `borrower_label` 補「（原借用人不存在）」）。`groups_owned.member_user_ids` **不還原**（跨帳號影響他人，安全）＋warning。`category/location` parent 指向未知／成環 → 視為 root／列錯誤（環）。items 還原 `created_at/updated_at`（解析失敗 → now＋warning）；日期／時間欄皆還原。
8. **對帳（reconciliation）**：對**備份檔內**每個 `track_batches` 物品檢 `quantity == Σ 未耗盡批次`，不一致列入報告（**只報告不自動修**，dry-run 即可預示）；不影響 status。
9. **幣別**：`preferences.currency` 匯出必有（`currency_from_raw`）；**replace 還原、create_only 不覆蓋**（列 skipped＋warning）。
10. **大檔上限**：`MAX_BACKUP_BYTES = 20 * 1024 * 1024`（nginx 32m 之下）；超過 → **413**＋明確 detail。`file` 僅讀入記憶體一次（20 MiB 可接受），MIME 不檢查（只看能否解析）。
11. **錯誤契約**：硬錯誤 → 400／413（無效 JSON、root 非物件、`format_version` 缺失/非整數/<1／>4、replace 未帶正確 `confirm`）；列級軟錯誤 → 200＋`status`（`ok`／`partial`／`error`）＋`errors`（**回全部、上限 100 筆**，另附 `errors_total`；UI 顯示前 5 筆）。`confirm` 僅 `mode=replace && !dry_run` 必填，值須為 `REPLACE`（UI 與 API 雙重防誤用）。`owner_id` 不驗證（資訊欄位）。
12. **稽核**：非 dry-run 匯入成功後寫 `audit_logs`（`action="backup.import"`，meta：mode／status／created_total／deleted_total／errors_total）——**必須在匯入 commit 之後**呼叫（`audit_service.log` 自帶 commit）。
13. **匯出確定性**：各實體清單輸出前以穩定鍵排序（`created_at, id`；taxonomy 以 `name, id`），降低 diff 噪音。
14. **Web 流程**：選檔／切模式 → 自動 dry-run（`mode` 隨選）→ 摘要表（per-entity「現有 → 匯入後」＋建立／沿用／加後綴／略過／錯誤）＋錯誤前 5＋warnings＋對帳區；`replace` 顯示「將刪除 N」＋「先下載備份」快捷＋確認字串輸入；「確認匯入」→ 結果三態（ok 綠／partial 橙／error 紅）；成功且非 error → `qc.invalidateQueries()`（全站）。換檔或切模式即重跑 dry-run。
15. **e2e 確定性**：備份檔以 Playwright `setInputFiles({name, mimeType, buffer})` 注入（先用 `request` fixture 打 `/api/backup/export` 取得 JSON，或組最小檔案）；全程本機 stack，無外部網路。
16. **i18n**：逐鍵插入（勿整檔重寫）——`settings.backup.*`（zh-TW／en）；entity 名稱逐鍵。
17. **不做（範圍外）**：匯入進度百分比／串流上傳（20 MiB 上限內直讀）；`webhook_deliveries` 還原；members 重建；`replace` 的「保留圖片」；export 分頁下載；定時備份。

**執行前置：**
1. worktree：`git worktree add .claude/worktrees/phase29-backup-restore -b claude/phase29-backup-restore`；**無新 migration**（alembic 維持 `0021`）
2. worktree 無 `.env`：先 `cp .env .claude/worktrees/phase29-backup-restore/.env`
3. worktree 首次 `pnpm install`（node_modules 不存在）
4. 起堆疊：`ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx`
5. 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `cd apps/web && pnpm test -- <filter>`／`pnpm typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`；e2e `cd apps/web && pnpm exec playwright test --workers=2`

---

## Phase 1: API（匯出擴充＋匯入）

### Task 1.1: 匯出擴充（format_version 4）

**Files:**
- Modify: `apps/api/app/services/backup_service.py`
- Test: `apps/api/tests/test_backup.py`（擴充）

**TODO:**
- [x] RED：更新／新增測試——`format_version == 4`；items 含 `barcode`／`track_batches`；新鍵存在（`preferences`／`item_custom_values`／`item_batches`／`loans`／`quantity_logs`／`item_versions`／`stocktakes`／`webhooks`／`notification_preferences`）；建 1 物品（barcode、cost、2 批次 1 耗盡）＋借出＋調量 2 次＋自訂欄位/值＋清單＋盤點＋webhook＋通知偏好＋currency=USD → 各鍵內容正確；清單排序穩定（同名建立順序無關）
- [x] GREEN：items 欄位表加 `barcode`／`track_batches`；新增全域查詢與輸出：
  - `preferences: {currency}`（`currency_from_raw(user.preferences or {})`，需載入 user 或用 `select(User.preferences)`）
  - `item_custom_values: [{item_id, custom_field_id, value}]`（限自己 items 的列）
  - `item_batches: [{id, item_id, quantity, expiry_date, received_at, note, is_depleted, created_at}]`
  - `loans: [{id, item_id, borrower_user_id, borrower_label, lent_at, expected_return, returned_at, notes}]`
  - `quantity_logs: [{id, item_id, user_id, old_quantity, new_quantity, reason, created_at}]`
  - `item_versions: [{id, item_id, user_id, snapshot, created_at}]`
  - `stocktakes: [{id, name, status, started_at, completed_at, items:[{item_id, expected_quantity, actual_quantity, note, scanned_at}]}]`
  - `webhooks: [{id, name, url, secret, events, is_active, created_at}]`
  - `notification_preferences: [{type, channel, enabled}]`
- [x] 各清單輸出前穩定排序（`created_at, id`；taxonomy `name, id`）；`_serialize` 沿用（UUID→str、Decimal→str、datetime→isoformat、**新增 `date`→isoformat 分支**——`date` 非 `datetime` 子類實例，先前會直落 `json.dumps` TypeError）
- [x] 既有鍵（items／categories／…／groups_owned）輸出欄位不變（除 items 加 2 欄）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_backup.py`

### Task 1.2: 匯入解析＋plan（dry-run 零寫入）＋route/schema

**Files:**
- Create: `apps/api/app/services/backup_import_service.py`、`apps/api/app/schemas/backup.py`、`apps/api/tests/test_backup_import.py`
- Modify: `apps/api/app/routes/backup.py`

**TODO:**
- [x] RED：新測試檔（`auth` fixture 複製 `test_backup.py` 範式；上傳以 `files={"file": ("backup.json", json.dumps(doc).encode(), "application/json")}`＋`data={"mode":..., "dry_run":"true"}`）：
  - 無效 JSON／root 非物件／`format_version` 缺失／`format_version=5`／`format_version=0` → 400＋明確 detail
  - 大檔（monkeypatch `backup_import_service.MAX_BACKUP_BYTES` 縮小）→ 413
  - 空備份（全鍵空）→ 200 `status="ok"`、各實體 `imported=0`
  - dry-run **零寫入**：匯入前後對所有實體列數與內容不變（含 webhooks／notification_preferences／groups）
  - `mode` 非白名單 → 422；`mode=replace`＋非 dry-run 未帶 `confirm` → 400；`confirm` 非 `REPLACE` → 400
  - v3 檔（無新鍵）可匯入；items 缺 `barcode`／`track_batches` → 預設 null／false
  - 摘要形狀：`entities[]`（entity／existing／imported／created／reused／renamed／skipped／errors）＋`errors[]`（entity／index／name／message）＋`warnings[]`＋`reconciliation[]`
- [x] GREEN：
  - `schemas/backup.py`：`BackupImportEntitySummary`／`BackupImportError`／`BackupReconciliationItem`／`BackupImportResult`（`format_version:int, mode:Literal, dry_run:bool, status:Literal["ok","partial","error"], deleted_total:int, entities:[...], errors:[...], errors_total:int, warnings:[str], reconciliation:[...]`）
  - `backup_import_service.py`：`plan(session, user_id, payload, *, mode) -> _Plan`（純讀：解析→逐實體驗證→名稱匹配→id-map→對帳；UUID 於此配發；回 per-entity buckets＋errors＋warnings＋reconciliation＋replace 的將刪除數）；`MAX_BACKUP_BYTES`；`parse` 硬錯誤拋 `BackupFormatError`（route 轉 400）
  - `routes/backup.py`：`POST /import`（`file: UploadFile`、`mode: Literal["create_only","replace"]=Form("create_only")`、`dry_run: bool=Form(False)`、`confirm: str|None=Form(None)`；`response_model=BackupImportResult`）——讀檔（>上限→413）→ parse（硬錯→400）→ `confirm` 檢查 → plan → `dry_run=True` 回摘要；`:False` 進 apply（T1.3/T1.4）
- [x] 列級驗證定案（錯誤訊息具體、繁中）：items（`name` 必填非空；`quantity` 非負整數預設 1；`barcode` ≤32 字；`min_quantity`／`cost` 非負；`tag_names` 字串陣列）；categories/locations（`name` 必填；環檢測）；batches/logs/versions/loans/stocktake_items（`item_id` 須命中 id-map，否則列錯誤）；lists（`kind`／`title` 必填）；webhooks（`url` 必填）；通知偏好（`type`／`channel`／`enabled` 必填）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_backup_import.py`

### Task 1.3: create_only apply（id-map／名稱匹配／webhooks 停用／對帳）

**Files:**
- Modify: `apps/api/app/services/backup_import_service.py`
- Test: `apps/api/tests/test_backup_import.py`（續寫）

**TODO:**
- [x] RED：
  - **round-trip 等價**：帳號 A 全量資料（分類樹／位置樹／標籤／倉庫／自訂欄位＋值／2 物品（barcode／cost／track_batches）／2 批次（1 耗盡）／借出（借用人 B）／2 調量歷程／1 版本／清單＋2 列／盤點／webhook／通知偏好／currency=USD）× export → 空帳號 C **replace 匯入** → 重匯出後 A/C 資料等價（ids／owner 正規化、逐實體業務欄位比對；currency 相同）；另 **create_only 匯入** 空帳號 → 除 `preferences.currency`（skipped＋warning）外等價
  - [x] **名稱匹配**：C 已有分類「食物」／標籤「x」／倉庫「家」→ create_only 匯入同名備份 → 不重複建立（`reused` 計數）且物品正確掛上既有列；**後綴**：同檔含兩個同 scope 同名分類（人工併檔）→ 第 2 個 `name (2)`＋`renamed=1`
  - [x] 引用不存在：item 的 `category_id` 指未知 → null＋warning；batch 指未知 item → 列錯誤（`skipped`）
  - [x] webhooks 匯入後 `is_active=false`（備份中為 true）；`groups_owned` 建立但 `members` 不還原（warning）；loan `borrower_user_id` 不存在 → null＋label 補值
  - [x] **partial**：1 列壞（items 空 name）＋其餘有效 → `status="partial"`、`errors_total=1`、有效列已匯入、`errors[0].name` 可讀
  - [x] **對帳**：備份內 `quantity != Σ 未耗盡批次` 的物品 → `reconciliation` 1 筆（dry-run 與實際匯入皆回）
  - [x] 稽核：非 dry-run 成功匯入後 `audit_logs` 有 `backup.import`（`resource_id=None`、meta 計數）；dry-run **不寫**稽核
- [x] GREEN：`apply_create_only(session, user_id, plan)`——依 plan 建立（先 taxonomy → items → 子表 → lists／stocktakes／webhooks／prefs）；`reused` 沿用既有列；`renamed` 後綴；`webhooks.is_active=False`；`notification_preferences` 既有 (type,channel) → `skipped`；currency → skipped＋warning；`await session.commit()`；完成後 `audit_service.log(...)`（T1.2 契約 12）
- [x] 交易邊界：service 內單一 `commit`；例外 → `rollback()` 後 raise

**Commands:**
- 同 T1.2

### Task 1.4: replace apply（依賴序清空＋單一交易＋回滾）＋隔離性

**Files:**
- Modify: `apps/api/app/services/backup_import_service.py`
- Test: `apps/api/tests/test_backup_import.py`（續寫）

**TODO:**
- [x] RED：
  - **等價＋清空**：C 有舊資料（物品／清單／批次／webhook）→ replace 匯入 → 舊資料全數消失（逐實體 0 或＝備份數）、`deleted_total` > 0、新資料完整
  - [x] **隔離性**：B 帳號自有物品／分類／清單／webhook／通知偏好 → A replace 匯入前後 B 全數不變（含 B 的 group_members 於 A 的群組？——A 群組被清 → B 對 A 群組的 membership 消失，屬 A 資料範圍，測試登錄此語意；反之「B 自己群組」不變）
  - [x] **plan 有錯 → 中止零寫入**：replace＋1 壞列 → `status="error"`、`deleted_total=0`、原資料與稽核不變、無 `backup.import` 稽核
  - [x] **執行期例外 → rollback**：monkeypatch apply 內某一步（如 `_insert_items`）raise → 原資料完整（含被清前的列數）＋rollback 後無殘留
  - [x] dry-run replace：`deleted_total`＝現有可清列數、零寫入
  - [x] `confirm=REPLACE` 成功案例（非 dry-run）通過
- [x] GREEN：`apply_replace(session, user_id, plan)`（與 T1.3 共用 `apply_plan`；例外 rollback 後 re-raise → route 轉 500，資料完整）——同一交易：`_wipe(session, user_id)`（依定案 6 依賴序 delete，逐一計數）→ 建立（重用 create_only 的 insert 步驟）→ `commit()`；任何例外 `rollback()` → `BackupImportResult(status="error")`；currency 覆寫；稽核於 commit 後
- [x] `deleted_total` 於 replace dry-run 以 COUNT 計算（不刪）；非 dry-run 以實際 rowcount 覆寫

**Commands:**
- 同 T1.2

### Task 1.5: api-types 重生成

**Files:**
- Modify: `packages/api-types/openapi.json`、`packages/api-types/src/index.ts`

**TODO:**
- [x] `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`＋`pnpm --filter @ims/api-types gen:types`
- [x] 確認生成：`BackupImportResult`／`BackupImportEntitySummary`／`BackupImportError`；`POST /api/backup/import` multipart
- [x] Commit（獨立 `chore(api-types)`）

---

## Phase 2: Web 備份頁

### Task 2.1: backup API client

**Files:**
- Create: `apps/web/lib/api/backup.ts`、`apps/web/lib/api/backup.test.ts`

**TODO:**
- [x] RED：`global.fetch` mock 範式——`downloadBackup(token)` 打 `/backup/export` 回 Blob 觸發下載（`URL.createObjectURL` spy；檔名自 `Content-Disposition`、缺失 fallback `ims-backup.json`）；`importBackup(file, {mode, dryRun, confirm}, token)` FormData 帶 `file`／`mode`／`dry_run`／`confirm`（confirm 僅 replace 非 dry-run）；回傳型別 `BackupImportResult`（自 `paths["/api/backup/import"]`）
- [x] GREEN：`BackupImportResult` type alias；`downloadBackup` 仿 `downloadItemsCsv`（`Content-Disposition` 檔名 fallback `ims-backup.json`）；`importBackup` 仿 `importItemsCsv`

**Commands:**
- `cd apps/web && pnpm test -- lib/api/backup`

### Task 2.2: 備份頁＋導覽＋匯出卡

**Files:**
- Create: `apps/web/app/(app)/settings/backup/page.tsx`、`apps/web/components/settings/backup-panel.tsx`、`apps/web/components/settings/backup-panel.test.tsx`
- Modify: `apps/web/components/settings/settings-nav.ts`、`apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`

**TODO:**
- [x] RED：nav 有 `backup`（`/settings/backup`，integrations 第 4 位）；面板渲染「匯出備份」卡；點「下載備份」→ `downloadBackup` 被呼叫（token 取自 `useAccessToken`）→ 成功 toast；失敗 → 錯誤 toast
- [x] GREEN：頁面 `SettingsPageShell`（`settings.index.pages.backup.title/description`）；面板匯出卡（說明＋按鈕＋loading「準備中…」）；i18n `settings.backup.export.*`／`settings.index.pages.backup.*` 逐鍵插入兩檔
- [x] 行動版：卡片堆疊、按鈕 ≥44px（`max-sm:min-h-11`）

**Commands:**
- `cd apps/web && pnpm test -- components/settings/backup-panel`

### Task 2.3: 匯入卡——選檔 → dry-run 摘要 → replace 確認

**Files:**
- Modify: `apps/web/components/settings/backup-panel.tsx`、`backup-panel.test.tsx`

**TODO:**
- [x] RED：
  - 選檔（`userEvent.upload`）→ 自動呼叫 `importBackup(file, {mode:"create_only", dryRun:true})`；摘要表渲染 per-entity（entity 中文名／現有／匯入後＝existing+created+renamed／建立／沿用／加後綴／略過／錯誤）；**切模式**（replace）→ 以 `mode:"replace"` 重跑 dry-run
  - errors 前 5 筆＋「還有 N 筆」；`warnings` 列表；`reconciliation` 區塊（橙）；replace：紅警示「將刪除 N 筆」＋「先下載備份」按鈕觸發 `downloadBackup`；確認字串輸入（placeholder `REPLACE`）——不符 → 「確認匯入」disabled，相符 → enabled
  - 硬錯誤（400 `detail`）→ 卡內 inline 明確訊息（`getApiErrorDetail`）；loading：解析中／比對中（`aria-busy`）
- [x] GREEN：`BackupPanel` 導入卡 state（`file`／`mode`／`dryRunResult`／`confirmText`／`busy`）；`useMutation` 或直接 async；replace 摘要之「匯入後」＝`created+renamed`；i18n `settings.backup.import.*`／`summary.*`／`replace.*`／`errors.*`（實作時定稿鍵名）
- [x] 無檔案空態：引導文案「選擇備份檔後會先顯示預覽，確認後才會寫入」

**Commands:**
- 同 T2.2

### Task 2.4: 執行匯入＋結果三態＋invalidate＋錯誤態

**Files:**
- Modify: `apps/web/components/settings/backup-panel.tsx`、`backup-panel.test.tsx`

**TODO:**
- [x] RED：
  - 「確認匯入」→ `importBackup(file, {mode, dryRun:false, confirm})`；`status:"ok"` → 綠報告（建立 X 筆／刪除 Y 筆）；`partial` → 橙＋失敗清單；`error` → 紅「未變更任何資料」；成功且 `status!=="error"` → `qc.invalidateQueries()`（spy）＋「重新比對」按鈕
  - 上傳後網路失敗 → toast＋inline 可重試；重新選檔 → 清結果重跑 dry-run
  - replace 匯入呼叫帶 `confirm:"REPLACE"`；create_only 不帶
- [x] GREEN：結果報告區塊（`role="status"`＋icon＋文字，§5.6 不單靠色彩）；i18n `result.*`；QueryClient 注入
- [x] locale 鍵集比對零差異（python flat-set 檢查）

**Commands:**
- `cd apps/web && pnpm test -- components/settings/backup-panel && pnpm typecheck`

---

## Phase 3: e2e、文件收尾

### Task 3.1: e2e `backup.spec.ts`

**Files:**
- Create: `apps/web/tests/backup.spec.ts`

**TODO:**
- [x] ① 桌面 round-trip：register A → API 建分類／標籤／2 物品（1 含 cost／barcode）→ `request.get("/api/backup/export")` 取 JSON（登入 token）→ `/settings/backup`：按「下載備份」→ `page.waitForEvent("download")` 檔名 `ims-backup-*.json`；register B → login → 上傳該 JSON → 摘要「現有 0 → 匯入後 2」「建立 2」→「確認匯入」→ 綠報告 → `/items` 見 2 件（含標籤）
- [x] ② replace：帳號 C 建 1 物品 → 上傳 A 備份 → 選「取代」→ 摘要顯示「將刪除」>0 → 確認字串輸入 `WRONG` → 按鈕 disabled；改 `REPLACE` → 匯入 → `/items` 僅 A 的 2 件（C 原 1 件消失）
- [x] ③ 錯誤態：上傳 `{ invalid json`（`setInputFiles` buffer）→ inline「這不是有效的 JSON 檔」（或 API detail）；空物件 `{}` → `format_version` 錯誤訊息
- [x] 全套 e2e 回歸（62 passed；`--workers=2`）

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx && cd apps/web && pnpm exec playwright test --workers=2`

### Task 3.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.29]`）、`docs/v2-roadmap.md`（Phase 29 ✅＋測試規模）、本計畫（勾選＋Final Verification）

**TODO:**
- [ ] CHANGELOG alpha.29：export v4（全量：barcode／批次／借還／歷程／盤點／webhooks／通知偏好／幣別）；`POST /api/backup/import`（dry-run／create_only／replace／對帳／稽核）；Web「備份」頁（匯出＋匯入三態）
- [ ] v2-roadmap：Phase 29 row ✅＋測試規模更新
- [ ] 本計畫：全任務勾選＋Final Verification（實測數字、環境註記）
- [ ] 收尾視覺走查：桌機（匯出卡／dry-run 摘要／replace 警示＋確認字串／結果三態）＋行動 390（卡片堆疊）；截圖人工檢視

**Commands:**
- `cd apps/web && pnpm exec playwright test --workers=2`

---

## API 契約（實作權威）

**`GET /api/backup/export`**（既有路徑擴充）：
- 回應 `format_version: 4`；既有鍵全保留（items 加 `barcode`／`track_batches`）；新增鍵：`preferences{currency}`、`item_custom_values[]`、`item_batches[]`、`loans[]`、`quantity_logs[]`、`item_versions[]`、`stocktakes[]`、`webhooks[]`、`notification_preferences[]`
- `Content-Disposition` 不變

**`POST /api/backup/import`**（**新增**，multipart/form-data）：
- `file`（JSON，≤20 MiB → 413）；`mode`＝`create_only`（預設）｜`replace`；`dry_run`（bool，預設 false）；`confirm`（`mode=replace && !dry_run` 必填且＝`REPLACE`，否則 400）
- 硬錯誤 400：JSON 無效／root 非物件／`format_version` 缺失或非整數或 <1 或 >4／`confirm` 規則；422：`mode` 非法
- 回應 200 `BackupImportResult`：

```json
{
  "format_version": 4, "mode": "create_only", "dry_run": true,
  "status": "ok | partial | error",
  "deleted_total": 0,
  "entities": [{"entity":"items","existing":0,"imported":2,"created":2,"reused":0,"renamed":0,"skipped":0,"errors":0}],
  "errors": [{"entity":"items","index":3,"name":"帳篷","message":"..."}],
  "errors_total": 0,
  "warnings": ["..."],
  "reconciliation": [{"item_id":"...","name":"...","quantity":5,"batch_total":3}]
}
```

- 語意：plan 純讀（dry-run 零寫入）；create_only 列級錯誤容忍（partial）；replace 全有全無；`entities` 分桶 `imported = created + reused + renamed + skipped + errors`；errors 回全部（上限 100，`errors_total` 為總數）；對帳＝檔案內 `track_batches` 物品 `quantity vs Σ 未耗盡批次`
- 匯入成功（非 dry-run）後寫 `audit_logs`（`backup.import`）；dry-run 不寫

**Web client**：`downloadBackup(token)`；`importBackup(file, {mode, dryRun, confirm}, token): Promise<BackupImportResult>`

### §5.4 狀態表（本 phase 介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| 匯出卡（29） | 按鈕「準備中…」 | — | 錯誤 toast＋按鈕可重試 | 「備份已開始下載」toast | — |
| 匯入卡（29） | 上傳/解析 progress（`aria-busy`）；dry-run「比對中…」 | 未選檔 → 引導文案（先預覽、確認才寫入） | 空檔/格式錯誤 → 卡內明確訊息；驗證失敗 → per-entity 錯誤列舉（前 5 筆）＋`detail` inline | 結果報告三態：全成功綠（建立 X／刪除 Y）／部分成功橙＋失敗清單／全失敗紅（未變更資料） | 部分成功明確計數，不靜默；replace 顯示將刪除總數＋確認字串 |

- 補充規格：dry-run 摘要必含 per-entity「現有 → 匯入後」對照（建立 N／沿用 R／名稱衝突加後綴 M／略過 S／錯誤 K）；replace 顯示將刪除數＋「先下載備份」

### 驗收對照（roadmap §六 Phase 29）

| 驗收項 | Task |
|---|---|
| `POST /api/backup/import`（multipart、dry_run） | T1.2 |
| 驗證 `format_version`＋per-entity 摘要與錯誤列舉 | T1.1（v4）＋T1.2 |
| create_only：新 id、名稱匹配/後綴、不覆蓋 | T1.3 |
| replace：單一交易清空＋失敗全回滾＋隔離性 | T1.4 |
| 不還原 audit_logs／api_tokens；webhooks 停用還原 | T1.3＋T1.4（清空範圍） |
| 關聯重建（taxonomy 名稱匹配；loans／quantity_logs／batches id-map） | T1.3 |
| 匯入後對帳（quantity vs 批次） | T1.2＋T1.3 |
| 還原範圍全量＋版本遞增與相容矩陣 | T1.1＋T1.2 |
| Web「備份」頁：匯出＋匯入三態（選檔→dry-run 摘要→確認→結果） | T2.2–T2.4 |
| dry-run 零寫入 | T1.2 |
| 大檔處理（大小上限） | T1.2（413／20 MiB） |
| round-trip 等價（export→import 空帳號） | T1.3＋T3.1① |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run --extra test pytest -q` → ___ passed
- [ ] Web：`pnpm test` → ___ passed（___ 檔）＋`typecheck` 0 error
- [ ] api-types 重生成零 diff
- [ ] e2e：___ passed（含 `backup.spec.ts` 3 情境；`--workers=2`；於全部程式碼變更後重跑）
- [ ] 視覺走查：桌機（匯出卡／dry-run 摘要／replace 確認字串／結果三態）＋行動 390；截圖人工檢視

### 收尾環境註記（2026-10-17 起填）

- worktree 首次使用需先 `pnpm install`；`packages/api-types/src/index.ts` 為 tracked 生成檔 → 與 `openapi.json` 一併提交
- e2e 跑在 worktree 自身 `ims-v2` stack（`ENABLE_DEV_ROUTES=1`、nginx port 80、`client_max_body_size 32m`）；本 phase 無 migration（alembic 維持 0021）
- `collaboration.spec.ts` 為已知間歇性案例（重跑排除）
