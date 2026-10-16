# Changelog

本專案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式與 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

v2 為全面重寫版（Next.js + FastAPI monorepo，位於 `apps/`），v1 為 Flask + Jinja2（保留於 `app/`、`templates/` 目錄；參見 [`legacy-v1` 章節](#legacy-v1-保留))。

## [Unreleased]

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
