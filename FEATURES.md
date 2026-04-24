# 功能詳述（v2）

v1 的「記錄物品放在哪裡」本質沒有變，但 v2 在此之上重建了幾乎所有功能，並新增了 AI、webhook、PWA、雙語等。本文按功能區塊說明具體實作細節與相關 API 路由。

高階總覽請直接看 [README.md](README.md)；逐 phase 變更請看 [CHANGELOG.md](CHANGELOG.md)。

---

## 📦 物品管理

**資料欄位**：`name`（必填）、`description`、`quantity`（預設 1、non-neg 約束）、`min_quantity`（選，用於低庫存警示）、`notes`、`is_favorite`、`image_id`、`category_id`、`location_id`、`warehouse_id`、`tags[]`、`created_at` / `updated_at`、`is_deleted`（soft delete）。

**主要路由**：
- `GET /api/items` — 列表 + 搜尋（`q`、`category_id`、`location_id`、`warehouse_id`、`tag_ids[]`、`favorite`、`min_quantity`、`page`、`page_size`）
- `POST /api/items` / `GET|PATCH|DELETE /api/items/{id}`
- `POST /api/items/{id}/favorite` 切換收藏
- `GET /api/items/{id}/history` 觀看 quantity log + version snapshot 合併時序

---

## 🏷 分類體系

- **分類（Categories）** — 單層，依名稱唯一 per 用戶
- **位置（Locations）** — 樓層 / 房間 / 區域；`sort_order` 支援手動排序；`floor_plan_image_id` 可附樓層平面圖
- **倉庫（Warehouses）** — 跨實體場所隔離，`(owner_id, name)` 唯一
- **標籤（Tags）** — 多對多，同時支援物品間共用
- **自訂欄位（Custom Fields）** — `item_types` 定義某類物品有哪些自訂欄位；`item_templates` 定義預設值組合；每件物品可在 `custom_values` JSON 存值

---

## 📷 QR / 掃碼

### 產生（Phase 13）
- `GET /api/items/{id}/label.png` 直接回 PNG 標籤（QR + 物品名）
- 物品詳細頁「下載標籤」按鈕
- `/items/labels` 列印預覽頁，A4 多格佈局

