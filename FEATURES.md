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
- **位置（Locations）** — 樓層 / 房間 / 區域；`sort_order` 支援手動排序；可附樓層平面圖並在圖上標示子位置的區域（Phase 47）：`/locations/{id}/plan` 檢視時點區域即可看到該位置（含子孫）的物品；編輯時拖曳畫矩形或用鍵盤調整。區域存於子位置的 `plan_region`（相對父位置圖片的 0–1 矩形），搬移位置或移除圖片時由伺服器自動清除
- **倉庫（Warehouses）** — 跨實體場所隔離，`(owner_id, name)` 唯一
- **標籤（Tags）** — 多對多，同時支援物品間共用
- **自訂欄位（Custom Fields）** — `item_types` 定義某類物品有哪些自訂欄位；`item_templates` 定義預設值組合；每件物品可在 `custom_values` JSON 存值

---

## 📷 QR / 掃碼

### 產生（Phase 13）
- `GET /api/items/{id}/label.png` 直接回 PNG 標籤（QR + 物品名）
- 物品詳細頁「下載標籤」按鈕
- `/items/labels` 列印預覽頁，A4 多格佈局

### 伺服器端標籤 PDF（Phase 41）
- `GET /api/items/labels.pdf?ids=…&start=0`：A4 3×7＝21 張（63.5 × 38.1 mm），每張含 QR（既有深連結）、Code128、名稱（2 行內截斷）、短 id／數量、條碼數字
- `start` 0–20 可跳過前 N 格，重用印過一半的貼紙；`ids` 去重後 1–100 筆；任一筆不可見 → 404（全有全無）
- 內嵌 Noto Sans TC 子集（OFL 1.1），PDF 只嵌實際用到的字形；`reportlab` + `python-barcode`，無系統字型／poppler 相依
- `/items/labels` 頁「下載 PDF」按鈕，檔名 `item-labels-YYYYMMDD.pdf`；既有「列印」保留

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

## 🗓 定期報表（Phase 31 月報、Phase 42 週報）

- `reports` 表（`UNIQUE(user_id, period)`、JSON 快照）＋ migration 0023／0026；`period` 支援 `YYYY-MM` 與 `YYYY-Www`，`kind` 區分 `monthly`／`weekly`
- `report.monthly`：每月 1 日生成上一個完整月（Asia/Taipei）
- `report.weekly`：每週一生成上一個完整 ISO 週（週一至週日）；`report_weekly_enabled` **預設 false**，需在 `/settings/reports` 開啟「每週摘要」
- 兩者共用 payload：庫存現況、期間動態（新增／刪除／入出庫／借還／逾期）、30 天內到期與已過期、期初／期末估值、熱門分類／位置、`has_activity`
- 冪等：同使用者同期間僅一列；空月／空週仍建列但**不通知**；無可見物品不建列；逐使用者錯誤隔離
- 交付：站內 `report_ready`＋Email（zh-TW／en、fail-soft）；deep link `/reports/{id}`
- `GET /api/reports`（`generated_at DESC`、回傳 `kind`）／`GET /api/reports/{id}`（僅本人；他人 404）
- Web `/reports` 清單混合兩種報表（「週報」徽章＋日期範圍）、詳情依 `kind` 切換文案、空狀態分流；`/settings/reports` 兩個獨立開關
- `GET /api/jobs/{job_name}/status` 的 `thresholds.stale_after_hours`：`expiry-scan` 26h／`report.weekly` 170h／`report.monthly` 770h

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

## 🔗 Webhooks（Phase 10 + Phase 21 + Phase 44）

- 用戶於設定頁新增 HTTP endpoint + 選擇訂閱事件
- 支援事件：`item.created` / `item.updated` / `item.deleted`
- 派送時機：`items_service.create_item / update_item / delete_item` 主交易 commit 後
- HMAC-SHA256 簽章於 `X-IMS-Signature` header（計算方式 `HMAC(secret, body_bytes)`，hex digest）
- `webhook_deliveries` 表記錄每次派送 `status_code`、`response_excerpt`（前 500 字元）、`attempt`、`next_retry_at`
- Fail-soft：HTTP 失敗不 rollback 主交易，只在 delivery 表留下錯誤狀態

### 重試政策（Phase 21）
- 最多 5 次總嘗試（初次 dispatch + 4 次重試），失敗後 backoff 為 30s → 2min → 8min → 30min
- 成功條件：2xx status code。其餘（含網路錯誤）皆視為失敗並排程下一次
- 每次重試產生新的 delivery row（保留完整歷史），前一筆的 `next_retry_at` 清為 NULL
- `POST /api/webhooks/process-retries`：外部 scheduler/cron 觸發，處理所有到期重試；回傳 `{processed, succeeded, remaining}`
- `POST /api/webhooks/{id}/deliveries/{delivery_id}/retry`：擁有者手動重試單筆（繞過 backoff）
- 純函式 `is_success(status_code)`、`backoff_after(attempt)` 可直接單元測試

