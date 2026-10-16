# Changelog

本專案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式與 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

v2 為全面重寫版（Next.js + FastAPI monorepo，位於 `apps/`），v1 為 Flask + Jinja2（保留於 `app/`、`templates/` 目錄；參見 [`legacy-v1` 章節](#legacy-v1-保留))。

## [Unreleased]

## [2.0.0-alpha.26] — Phase 26：多層位置樹重建

- **破壞性 schema 重構**：`locations` 由平面三欄（floor/room/zone）改為**任意深度樹**——`parent_id`（self-FK, RESTRICT）、`name`、`kind`（`floor|room|shelf|box|other` 或自由文字）、`sort_order`（同 parent 內）、`floor_plan_image_id` 保留；同 parent 同名唯一（partial unique ×2）；`(owner_id, parent_id, sort_order)` 索引。Alembic 遷移 `0020`（**不可逆**，downgrade 明確 raise）
- **一次性資料遷移**（`location_tree_migration`）：舊列 → canonical 節點鏈（深度 1→`floor`、2→`room`、≥3→`other`），物品**重新指向**最深節點後刪除舊列（**保證無孤兒**）；同 owner 同組合重複列合併；`analyze_flat()` 唯讀 dry-run（`scripts/location_migration_dry_run.py`）與 `migrate_flat()` 同報告：`{source_rows, created_nodes, merged_rows, orphan_nodes, unassigned_items}`。dev 庫實測：`5 / 7 / 1 / 1 / 216`，遷移後 0 件懸空 `location_id`
- **樹 API**：`GET /api/locations`（走訪序＋完整 `path`）、`GET /api/locations/tree`（巢狀＋直接物品數 `item_count`）、`GET /api/locations/{id}/path`（麵包屑 `nodes`）、`POST`（`parent_id`／`kind`）、`PATCH`（改名／kind／排序／floor plan，帶 `parent_id` 即**搬移**）、`POST /reorder`（**parent 範圍**、需完整子集合）、`DELETE`
- **守衛**：搬到自身或子孫 → 422 `{code:"cycle"}`；同 parent 同名 → 409 `{code:"duplicate_name"}`；**有物品或有子節點一律禁止刪除**（409 結構化 detail `{code, items, children}`，無遞移刪除）；parent 非本人所有 → 404
- **含子孫查詢**：`GET /api/items?location_id=&location_scope=subtree|exact`（**預設含子孫**，recursive CTE 取子孫集合；「僅此層」＝`exact`）
- **消費端整合**：`ItemRead.location` 帶完整樹路徑（依物品 owner 批次計算，共享可見物品亦正確；列表／詳情／掃碼候選一致）；統計 `by-location` label＝樹路徑；CSV 匯出改 `location_path`（舊三欄檔仍可匯入，逐層建／重用節點）；備份 `format_version` 1 → 2（locations 改樹欄位）；`warehouse` 維持獨立軸
- **新 UI**：`/locations` 樹管理頁（展開收合、行內改名（F2／雙擊）、新增子節點、搜尋（無結果→建立節點）、空樹引導、skeleton／錯誤重試）——**桌面拖放**（HTML5 DnD；非法目標即時灰化＋tooltip；拖到容器空白＝移到最上層，**drop 停止冒泡**兩者互斥不重複送出）與**行動版**「⋯ → 搬移至」（bottom sheet＋扁平搜尋顯示完整路徑）；**鍵盤操作**（↑↓ 移焦、→ 展開／首子、← 收合／父節點、Enter 切換、F2 改名；roving tabindex）；`role="tree"`＋`aria-expanded/level/selected`、樂觀更新＋`aria-live` 播報
- **樹狀選擇器**（共用）：桌機**cascading** 逐層下拉（可停在任一層）／行動 **bottom sheet＋扁平搜尋**（完整路徑）；整合物品表單、篩選面板、刪除對話框「先搬移物品」
- **路徑呈現**：物品詳情麵包屑（>3 層中間截斷「1F / … / 抽屜」＋`title` 全路徑）、列表位置欄與批次搬移清單顯示樹路徑、篩選面板「僅此層」toggle
- **安全網**：遷移前強制全庫備份（`pg_dump`）＋dry-run 審查（roadmap §六要求）
- 新增 47 個 API 測試（644 → 691）；新增 52 個 web 測試（324 → 376，72 → 79 檔）；e2e 16 → 17 spec（新增 8 情境：建樹／改名／拖放（含非法目標灰化）／刪除限制→先搬移／表單 cascading→詳情麵包屑／篩選含子孫＋僅此層／行動搬移／真實遷移資料在 UI 呈現）

## [2.0.0-alpha.25] — Phase 25：條碼掃描（內查＋外查）

- 新欄位與資料表：`items.barcode`（varchar 32、`(owner_id, barcode)` 索引、**不設唯一**——同條碼可分開建檔多件）與 `barcode_lookups` 外部查詢快取（`code` unique／`source`／`payload` JSONB 可空＝負快取／`fetched_at`）；Alembic 遷移 `0019`
- 新 API `GET /api/barcodes/{code}`（任何登入者；空／>64 字 422）：先 canonicalize（去空白／連字號／底線；數字 8–14 位或 ISBN-10 收斂），owner 範圍精確內查；命中即回候選（`external_status=skipped`，**不呼叫外部**）；查無才外查
- 外查 provider 抽象：EAN-13／EAN-8／UPC-A（checksum 驗證）→ Open Food Facts；ISBN-10 與 978/979 書碼 → Open Library；httpx timeout 3 秒、fail-soft（逾時／網路／非 JSON／5xx → `unavailable`，不寫快取、不 500）；404／`status: 0` → `not_found`
- 快取：正負結果皆存（負快取避免家庭物品重複打 API），TTL 30 天；並發以 savepoint 吸收 unique 衝突
- 外部結果 → 新增表單 prefill：名稱、描述（品牌／分類／容量；書：作者／出版／出版社）＋分類建議（與使用者葉分類名稱字面比對、唯一命中才帶入）＋來源標註；**只填空欄位**，不覆蓋已輸入
- 物品整合：表單 `barcode` 欄位（手輸或掃碼帶入；「查詢」按鈕）＋`?barcode=` 帶入（快取命中即時）；詳情頁 monospace 顯示＋複製；列表 `q` 併入條碼比對；CSV 匯出新增 `barcode` 欄（description 後）、匯入可選欄並套正規化（round-trip 不丟欄位）
- `/scan` 掃描引擎置換：原生 `BarcodeDetector`（可用時快路徑，依 `getSupportedFormats` 取交集）→ `@zxing/browser` 多格式 fallback（QR、EAN-13/8、UPC-A/E、Code128/39、ITF＋TRY_HARDER）；既有 QR 流程零回歸（deep link／裸 UUID 導頁、非條碼輸入維持名稱搜尋）
- 掃碼流程 UI：內查單筆直接跳轉、多筆候選列表（縮圖／名稱／位置路徑／數量）；外查三態與查無區分（`ok` 來源標註＋帶入新增；`not_found`「查無公開資料，已帶入條碼，請補名稱」；`unavailable`「網路不穩，條碼已保留」＋重試）；權限被拒→「開啟權限」＋手動輸入保底
- 行動版掃描 FAB（§5.7）：僅 `md` 以下顯示、避底部安全區、`aria-label`；`/scan` 頁自身不顯示；桌面既有 nav 入口保留
- 標籤列印加印條碼數字（stretch；`ItemLabel.barcode`，單張與批量標籤頁）
- 依賴：新增 `@zxing/browser`＋`@zxing/library`；移除 `qr-scanner`
- 新增 42 個 API 測試（602 → 644）；新增 55 個 web 測試（269 → 324，64 → 72 檔）；e2e 15 → 16 spec（新增 7 情境：內查單筆／多筆候選、非條碼回歸、表單 prefill、建立＋詳情＋搜尋、行動 FAB、桌面無 FAB）
- 註：e2e 不依賴外部網路（外查三態由 API provider mock 與元件測試覆蓋）

## [2.0.0-alpha.24] — Phase 24：排程自動化＋到期提醒

- 新 job 機制（外部 cron ＋ 冪等端點；Phase 31 月報表重用）：job registry（`JobSpec`／`run_job`）＋ `POST /api/jobs/{job_name}/run`（**管理員**；匿名 401／非 admin 403／未知 job 404；管理員 PAT 可觸發）、`GET /api/jobs/{job_name}/status`（任何登入者；門檻＋上次執行＋`stale` 停跑判定）
- 新資料表 `job_runs`（執行觀測；`result` 固定契約 `{processed, emitted, errors}`）與 `expiry_alerts`（冪等 dedupe：UNIQUE(`batch_id`,`level`,`sent_on`)＋savepoint 吸收並發衝突）；Alembic 遷移 `0018`
- 首個 job `expiry-scan`：以 Asia/Taipei「今天」掃描批次到期——`d30`／`d7`／`d0` 各為首次跨入**一次性**提醒（上線初期既有批次一次補齊）、`expired` 過期後每日一則至過期 14 天止（站內保留）；同日重跑不重發、隔日只補差額
- 摘要制通知：每用戶每日每類型最多一則（「N 件物品即將到期／已過期」＋最急品名與天數），deep link 直達到期檢視（`/items?sort=expiry_asc`、`/items?expiry=expired&sort=expiry_asc`）；尊重 Phase 23 通知偏好（`emit` 層過濾，Email／LINE／Telegram 預設維持關）
- 失敗語義：逐用戶隔離（單一用戶失敗不影響他人）、部分成功保留、`status=failed` 可安全重跑補差額
- 新 API 欄位：`GET /api/stats/expiry` 加 `reminded_today`（該 owner 今日有無掃描提醒；固定查詢數）
- 新 UI：儀表板到期卡疊加「今天已彙總提醒」註記（Bell＋muted 小字，不改變排序與尺寸）；`/settings/reminders`「提醒排程」頁（群組「通知與提醒」第三頁）——目前門檻、上次執行（成功／失敗／執行中／從未）、停跑警示（從未執行或逾 26h）＋cron 片段＋PAT 與文件連結；loading／error 狀態契約完備
- 文件：新增 [`docs/scheduling.md`](docs/scheduling.md)（三分鐘上手＋crontab／systemd timer／GitHub Actions 範例＋端點語義＋疑難排解）
- 移除閒置依賴 `apscheduler`（含 `pytz`／`tzlocal` 連帶項；容器系統 tzdb 正常，`ZoneInfo` 驗證通過）
- 新增 42 個 API 測試（560 → 602）；新增 11 個 web 測試（258 → 269，61 → 64 檔）；e2e 14 → 15 spec（新增 3 情境：掃描→摘要→deep link→註記主流程、權限矩陣、設定頁狀態）

## [2.0.0-alpha.23] — Phase 23：通知偏好中心＋設定頁 IA 重構

- 設定頁 IA 重構：單頁 10 tabs → `/settings` 索引頁四群組（個人／通知與提醒／整合與資料／管理）＋ 11 個子路由（`/settings/notifications` 為新增頁，其餘 10 個為既有面板搬遷）；`/settings/taxonomy` 與既有連結不動，既有面板功能零回歸
- 新資料表 `notification_preferences`（`user_id`＋`type`＋`channel` unique；缺列＝預設）；Alembic 遷移 `0017`
- 新 API：`GET /api/notifications/preferences`（展開 11 類型 × 5 管道完整矩陣＋`has_custom`＋各管道可用性）、`PUT`（批次更新；未知 type／channel → 422）、`DELETE`（重置為預設）
- 只存「顯式覆寫」列：未存＝預設；`enabled == 預設` 時自動刪列；偏好計算唯一入口 `services/notification_prefs.py`（類型／管道／鎖定／預設／emit 映射全集中）
- 預設值：全部開啟，唯二例外「即將到期」與「已逾期」的 Email／LINE／Telegram 預設關（保留站內與瀏覽器推播）；不可關類別 `group_invite`、`system` 由後端強制（PUT 關閉 → 422）
- 行為整合：`emit()` 站內建立前查偏好（關 → 不建列）；`deliver_all(type=…)` 逐管道過濾；偏好查詢 fail-soft（出錯一律視為開啟，不影響觸發交易）
- 未綁定判定：LINE＝`user_line_linked`、Telegram＝`user_telegram_linked`、Web Push＝訂閱數 > 0；未綁定欄位 disabled＋「前往綁定」引導至 `/settings/channels`
- 新 UI：`/settings/notifications` 偏好矩陣 — 桌機表格式（類型×管道）／md 以下卡片式；樂觀切換＋失敗回滾 toast、鎖定列鎖頭＋tooltip、預設摘要條、重置 AlertDialog、skeleton／錯誤重試；tap target ≥44px
- 新增 40 個 API 測試（520 → 560）；新增 40 個 web 測試（218 → 258，48 → 61 檔）；e2e 14 spec（新增 4 情境，含「關閉站內 low_stock → 門檻觸發不再產生通知」端到端整合）

## [2.0.0-alpha.22] — Phase 22：批次庫存＋到期管理

- 新資料表 `item_batches`、`items.track_batches` 旗標；Alembic 遷移 `0016`
- 新 API：`GET/POST /api/items/{id}/batches`、`POST /api/items/{id}/consume`（FEFO，支援 `quantity`）、`POST /api/items/{id}/batches/disable`（合併並關閉追蹤）、`PATCH/DELETE /api/batches/{batch_id}`、`POST /api/batches/{batch_id}/consume`、`GET /api/stats/expiry?days=`
- FEFO 消耗依到期日升冪（無到期日最後）、支援跨批次拆分；超額消耗 409 不靜默；併發雙 consume 以原子條件 UPDATE＋rowcount 保證（SQLite／Postgres 皆無 lost update）
- 追蹤物品數量一律由批次重算（進貨／消耗／關閉追蹤／盤點／CSV 匯入皆維持 invariant）；`PATCH` tracked 物品 `quantity` → 409 導向批次端點
- 列表聚合：`soonest_expiry` 以 correlated MIN 子查詢計算（查詢數不隨列數成長）；新增 `expiry=expired|expiring_soon` 與 `sort=expiry_asc` 篩選
- 到期門檻：`days_left<0` 過期、0–7 天即將到期（`EXPIRING_SOON_DAYS=7`）；`clock.py` 為全站「今天」唯一來源（Asia/Taipei）
- 新 UI：物品詳情批次區塊（進貨／−1 樂觀消耗含回滾／已耗盡折疊／關閉追蹤確認）、物品表單「追蹤批次」切換（新建送出後建立首批、編輯開啟當下即建立）、物品列表到期 badge／篩選 chips／到期模式（行內 −1、批次展開、清零 toast＋`aria-live`）、儀表板到期行動卡（deep link 至篩選視圖）
- 色彩契約 §5.6：新增 `--warning`／`--success` tokens；到期 badge 過期紅／7 天內橙／其餘中性，且附文字標籤（非僅顏色）
- 新增 79 個 API 測試（441 → 520）；新增 56 個 web 測試（162 → 218，41 → 48 檔）
- 修正（Final Verification 期間發現的真實缺陷）：
  - Service Worker 首裝接管（`clients.claim()`）不再整頁 reload：原本每次首次造訪都會在載入後約 1 秒重載、抹掉使用者正在輸入的內容；改為僅在「更新接管」或使用者按下重新載入時重載（`shouldReloadOnControllerChange`）
  - 登入表單改為不受控輸入＋`FormData`：避免 hydration 完成時 React 以空 state 覆寫已輸入的帳密
  - React Query 對 4xx（含 404/401）不再重試：錯誤 UI 即時顯示（原本需等約 7 秒退避重試，「找不到此物品」才會出現）
  - 清單／轉移對話框補齊 `label`↔`input` 關聯（可及性；原本 label 未綁定輸入框）
  - `/__dev/*` 展示頁：`app/__dev` 因 Next 私有資料夾規則（`_` 前綴）永不路由，改置 `app/dev` 並以 rewrite 保留原路徑；新增 `ENABLE_DEV_ROUTES` build arg／env 開關（預設關閉，生產環境仍 404）

## [2.0.0-alpha.21] — Phase 21：Webhook 重試

- `webhook_deliveries` 新增 `attempt`（1-indexed 嘗試次數）與 `next_retry_at`（下次重試時間）欄位，Alembic 遷移 `0015`
- 重試政策：最多 5 次總嘗試（初次 + 4 次重試），backoff 為 30s / 2min / 8min / 30min
- `POST /api/webhooks/process-retries` — 外部 scheduler/cron 呼叫，處理到期重試並回傳 `{processed, succeeded, remaining}`
- `POST /api/webhooks/{id}/deliveries/{delivery_id}/retry` — 擁有者手動重試單筆（繞過 backoff）
- 每次重試產生新的 delivery row（保留完整歷史），前一筆的 `next_retry_at` 清為 NULL
- 成功（2xx）停止重試；網路錯誤視同失敗，一樣排程重試
- 刪除 webhook 時 cascade 刪除 deliveries，process-retries 正確處理「webhook 不存在」情境
- 新增 16 個 API 測試：純政策函式 (is_success, backoff_after)、dispatch 排程、process-retries 重試/成功/放棄、manual retry；API 測試總數 425 → 441

## [2.0.0-alpha.20] — Phase 20：Tag 管理 UI

- 新 API：`GET /api/tags/with-counts`、`PATCH /api/tags/{id}`（rename）、`POST /api/tags/{id}/merge`、`DELETE /api/tags/{id}?force=`、`POST /api/tags/prune-orphans`
- Merge 語義嚴謹：同時 tag 兩者的物品 item_tags 去重 + 其他 reassign + 刪除 source
- Delete 預設拒絕有物品使用的 tag（409），需 `?force=true`
- rename 自動 normalize（lowercase + trim），衝突 409
- 新 UI：`/settings/taxonomy` 新增「標籤」頁籤，inline rename / merge dropdown / delete / 「清理孤兒 tag」按鈕
- 新增 19 個 API 測試（with-counts、rename 衝突/跨用戶、merge overlap/reassign/self-reject、delete force/orphan、prune 冪等）；API 測試總數 406 → 425

## [2.0.0-alpha.19] — Phase 19：CSV tags round-trip

- `tag_names` 欄位加入 export/import 支援，完成 CSV round-trip
- Export 時以字母排序後的 pipe-delimited 字串輸出
- Import 時查不到 tag 就 auto-create（per-owner 隔離）
- 單格內 dedupe：`kitchen|kitchen| |kitchen ` → `kitchen`
- 新增 8 個 API 測試涵蓋 export / import / dedupe / per-owner 隔離 / 完整 round-trip；API 測試總數 398 → 406

## [2.0.0-alpha.18] — Phase 18：Service Worker 更新提示

- SW `install` 不再自動 `skipWaiting`；改由 page 發送 `SKIP_WAITING` 訊息觸發
- 新增 `sw-update-detector.ts` 純 helper：偵測 waiting SW（兩種觸發路徑）與 controllerchange
- `ServiceWorkerProvider` 顯示 sonner 持續 toast（`duration: Infinity`）+「重新載入」action
- SW cache 版本升級 `ims-v2 → ims-v3`
- 新增 12 個 web 測試（7 detector 行為 + 5 sw.js 靜態 invariant）；web 測試總數 75 → 87

## [2.0.0-alpha.17] — Phase 17：文件同步

- 新增 `CHANGELOG.md`（本文件）
- README / README_EN 改以「v2 shipped, v1 legacy」為首，功能列表分 10 大區塊
- FEATURES.md 從行銷口吻改為逐功能開發者參考（列出實際路由、表、欄位、Phase 來源）
- docs/v2-roadmap.md 補上 Phase 1–16 表格與「後續候選」清單
- docs/API.md、docs/ARCHITECTURE.md 頂端加 legacy banner，指向 v2 OpenAPI 與 README 對應章節

## [2.0.0-alpha.16] — Phase 16：PWA Polish

- Manifest 新增 `id` / `scope` / `lang` / `categories` / shortcuts（長按 home-screen icon 直跳 `掃碼`、`新增物品`、`儀表板`）
- `purpose: maskable` 獨立宣告，Android 12+ home-screen icon 遮罩更穩定
- iOS standalone：`apple-mobile-web-app-capable`、status bar 樣式、多尺寸 apple-touch-icon、`format-detection` 關閉電話自動連結
- Service Worker cache 升級 `ims-v1 → ims-v2`，`/scan` 排除 navigate cache（相機頁離線無用）
- 新增 7 個 manifest invariant 測試（icon signature、shortcut 覆蓋、maskable 等）

## [2.0.0-alpha.15] — Phase 15：相機 QR 掃碼

- 新增 `/scan` 路由 + 全域導航的「掃碼」入口
- 動態 import [`qr-scanner`](https://github.com/nimiq/qr-scanner) 不進 server bundle
- `extractItemIdFromPayload()` 純函式：支援完整 URL、巢狀前綴、裸 UUID、大小寫正規化
- 相機拒權 / 無相機 / 初始化錯誤三種狀態都有 actionable 文案
- 桌機 fallback：貼 URL、UUID 或關鍵字即可導航
- 9 個單元測試覆蓋全部 payload 情境

## [2.0.0-alpha.14] — Phase 14：CSV 批次匯入/匯出

- `POST /api/items/bulk-import` — multipart CSV，per-row 驗證 + dry-run 預覽
- `GET /api/items/bulk-export` — 串流輸出，支援 query 篩選
- 設定頁新增「資料匯入/匯出」分頁
- 匯入摘要顯示成功數、失敗列號與原因

## [2.0.0-alpha.13] — Phase 13：物品 QR 與可列印標籤

- `GET /api/items/{id}/label.png` — 物品 QR 標籤（包含名稱）
- 物品詳細頁新增「下載標籤」按鈕
- `/items/labels` 列印預覽頁（A4 多格佈局）

## [2.0.0-alpha.12] — Phase 12：儀表板與統計 v2

- Overview 擴充 `total_warehouses`、`low_stock_items`、`active_loans`
- 新端點：`/by-warehouse`、`/low-stock`、`/active-loans`、`/trend`、`/activity`
- Dashboard 新增 LowStockCard（赤字排序）、ActiveLoansCard（逾期提示）、ActivityFeed（合併 quantity log + loans + 版本快照）
- Statistics 新增 TrendChart（30 天 area chart）、WarehouseChart（pie）
- 修正 Phase 11 的 `LocationCreate.sort_order` TS 類型問題

## [2.0.0-alpha.11] — Phase 11：位置進階

- `locations.sort_order`（手動排序）與 `locations.floor_plan_image_id`（附樓層圖）
- `POST /api/locations/reorder` — 一次改寫排序、跨用戶隔離

## [2.0.0-alpha.10] — Phase 10：Webhooks

- 用戶擁有 HTTP hooks 對 `item.created` / `item.updated` / `item.deleted` 事件派送
- HMAC-SHA256 簽章於 `X-IMS-Signature` header
- `WebhookDelivery` 記錄每次派送的狀態碼與回應摘要
- Fail-soft：派送失敗不影響主交易

## [2.0.0-alpha.9] — Phase 9：備份匯出

- `GET /api/backup/export` — 使用者全資料 JSON dump，含 `format_version=1`
- UUID/datetime 正規化處理；匯入功能 YAGNI 暫緩

## [2.0.0-alpha.8] — Phase 8：倉庫

- `warehouses` 表，`(owner_id, name)` 唯一
- `items.warehouse_id` 可選 FK
- 倉庫 CRUD 設定頁

## [2.0.0-alpha.7] — Phase 7：外部通知

- Email（fastapi-mail SMTP）
- LINE Messaging API push
- Telegram Bot `sendMessage`
- Web Push（pywebpush + VAPID）
- 四種管道全部 fail-soft，失敗不影響通知建立

## [2.0.0-alpha.6] — Phase 6：盤點

- `stocktake_sessions` + `stocktake_items` 雙表
- `scan_item` upsert；`complete_stocktake` 套用差額並寫入 quantity log（`reason=stocktake:<name>`）

## [2.0.0-alpha.4+5] — Phase 4+5：自訂欄位 + 物品歷史

- `item_types`、`custom_fields`、`item_templates` 模型與 CRUD
- 每件物品可附 JSON 形式自訂欄位值
- `quantity_logs`（新舊數量差異）、`item_versions`（完整快照）
- `items.update` 先記錄 delta、再做變更，fail-soft

## [2.0.0-alpha.3] — Phase 3：Gemini AI 辨識

- `POST /api/ai/suggest` — 讀取已上傳圖片，回傳物品名稱、描述、分類建議、標籤
- 使用 `google-genai>=1.0` SDK，模型 `gemini-2.0-flash`，提示語為繁中
- 無 `GEMINI_API_KEY` 回 503；上游錯誤回 502

## [2.0.0-alpha.2] — Phase 2：圖片上傳

- `POST /api/images` multipart upload，MIME 允許清單：jpeg/png/webp/gif
- 儲存路徑 `{media_dir}/{owner_id}/{uuid}{ext}`
- 群組成員可跨擁有者檢視（利用 `visible_item_owner_ids`）

## [2.0.0-alpha.1] — Phase 1：收藏 + API Tokens + 稽核日誌

- `items.is_favorite` 欄位、`/favorites` 篩選與切換
- Personal Access Tokens（`ims_pat_` 前綴、SHA-256 雜湊存放）
- `audit_logs` 表，新增 token、變更權限等敏感操作全記錄

## [2.0.0-alpha.0] — v2 基礎骨架

- Next.js 15 App Router + typed routes，zh-TW / en 雙語
- FastAPI 0.115 async + SQLAlchemy 2.0 + Pydantic v2 + Alembic
- JWT 雙 token（access + refresh cookie）、angles cookie 同步
- Docker Compose（web + api + postgres），健康檢查
- 已復刻 v1：物品 CRUD、分類、位置、清單、借出、群組協作、通知、儀表板、統計

## Legacy v1

Flask + Jinja2 實作仍保留在 `app/`、`templates/`、`static/`，不再接受新功能開發，僅保留資料匯出工具。詳見 [docs/v2-roadmap.md](docs/v2-roadmap.md) 的遷移說明。