### 掃描（Phase 15）
- `/scan` 路由 + 全域導航「掃碼」入口
- 動態 import [`qr-scanner`](https://github.com/nimiq/qr-scanner) 不進 server bundle
- 偏好後置相機（`preferredCamera: "environment"`）、自動跳轉到 `/items/{id}`
- `extractItemIdFromPayload()` 純函式識別：完整 URL、巢狀路徑前綴、裸 UUID、大小寫不敏感、前後空白
- 相機拒權 / 無相機 / 初始化錯誤三種狀態都有繁中文案
- 桌機 fallback：貼 URL、UUID 或關鍵字可搜尋 / 導航

---

## 🤖 AI 辨識（Phase 3）

- `POST /api/ai/suggest` — 請求 body 帶 `image_id`，回傳 `{ name, description, category_hint, tags[] }`
- 實作細節：
  - `google-genai>=1.0` SDK、模型 `gemini-2.0-flash`
  - 提示語為繁體中文，限定 JSON 結構輸出
  - `GEMINI_API_KEY` 未設：回 `503 Service Unavailable`
  - 上游 Gemini 錯誤：回 `502 Bad Gateway`，不洩漏內部 trace

---

## 🤝 借出 / 協作

### 借出（Loans）
- `item_loans` 表含 `borrower_user_id`（系統內部用戶）或 `borrower_label`（外部姓名）二擇一
- 每件物品同時最多一筆未歸還借出（部分索引 `WHERE returned_at IS NULL`）
- `POST /api/items/{id}/loans` 開借出，`POST /api/items/{id}/loans/{loan_id}/return` 歸還
- 儀表板自動排序未歸還、計算 `is_overdue`

### 群組（Groups）
- 跨用戶分享物品可見性
- 權限：`admin` / `member`
- 轉移紀錄：位置 / 倉庫變更進 `item_transfers` 表

---

## 📢 通知（Phase 5 + Phase 7）

### 站內
- `notifications` 表，每用戶個別計數未讀
- `/api/notifications` 列表 + mark-as-read
- 低庫存、借出到期、歡迎訊息、群組邀請

### 外部管道（fail-soft，失敗不影響通知建立）
| 管道 | 實作 |
|------|------|
| Email | fastapi-mail + SMTP |
| LINE | `api.line.me/v2/bot/message/push` via httpx |
| Telegram | `api.telegram.org/bot{token}/sendMessage` via httpx |
| Web Push | pywebpush 2.0 + VAPID claims |

用戶於設定頁綁定後，`deliver_all()` 根據綁定扇出。任何一個管道 HTTP 失敗只會記錄，不會 rollback。

---

## 📋 盤點與庫存（Phase 6）

- `stocktake_sessions` 代表一輪盤點（名稱、建立時間、完成時間）
- `stocktake_items`：每件物品在此輪中掃到的實際數量（`expected = 當下 items.quantity`、`counted` 由使用者輸入）
- `POST /api/stocktake/{id}/scan` upsert；`POST /api/stocktake/{id}/complete` 套用 `counted - expected` 的差額並在 `quantity_logs` 寫入 `reason=stocktake:<session_name>`

---

## 📊 儀表板與統計（Phase 4 + Phase 12）

### Overview（`GET /api/stats/overview`）
總計：items、quantity、categories、locations、tags、warehouses、low_stock_items、active_loans。

### 分布（pie / bar）
- `/api/stats/by-category` · `/by-location` · `/by-warehouse` · `/by-tag`

### 時間序列
- `/api/stats/trend?days=30` — 每日新增物品數（稠密，沒有當天也回 0）

### 警示
- `/api/stats/low-stock` — `quantity < min_quantity`，依 deficit 降序
- `/api/stats/active-loans` — 未歸還借出，含 `is_overdue` 旗標

### 活動流
- `/api/stats/activity` — 合併 `quantity_logs` / `item_loans` 開借出 + 歸還 / `item_versions` 快照，依時間倒序

---

## 🔗 Webhooks（Phase 10）

- 用戶於設定頁新增 HTTP endpoint + 選擇訂閱事件
- 支援事件：`item.created` / `item.updated` / `item.deleted`
- 派送時機：`items_service.create_item / update_item / delete_item` 主交易 commit 後
- HMAC-SHA256 簽章於 `X-IMS-Signature` header（計算方式 `HMAC(secret, body_bytes)`，hex digest）
- `webhook_deliveries` 表記錄每次派送 `status_code`、`response_excerpt`（前 500 字元）、`duration_ms`
- Fail-soft：HTTP 失敗不 rollback 主交易，只在 delivery 表留下錯誤狀態

---

## 🔑 API Tokens + 稽核（Phase 1）

- Personal Access Tokens 前綴 `ims_pat_`，SHA-256 雜湊存放
- 原始 token 只在建立當下出現一次
- `audit_logs` 表記錄：token create / delete、密碼變更、群組權限變更、bootstrap admin 等敏感動作

---

## 📥 CSV 匯入 / 匯出（Phase 14）

### 匯入
- `POST /api/items/bulk-import` multipart CSV
- Per-row 驗證，失敗不影響成功者
- 支援 `dry_run=true` 預覽：回傳將建立的筆數、會跳過的失敗列號 + 原因
- 欄位對應：`name`（必）、`description`、`quantity`、`min_quantity`、`notes`、`category_name`、`location_label`、`warehouse_name`、`tag_names`（以 `|` 分隔）

### 匯出
- `GET /api/items/bulk-export` 串流 CSV（`text/csv; charset=utf-8`）
- 尊重 query 篩選，同 `GET /api/items` 規則

---

## 💾 備份匯出（Phase 9）

- `GET /api/backup/export` — 使用者全資料 JSON dump
- `format_version: 1` 用於未來 schema 相容
- 涵蓋：items（含 soft-deleted）、categories、locations、warehouses、tags、custom_fields、item_templates、loans、quantity_logs、webhooks、api_tokens（只含 metadata，不含明文）、audit_logs
- `datetime` 正規化為 ISO-8601，`UUID` 正規化為字串

---

## 📱 PWA（Phase 16）

### Manifest
- `id: "/dashboard"`、`scope: "/"`、`display: standalone`、`orientation: portrait`
- `lang: "zh-Hant"`、`categories: ["productivity", "utilities"]`
- `shortcuts[]`：長按 home-screen icon 跳 `/scan`、`/items/new`、`/dashboard`
- `purpose: any` 與 `purpose: maskable` 分開宣告

### iOS
- `apple-mobile-web-app-capable: true`、status bar 樣式、多尺寸 apple-touch-icon
- `format-detection.telephone: false`

### Service Worker
- Cache 名稱 `ims-v2`；install 時 precache `/offline`
- `/_next/static/*` cache-first
- Navigate 請求 network-first → fallback cache → `/offline`
- `/scan` 排除在 navigate cache 外（相機頁離線無用）

---

## 🌍 i18n（Phase 2）

- next-intl 處理訊息字典
- `messages/zh-TW.json` / `messages/en.json`
- Cookie `ims_locale` 存偏好（middleware 讀取並注入到 server components）
- 設定頁提供切換，自動呼叫 `/api/preferences` 同步到後端

---

## 🧪 測試

- **API**: pytest-asyncio + FastAPI TestClient + aiosqlite（每個 test 一個乾淨 in-memory DB）。398 passed。
- **Web**: vitest + @testing-library/react + jsdom。75 passed across 19 files。
- **TS**: `tsc --noEmit` 嚴格模式乾淨。

---

## ⚙️ 開發流程

1. 新功能開 worktree：`git worktree add .claude/worktrees/<name> -b claude/<name>`
2. API 側改 schema → 寫 alembic 遷移 → 更新 repository / service / route → 補測試
3. Regen api-types：`cd packages/api-types && node generate.mjs`
4. Web 側改 UI → 寫 vitest 測試 → 跑 typecheck
5. Commit、merge 回 main、push、清 worktree

詳見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。