### 出站 URL 防護（Phase 44）
- **寫入時**（不做 DNS）：只收 http／https、必須有 host、拒絕 userinfo、IP 字面值須為全域位址、拒絕 `localhost`／`*.localhost`／`*.local`／`*.internal` 與十進位／八進位／十六進位／省略段 IPv4 寫法 → `422`（`detail[].msg` 含 `webhook_url_not_allowed`）
- **送出時**（每次投遞含重試）：解析 DNS，所有結果都須為全域位址（含 IPv4-mapped IPv6；封鎖 `::/96`、NAT64、6to4、Teredo）；被擋 → 不發請求，記失敗 delivery（`status_code=NULL`、excerpt `error: destination not allowed`）
- **釘 IP**：連到已驗證的 IP，`Host` 與 TLS SNI／憑證驗證仍用原 hostname；不跟隨 redirect、不讀環境 proxy；最多試 3 個位址
- `WEBHOOK_ALLOW_PRIVATE_HOSTS`（預設 `false`）：自架把 webhook 指向 LAN 服務時由營運者開啟；仍只允許 http／https、不跟隨 redirect
- 既有指向內網的 webhook 不刪除，下一次投遞被擋並留下失敗紀錄
- Web Push 訂閱 endpoint 同樣套用（要求 https、送出前檢查、禁止 redirect）；無法釘 IP，對 DNS rebinding 只有降低

---

## 🔑 API Tokens + 稽核（Phase 1；查詢台 Phase 39）

- Personal Access Tokens 前綴 `ims_pat_`，SHA-256 雜湊存放
- 原始 token 只在建立當下出現一次
- `audit_logs` 目前記錄 **13 種 action**（Phase 40 擴充、Phase 44 新增 `auth.logout_all`）：
  - 認證：`auth.login`／`auth.logout_all`／`auth.login_failed`（失敗只記既有帳號，同一帳號 10 分鐘內只記一次；陌生帳號不寫）
  - 物品：`item.deleted`（meta 記名稱）／`item.bulk_deleted`（一次操作 1 列，meta 記 `count` 與 `item_ids`）
  - 權杖：`token.created`／`token.deleted`（只記 `name`，不記原文或雜湊）
  - 帳號：`user.password_changed`／`admin.user.set_active`
  - 群組：`group.member_added`／`group.member_role_changed`／`group.member_removed`
  - 備份：`backup.import`
- `GET /api/admin/audit-logs`：篩選 `action`／`resource_type`／`user_id`／`q`（涵蓋 action／resource_type／resource_id／meta）／`created_from`／`created_to`；**分頁信封** `{items,total,limit,offset,facets}`；`user_email` 由 LEFT JOIN 取得
- `GET /api/admin/audit-logs/export.csv`：套用相同篩選、UTF-8 BOM、上限 10,000 列；公式起首字元會加 `'` 中和（CSV injection）
- `/settings/audit` 查詢台：動作／資源類型下拉（選項來自 facets）、關鍵字 300ms debounce、日期起訖、分頁、`meta` 展開、CSV 匯出；行動版卡片

---

## 🔐 認證與登入防護（Phase 43 + Phase 44）

- `POST /api/auth/login` 只對**失敗**計數；成功登入不新增紀錄，並清除該帳號的失敗列
- **帳號分級鎖定**（`username.strip()` 精確比對；未知帳號也照樣計數，避免帳號列舉）：
  - 5 次／15 分鐘 → 鎖 15 分鐘
  - 10 次／1 小時 → 鎖 30 分鐘
  - 15 次／24 小時 → 鎖 1 小時
- **來源 IP 分級鎖定**（`request.client.host`）：
  - 10 次／1 分鐘 → 鎖 1 分鐘
  - 30 次／15 分鐘 → 鎖 15 分鐘
  - 成功登入**不**清除 IP 計數（避免用已知密碼反覆重置）
- 被鎖時回 `429 too many login attempts`＋`Retry-After: <seconds>`；不執行密碼驗證。既有／未知帳號、帳號／IP 鎖定對外一致；既有錯誤仍為 `401 invalid credentials`
- 被封鎖的請求**不再寫入**，避免攻擊者持續延長受害者鎖定
- `login_attempts`（Migration 0027）：每次失敗寫 account／ip 兩列；`key_hash = HMAC-SHA256(jwt_secret, "kind:value")`，不保存原始名稱或 IP；每次失敗清理 24 小時前紀錄
- 未知帳號仍對固定 dummy Argon2 hash 驗一次密碼，降低 timing 帳號列舉
- 節流查詢／寫入／重置失敗採 fail-soft（log warning＋rollback），不讓登入變成 500
- **Proxy 信任邊界**：compose 的 uvicorn 以 `--proxy-headers --forwarded-allow-ips='*'` 取得 nginx 後方真實 IP；API 只 `expose` 對內。若直接暴露 API，必須移除此旗標或限制 proxy IP，否則來源 IP 可被偽造
- Web 登入表單對 `429` 顯示「嘗試次數過多，請稍後再試」，其餘維持「帳號或密碼錯誤」
- **不做**：CAPTCHA／MFA／WebAuthn、註冊／refresh／忘記密碼 rate limit、管理員解鎖 UI、Redis 滑動視窗、稽核原始 IP／User-Agent

### Session 撤銷（Phase 44）

- `users.token_version`（Migration 0028，預設 0）；access／refresh token 帶 `ver` claim，`get_current_user` 與 `/api/auth/refresh` 比對，不符 → `401 token revoked`；無 `ver` 的舊 token 視為 0
- `POST /api/users/me/change-password` 同一筆 commit 遞增版本，**重新簽發** `access_token`（回應新增 `access_token`、`token_type`，保留 `success`）並重設 refresh cookie → 目前裝置保持登入、其他裝置失效
- `POST /api/auth/logout-all`（需登入，204）：遞增版本、清 cookie、稽核 `auth.logout_all`；`POST /api/auth/logout` 仍只清目前裝置 cookie（該裝置 access token 最長再活 15 分鐘）
- Web `apiFetch` 遇 `401`（請求帶 token、路徑非 `/auth/*`）時 single-flight 呼叫 `/auth/refresh` 並重試一次；重試後仍 401 才清 store（修正原本 access token 15 分鐘到期即被踢回登入頁）
- 設定 → 密碼頁有「登出所有裝置」區塊（AlertDialog 確認）；改密碼成功會提示其他裝置已登出
- **PAT（`ims_pat_`）不受版本影響**，不因改密碼或登出所有裝置失效
- 認證依賴：JWT 用 `pyjwt`、密碼雜湊用 `argon2-cffi`（既有 `$argon2id$` 雜湊免遷移）；`JWT_SECRET` 建議 ≥32 bytes（`openssl rand -hex 32`）

---

## 📥 CSV 匯入 / 匯出（Phase 14 + Phase 19）

### 匯入
- `POST /api/items/bulk-import` multipart CSV
- Per-row 驗證，失敗不影響成功者
- 支援 `dry_run=true` 預覽：回傳將建立的筆數、會跳過的失敗列號 + 原因
- **關聯 auto-create**：`category_name` / `location_floor` · `location_room` · `location_zone` / `warehouse_name` / `tag_names` 查不到就建立，per-owner 隔離
- `tag_names` 以 `|` 分隔多個 tag，空白與重複會被 dedupe（例：`kitchen|kitchen| |kitchen ` → `kitchen`）
- 欄位對應：`name`（必）、`description`、`quantity`、`min_quantity`、`notes`、`category_name`、`location_floor` · `location_room` · `location_zone`、`warehouse_name`、`tag_names`

### 匯出
- `GET /api/items/export.csv` 串流 CSV（`text/csv; charset=utf-8`）
- 尊重 query 篩選，同 `GET /api/items` 規則
- `tag_names` 欄位輸出字母排序後、以 `|` 分隔
- 完整 round-trip：export → 新 owner import 會重建所有關聯（見 `test_import_roundtrip_preserves_tags`）

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

- **API**: pytest-asyncio + FastAPI TestClient + aiosqlite（每個 test 一個乾淨 in-memory DB）。**1455 passed**；golden eval **28 passed／1 skipped**；`ruff check` 零違規（`All checks passed!`）。
- **Web**: vitest + @testing-library/react + jsdom。**824 passed across 138 files**。
- **E2E**: Playwright chromium **91 passed／1 skipped**（`--workers=1`；Phase 46 實跑的 30 spec／96 情境含 ai-stub；Phase 47 另新增 `floor-plan.spec.ts` 3 情境，由 CI 執行）＋ ai-stub 4 passed。
- **TS**: `tsc --noEmit` 嚴格模式乾淨；`next build` 成功。
- Phase 44 新增 `session-security.spec.ts`（2 情境）並改寫 `webhooks.spec.ts`，已於全新 docker stack 實跑通過；skip 的 1 個情境是 `locations-tree.spec.ts` 的「真實遷移後的位置樹」依賴舊 dev 庫的 `phase26_demo` 遷移 fixture，全新資料庫不存在 → 改為明確 skip（原本會登入逾時失敗；與本期無關）。

---

## ⚙️ 開發流程

1. 使用現有 Python 3.13／uv 與 pnpm lockfile；`make install` 安裝。
2. API schema 異動時更新 migration／service／route 與測試，以 `make gen-types` 匯出 OpenAPI 並產生型別。
3. Web 異動補相關測試並跑 typecheck；`make lint` 檢查 API ruff（F＋E9）與 Web ESLint。
4. CI API gate 涵蓋 pytest、golden eval 與 PostgreSQL migration 升降版；e2e job 跑完整 Compose 的 chromium 與 ai-stub。
5. 部署使用非 root images、readiness healthcheck、request id 與結構化日誌、nginx CSP／條件式 HSTS；非 dev 預設關閉 API 文件頁。
6. commit、push、分支與部署依該次工作授權執行。

詳見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。
