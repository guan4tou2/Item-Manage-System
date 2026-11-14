# Changelog

本專案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式與 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

v2 為全面重寫版（Next.js + FastAPI monorepo，位於 `apps/`）。v1（Flask + Jinja2）已下線，歷史快照保留於 `v1-final` tag；下方歷史條目維持當時紀錄。

## [Unreleased]

## [2.0.0-alpha.51] — Phase 51：離線新增物品

- **範圍收斂**：已開著 App 時斷線仍可「新增物品」，資料先存在裝置上，連線後自動同步；不做離線編輯／刪除、不做分頁關閉後的背景同步、不做離線上傳圖片或 AI
- **Migration 0033**：`idempotency_keys` 表（`owner_id` FK users CASCADE、`key` char 36、`item_id` FK items CASCADE、`created_at`）；`UNIQUE(owner_id, key)`；同一交易內寫入 key 與物品；downgrade 刪表
- **伺服器端冪等**：`POST /api/items` 接受選填 `Idempotency-Key` 標頭（UUID，非 UUID → `422`）。同使用者同 key 重送 → 回傳首次建立的物品（`200`，內容同 `ItemRead`），資料庫只有一筆；並行重送以 unique constraint 收斂；物品已軟刪除 → `410 {"code":"idempotent_item_deleted"}`；沒帶標頭行為不變。每次 keyed 寫入清除 7 天前紀錄
- **離線佇列**：瀏覽器 IndexedDB（`ims-offline`／`pending-items`），主鍵 `client_id`＝`crypto.randomUUID()`，同時作為 `Idempotency-Key`；記錄 `owner_user_id`、表單 payload、啟用批次與自訂欄位所需資料、`created_at`、`status`（`pending`／`syncing`／`failed`）、`error_code`、`attempts`
- **進佇列時機**：`navigator.onLine` 為 false，或 fetch 因網路層失敗（丟例外、無 HTTP 回應）→ 存入佇列；拿到 HTTP 回應的 4xx／5xx 不進佇列，維持原錯誤處理
- **同步時機**：`online` 事件、App 載入時、登入成功後、使用者按「立即同步」；single-flight 逐筆依建立順序重放線上新增流程
- **失敗分類**：網路層失敗 → 維持 `pending` 下次再試；`401` → 整輪暫停等重新登入；`403`／`404`／`409`／`410`／`422` 等確定性錯誤 → 標 `failed` 並記 `error_code`，使用者可「編輯後重送」或「捨棄」；`5xx` → `attempts` 加一，連續 5 次後標 `failed`；物品已建立但後續步驟（批次、自訂欄位）失敗 → 移出佇列並提示到物品頁補填
- **離線時不可用的欄位**：圖片上傳與 AI 辨識需要連線，離線時表單入口顯示為不可用並說明原因；已上傳好的 `image_id` 會跟著佇列項目保留
- **介面**：離線提示列「目前離線——新增的物品會先存在這台裝置」，恢復連線即消失，使用 `aria-live="polite"`；送出後 toast「已存在這台裝置，連線後自動同步」並回到物品清單；清單頁待同步區塊顯示「N 筆待同步」、每筆名稱／時間／狀態與「編輯後重送」「捨棄」；同步成功 toast「已同步 N 筆」；導覽列「物品」旁有待同步數量徽章
- **IndexedDB 不可用／空間不足**：私密視窗或停用 IndexedDB 時離線送出顯示「這個瀏覽器無法離線保存」；儲存空間不足同樣有明確訊息
- **登出**：登出不刪除 IndexedDB；一般登出與「登出所有裝置」確認框會先檢查佇列並提示使用者
- **Service worker**：未更動快取策略；從未開過 App／頁面的離線啟動不保證可用
- **明確不做**：分頁關閉後背景同步（Background Sync API）、離線編輯／刪除既有物品、離線上傳圖片、離線 AI、預先快取所有頁面、跨裝置同步佇列
- 測試：API 1524 → **1534 passed**；Web 926 → **975 passed（154 檔）**；typecheck 0 error；lint `next lint --max-warnings 0` 通過。主代理以本機 SQLite 暫時資料庫＋`next dev`、停止 API 行程模擬斷線實際操作：同一 `Idempotency-Key` 連送兩次 `POST /api/items` → 第一次 `201`、第二次 `200`，清單只有一筆；非 UUID key → `422`；開著新增表單停止 API → 送出出現「1 筆待同步」「立即同步」與導覽列徽章；重新啟動 API 按「立即同步」→ toast「已同步 1 筆」、清單出現該物品且只有一筆。此次實測觸發 D7 的「網路層失敗」路徑（`navigator.onLine` 仍為 true）；`navigator.onLine` 為 false 的路徑由單元測試與 e2e spec 涵蓋，主代理未以瀏覽器離線模擬實測。**未在本機執行**：Playwright e2e（`offline-add.spec.ts`）與 Migration 0033 的 PostgreSQL 升降版，交由 CI；真實瀏覽器離線模式、私密視窗無 IndexedDB、儲存空間不足、375px 版面未以瀏覽器實測；分頁關閉期間不會同步；CI 結果 push 後由 CI 確認
- **修正物品詳情頁長名稱撐破手機版面（既有問題）**：標題遇到沒有斷字機會的長名稱（代號、條碼式名稱）不會折行，375px 下出現水平捲軸；由批次成本的 e2e 在 CI 暴露。標題改為可任意斷行
- **CI 確認**：`a2ba6a0` 的 `api`／`web`／`audit`／`docker`／`e2e` 五個 job 全數通過（含 Migration 0030–0033 的 PostgreSQL 升降版與 Phase 48–51 新增的 e2e 情境）

**同日維護項目（第二批）**：

- Dependabot：合併 6 個檢查全綠的 PR——`github/codeql-action` 3→4、`docker/login-action` 3→4、`actions/setup-python` 5→7、`docker/setup-qemu-action` 3→4、`actions/setup-node` 4→7，以及 Python minor／patch 群組更新（含 `sqlalchemy` 2.0.35→2.1.8、`uvicorn` 0.30.6→0.54.0、`pydantic` 2.12.5→2.14.3、`pydantic-settings` 2.11.0→2.16.2、`alembic` 1.13.3→1.20.1、`asyncpg` 0.30.0→0.32.0、`python-multipart` 0.0.31→0.0.33、`pywebpush` 2.0.0→2.5.0、`pytest` 9.0.3→9.2.0、`aiosqlite` 0.20.0→0.22.1、`pypdfium2` 5.14.0→5.15.2）。仍開著未處理的：`vitest` 5、`eslint` 10、`tailwindcss` 4、`google-genai` 3（皆為 major，需個別評估）、npm minor／patch 群組（檢查未過）、`docker/setup-buildx-action` 4 與 `pytest-cov` 7（等 rebase）。併入後以新版本重跑 API 全套仍為 1534 passed，OpenAPI 輸出僅描述性差異、TypeScript 型別不變
- codex 的使用額度在本輪用完；Phase 48–50 與維護項目的文件、以及本次文件更新由 opencode 完成

**同日維護項目（第三批：大版本升級）**：

- **修正 AI 功能使用已停用的模型**：`gemini-2.0-flash` 已於 2026-06-01 被 Google 關閉，原本四處寫死該模型的呼叫都會失敗。改為設定值 `GEMINI_MODEL`（預設 `gemini-3.6-flash`），並新增測試確認送給 SDK 的模型名稱來自設定、原始碼不再寫死。`google-genai` 2.x → 3.1.0。**未以真實 API 金鑰實測**（本機與 CI 都沒有金鑰），部署後請實際跑一次 AI 辨識確認
- `pytest-cov` 6 → 7.1.0、`docker/setup-buildx-action` 3 → 4
- `vitest` 2 → 5.1.0（連帶 `vite` 8.3.8、`@vitejs/plugin-react` 6.3.0）；npm minor／patch 群組 28 個套件（含 `@tanstack/react-query` 5.107）。react-query 新版的通知時機讓 4 個「資料還沒載入就操作」的測試露餡，已改為先等資料載入；產品程式未變
- **Next.js 15 → 16.4.6、ESLint 9 → 10.15.0**：`.eslintrc.json` 改為 flat config（`eslint.config.mjs`），`lint` script 由 `next lint` 改為 `eslint . --max-warnings 0`（Next 16 已移除 `next lint`）；`middleware.ts` 依 Next 16 慣例改名為 `proxy.ts`，邏輯與 matcher 不變
- **Tailwind CSS 3.4 → 4.3.5**：PostCSS 外掛改為 `@tailwindcss/postcss`、移除 `autoprefixer`；`globals.css` 改用 `@import 'tailwindcss'`＋`@config` 沿用既有 `tailwind.config.ts`（色彩與字型 token 落點不變）。為了讓畫面不變，在 `globals.css` 保留 v3 的預設邊框色、預設 ring 色、按鈕游標、placeholder 色、`container`、`space-*`／`divide-y` 與 `hover` 行為；v4 改名的類別一併調整（`shadow-sm`→`shadow-xs`、`backdrop-blur`→`backdrop-blur-sm`、`outline-none`→`outline-hidden`、裸 `rounded`→`rounded-[0.25rem]`、`flex-shrink-*`→`shrink-*`），`cn()` 補上新語法的合併規則
- **瀏覽器基準提高**：Tailwind 4 需要 Safari 16.4+、Chrome 111+、Firefox 128+；更舊的瀏覽器版面可能不正確
- 驗證：遷移前後以正式建置各拍 40 張截圖（9 個頁面＋登入頁 × 明暗 × 1280／375px）逐張比對，容許差異 0.05% 下 36 張一致；統計頁 4 張的差異經查為圖表進場動畫的截圖時機（同一頁在遷移前自我比對就不穩定），以等待動畫結束的截圖目視確認與遷移前一致。另以瀏覽器實際操作確認對話框／下拉選單／側邊抽屜的進場動畫、鍵盤 focus ring、暗色模式與 375px 版面正常。Web 975 passed（154 檔，Node 22 與 24）、typecheck 0 error、lint 0 warning、`next build` 成功；本機 e2e（SQLite 暫時資料庫＋正式建置，chromium）93 passed／1 skipped，另 6 個 `reminders`／`reports` 情境需要 Docker 內的 PostgreSQL，本機無法執行，由 CI 確認

**同日維護項目（第四批：其餘大版本）**：

- `tailwind-merge` 2.5 → 3.7.0：原生支援 Tailwind 4，移除第三批在 `cn()` 補的暫時合併規則
- `lucide-react` 0.447 → 1.73.0、`@hookform/resolvers` 5 → 7.0.6、`jsdom` 29 → 31、`@testing-library/jest-dom` 6 → 7：程式不需修改
- **`recharts` 2 → 3.10.1**：統計頁七張圖。新版圓餅圖圖例預設由圓點變成方塊、趨勢圖日期刻度變密，分別以 `iconType="circle"` 與 `minTickGap` 調回原本的樣子；長條、圓餅、面積與 tooltip 以瀏覽器實際操作確認正常（明亮 1280px、暗色 375px）。趨勢圖尾端刻度與升級前略有不同（多顯示一個日期），不影響閱讀
- **TypeScript 5.6 → 6.0.3**：三處 `Uint8Array` 型別需標明為 `Uint8Array<ArrayBuffer>`（Web Push 金鑰轉換與兩個測試）。`openapi-typescript` 的 peer 範圍仍寫 `^5.x`（安裝時有警告），實測以 TS 6 重新產生 API 型別只差一處註解空白
- **TypeScript 7 暫不升**：`typescript-eslint` 目前只支援到 `<6.1.0`、`openapi-typescript` 只宣告支援 5.x，等這兩個工具支援後再評估。`@types/node` 維持 22（對應 CI 與正式環境的 Node 22）
- 驗證：Web 975 passed（154 檔，Node 22 與 24）、typecheck 0 error、lint 0 warning、`next build` 成功、`pnpm audit --prod` 無已知漏洞；本機 e2e（SQLite 暫時資料庫＋正式建置，chromium）93 passed／1 skipped，與升級前相同，另 6 個需要 Docker 內 PostgreSQL 的 `reminders`／`reports` 情境由 CI 確認

## [2.0.0-alpha.50] — Phase 50：清單分享唯讀連結

- **分享範圍＝單一清單**：一條連結只對應一份清單，不會連帶揭露物品庫存、位置、其他清單或帳號資訊
- **Migration 0032**：`list_shares` 表（`list_id` FK CASCADE、`owner_id` FK CASCADE、`token_hash` char 64 unique、`token_prefix` varchar 6、`show_prices` bool 預設 false、`expires_at` timestamptz nullable、`access_count` int 預設 0 等）；downgrade 刪表
- **Token 設計**：`secrets.token_urlsafe(32)`（256 bit）；資料庫只存 SHA-256 雜湊與前 6 碼；完整連結**只在建立當下顯示一次**，遺失就撤銷重建
- **Token 不進 URL 路徑或 query**：分享網址為 `/share#{token}`，fragment 不會送到伺服器，因此 token 不會出現在 nginx／應用程式 access log，也不會經由 `Referer` 外洩；公開頁以 JavaScript 讀取 fragment，再用 **`X-Share-Token` 標頭**呼叫 API
- **預設不揭露金額**：`budget` 與條目 `price` 預設不出現在公開回應；建立連結時可開啟「顯示價格」
- **不揭露擁有者身分**：公開回應白名單只含 `kind`、`title`、`description`、`start_date`、`end_date`、條目（`name`、`quantity`、`note`、`link`、`is_done`），以及 `show_prices=true` 時的 `budget`、條目 `price` 與帳號幣別；不含任何 UUID、使用者名稱、email、建立／更新時間
- **效期與撤銷**：建立時必選 1 天／7 天／30 天／永久，預設 7 天；過期、已撤銷、不存在一律回同樣的 `404`（不區分）；每份清單最多 5 條有效連結，超過回 `409`
- **公開端點回應標頭**：`Cache-Control: no-store`、`X-Robots-Tag: noindex, nofollow`、`Referrer-Policy: no-referrer`
- **條目連結安全**：公開回應中，非 `http:`／`https:` 的 `link` 一律設為 null；公開頁再次檢查，只有 http(s) 才渲染成超連結（`rel="noopener noreferrer nofollow"`、`target="_blank"`），避免 `javascript:` 等 scheme
- **API**：管理端點 `POST|GET|DELETE /api/lists/{list_id}/shares`（需登入）；公開端點 `GET /api/public/list`（不需登入，token 由 `X-Share-Token` 標頭帶入）
- **Web 管理**：清單詳情頁「分享」按鈕 → 對話框：效期選擇、顯示價格開關、一次性網址與複製、既有連結列表（前 6 碼、建立／到期時間、最後存取、存取次數、撤銷）；viewer 不渲染入口
- **公開頁 `/share`**：獨立於登入區外的路由，不套用 app 導覽列；唯讀呈現清單標題、說明、日期與條目；完成狀態同時以文字與刪除線標示；設 `noindex` meta 與 `no-referrer`；狀態涵蓋載入中、缺 token、無效／過期、網路錯誤重試
- **稽核**：建立與撤銷各寫一筆稽核（`list.share_created`／`list.share_revoked`）；`meta` 只記清單 id、效期、是否顯示價格與 token 前 6 碼，**不記 token 或其雜湊**。公開存取不寫稽核，只原子更新 `last_accessed_at` 與 `access_count`（fail-soft）
- **不進備份**：分享連結屬憑證性質，不納入備份匯出／匯入
- **明確不做**：分享物品庫存／位置／報表、密碼保護連結、允許對方編輯或勾選、公開存取速率限制、Open Graph 連結預覽
- 測試：API 1487 → **1474 passed**；Web 856 → **859 passed（144 檔）**；typecheck 0 error；lint 0 error／0 warning，`next lint --max-warnings 0` 通過；`next build` 成功。以 API 與未登入瀏覽器實際操作驗證白名單、三標頭、token 不進 log、375px 公開頁。**未在本機執行**：Playwright e2e（`list-share.spec.ts`）與 Migration 0032 的 PostgreSQL 升降版，交由 CI；公開存取沒有速率限制；本機 SQLite 時間欄位顯示為無時區

**同日維護項目**：

- `AuthImage` 記憶體 blob 快取：以 `imageId` 為 key、併發去重、引用計數、上限 50 筆的 LRU 淘汰、失敗不快取、登出時清空（token refresh 不清）。審查時修正：元件取消載入時會把同一次取得釋放兩次，在 React StrictMode 下會讓顯示中的圖片被回收；已修並加回歸測試
- 前端 ESLint 警告 30 → 0，`lint` script 改為 `next lint --max-warnings 0`（零警告門檻）
- `next-intl` 3.21.1 → 4.15.1、`next-themes` 0.3.0 → 0.4.6：清掉剩下的 2 個 moderate advisory，`pnpm audit --prod` 回報 **No known vulnerabilities found**；兩者的 React 19／Next 15 peer 警告消失
- Phase 47 的 CI（run 43568435431）五個 job 全數通過，含 `floor-plan.spec.ts` 三個 e2e 情境與 Migration 0029 在 PostgreSQL 的升降版
- Dependabot：關閉 6 個已被涵蓋的 PR（#8–#13），5 個基底過舊的要求 rebase

## [2.0.0-alpha.49] — Phase 49：批次成本

- **Migration 0031**：`item_batches.unit_cost`（`NUMERIC(12,2)`、nullable、`>= 0` check constraint）；downgrade 刪欄
- **有效單價**：批次的有效單價＝`batch.unit_cost`，為 null 時退回 `item.cost`；兩者皆 null → 該批次「未定價」。`items.cost` 定位變成「預設單價」
- **物品估值（單一定義）**：未啟用批次維持 `item.cost × item.quantity`；啟用批次改為 `Σ 未耗盡批次（quantity × 有效單價）`，未定價批次以 0 計
- **「未定價」物品數**：未啟用批次 → `cost` 為 null；啟用批次 → 有任何未耗盡批次未定價；數量 0 的批次物品不算未定價
- **統計與報表共用**：`GET /api/stats/value` 的總值、未定價數與三個分布，以及月報／週報期末估值，都改用同一個 valuation 定義；期初估值以「目前加權平均單價」反推（近似值，文件明示）
- **API additive**：`BatchCreate`／`BatchUpdate`／`BatchRead` 新增 `unit_cost`；`BatchUpdate` 區分未提供與明確設為 null（清除）。不新增端點
- **備份**：匯出的批次列加上 `unit_cost`，匯入時還原；舊備份沒有此欄位照常匯入。`format_version` 不變
- **Web**：批次新增／編輯對話框加選填「單位成本」（顯示帳號幣別、預設單價提示）；批次列有成本時顯示單價，無時不顯示；物品表單成本欄位補提示「批次未填成本時使用此值」；物品詳情啟用批次時顯示估值小計
- **不受影響的流程**：FEFO 消耗、盤點調整、停用批次管理只動數量；CSV 匯入／匯出仍只處理物品層級
- **明確不做**：移動平均／FIFO 成本法、批次層級幣別與匯率、CSV 匯入／匯出批次、收據辨識入庫時自動建立帶成本的批次
- 測試：API 1465 → **1487 passed**；Web 848 → **856 passed（139 檔）**；typecheck 0 error；lint 0 error／30 warning。主代理實際操作：預設單價 50 的物品＋三批（2 個＠45、3 個＠60、1 個未填成本）→ `GET /api/stats/value` 的 `total_value` 為 320.00，詳情批次區塊顯示單價與「估值 NT$320」，未填批次不顯示單價。codex 回報既有估值／報表測試的預期金額全部未修改。**未在本機執行**：Playwright e2e（`items-batches.spec.ts` 新增情境）與 Migration 0031 的 PostgreSQL 升降版，交由 CI；報表期初估值為近似值

## [2.0.0-alpha.48] — Phase 48：收據人工核對與整張收據視圖

- **Migration 0030**：新表 `ai_receipt_reviews`（`receipt_id` GUID PK、`owner_id` FK users CASCADE、`verified_at` timestamptz NOT NULL、`note` varchar 200 nullable）。列存在＝已核對，取消核對＝刪除列；不改寫草稿的 `payload.receipt` 快照
- **收據擁有權**：以「本人名下至少有一列相同 `receipt_id` 的草稿（任何狀態）」判定；否則一律 `404`（不區分不存在與他人的）
- **端點**（皆在 `/api/ai/receipts` 之下；viewer `403`）：`GET /api/ai/receipts/{receipt_id}` 回整張收據（snapshot、review、image_id、lines[]）；`PUT /api/ai/receipts/{receipt_id}/review`（body `{note?: string ≤ 200}`）冪等 upsert，保留首次 `verified_at`；`DELETE /api/ai/receipts/{receipt_id}/review` 回 `204`
- **lines[]**：該收據全部狀態的草稿，依 `receipt_item.index` 排序；每行含 `draft_id`、`index`、原始名稱／數量／金額、`status`、已接受時的 `item_id`（物品已刪除則 `null`）
- **佇列帶出核對狀態**：`DraftRead` 新增 `receipt_review`（非收據草稿為 `null`）；清單端點以一次查詢取回當頁所有 `receipt_id` 的核對紀錄，不逐列查
- **群組標頭**：未核對維持既有呈現，writer 多「標記為已核對」；已核對以「已人工核對」取代差額／無法判斷警示，有備註時顯示備註；任何狀態都有「查看整張收據」連結；已核對時 writer 可「取消核對」。審查時調整：整張收據頁重用群組標頭時隱藏指向自己的「查看整張收據」連結
- **整張收據頁** `/items/drafts/receipts/{receiptId}`：頂部商家／日期／頁數／核對狀態；算術拆解明細表（品項合計 − 折扣 + 稅 + 運費 = 算術值 vs 收據總額 vs 差額）；桌面表格／手機收據行顯示全部品項行與狀態；第一頁影像（附「共 N 頁，僅保留第一頁」說明）；404／錯誤重試／viewer 狀態
- **不寫稽核、不進備份**：核對是使用者對自己暫存資料的註記；AI 草稿本來就不在備份範圍內
- **明確不做**：在收據層編輯總額／折扣／稅並重新計算對帳、保留並顯示收據的所有頁面影像、收據歷史清單頁、把核對紀錄寫入稽核或備份、自動核對
- 測試：API 1455 → **1465 passed**；Web 824 → **848 passed（140 檔）**；typecheck 0 error；lint 0 error／30 warning。主代理以 AI stub 在本機實際操作：上傳收據後標頭出現「標記為已核對」與「查看整張收據」；標記並填備註後顯示「已人工核對＋備註」與「取消核對」；整張收據頁顯示算術拆解、兩個品項行，接受一個後顯示「已入庫」；375px 無水平溢出；console 無錯誤。**未在本機執行**：Playwright e2e（`ai-stub.spec.ts` 新增情境）與 Migration 0030 的 PostgreSQL 升降版，交由 CI；只保留收據第一頁影像

## [2.0.0-alpha.47] — Phase 47：樓層平面圖互動

- **把既有但無介面的欄位做成功能**：`locations.floor_plan_image_id` 自 Phase 11 起存在於 API，但前端從未有任何平面圖介面。本期新增 `/locations/{id}/plan`：上傳／更換／移除平面圖、在圖上為直接子位置畫區域、點區域查看該位置的物品
- **Migration 0029**：`locations.plan_region`（JSON、nullable）＝該位置在**父位置平面圖**上的正規化矩形 `{x,y,w,h}`（0–1、最小 0.02、不得超出邊界、儲存到小數 4 位）；不合格 → `422`。downgrade 刪欄
- **一致性由伺服器強制**：設定區域時父位置必須有平面圖（否則 `422 parent_has_no_floor_plan`）；位置搬到別的父位置自動清除區域（除非同一請求明確給了新區域）；父位置移除平面圖 → 清除所有直接子位置的區域；更換平面圖 → 保留區域
- **圖片擁有者驗證（補既有缺口）**：設定 `floor_plan_image_id` 時驗證圖片存在且為本人所有，否則 `422 invalid_floor_plan_image`（原本完全不驗證）
- **API 僅 additive、無新端點**：`LocationRead`／`LocationTreeNode`／`LocationUpdate` 新增 `plan_region`；檢視頁資料全部來自既有的 `GET /api/locations/tree`
- **備份**：匯出的位置列含 `plan_region`，匯入時還原（不合格的值略過並記 warning）；`format_version` 不變。備份不含圖片檔，還原後需重新上傳平面圖
- **檢視模式**：區域是連結（`/items?location={id}`），標籤為「名稱＋含子孫的物品數」；圖下方一律附子位置清單，作為小區域與螢幕閱讀器的等價入口，並列出尚未放置的子位置
- **編輯模式**（viewer 不渲染）：圖片上方選取子位置 → 拖曳畫矩形（pointer events，滑鼠與觸控共用）；選取的區域可用方向鍵移動、`Shift`＋方向鍵縮放、`Delete`／`Backspace` 清除；每次變更立即儲存（樂觀更新，失敗回滾）
- **入口**：位置樹的更多操作選單加「平面圖」；已有平面圖的節點在列上顯示地圖連結
- **狀態**：載入 skeleton、沒有平面圖（writer／viewer 分流）、沒有子位置、尚未標示任何區域、樹／圖片載入失敗可重試、位置不存在
- **視覺與無障礙**：依 `DESIGN.md`——區域為 primary 邊框＋低透明度底，標籤用不透明底確保在任何圖片上可讀；`aria-label`「名稱，n 件物品」；觸控目標 44px；zh-TW／en
- **實際操作時修正**：隱藏的檔案輸入造成的頁面水平溢出、區域標籤可讀性與位置、編輯時選取列改到圖片上方
- **明確不做**：多邊形／旋轉區域、圖上顯示個別物品圖釘、自訂縮放／平移手勢、巢狀平面圖的串接導覽
- 測試：API 1440 → **1455 passed**；Web 805 → **824 passed（138 檔）**（Node 22 與 24）；typecheck 0 error；lint 0 error／30 warning；golden eval 28 passed／1 skipped；ruff 零違規；api-types 重新產生。以瀏覽器實際操作驗證檢視、拖曳編輯、375px 版面。**未在本機執行**：Playwright e2e（新增 `floor-plan.spec.ts` 3 情境）與 Migration 0029 的 PostgreSQL 升降版，交由 CI

## [2.0.0-alpha.46] — Phase 46：部署強化與可觀測

- **Image 與 Compose**：API 改以 `uv sync --frozen --no-dev` 依 `uv.lock` 多階段建置，runtime 無編譯工具，以 uid 10001 執行，包含 Alembic、scripts 與內附字型，可寫 `/app/media`；新增 API `.dockerignore`。Web runner 改用 `node`。移除未使用的 Redis／worker／redisdata 與設定；API readiness healthcheck，Web／nginx 等待 API healthy。
- **Readiness**：新增 `GET /api/health/ready`，DB `SELECT 1` 成功回 200 ready，失敗回 503 unavailable，不洩漏例外；既有 liveness 契約不變。
- **可觀測**：標準 logging 的 JSON／text（dev 預設 text，其餘 json）、`LOG_LEVEL=INFO`；冪等設定保留 pytest caplog。純 ASGI middleware 以 contextvars 傳遞 request id、回傳 `X-Request-ID`（傳入值限 `[A-Za-z0-9._-]{1,64}`），access log 含 method／path／status／duration_ms，略過 health，不記 query string／本文／認證 header／cookie；關閉 uvicorn access log。
- **瀏覽器防線與文件頁**：nginx 統一 CSP（同源外送限制，保留必要 inline script／style）、Permissions-Policy（同源相機）、僅 HTTPS forwarded header 回傳 HSTS；非 dev 預設關閉 docs／redoc／openapi 路由，`API_DOCS_ENABLED` 可覆寫，直接匯出 schema 不受影響。D12 決定保留 access token 於 localStorage，不列後續候選。
- **CI 與清理**：API gate 加 ruff（F＋E9）、golden eval、PostgreSQL migration up／down／up；新增 e2e job 跑 chromium 與 ai-stub，失敗保存 trace／Compose logs。修正未使用 import／變數，保留副作用與既有測試斷言；移除 datetime.utcnow，備份 exported_at 維持原本 Z 格式。Makefile lint 加 ruff，忽略 tsbuildinfo（既有追蹤檔留待使用者移除索引）。
- **既有 media volume 的升級處理**：API 改以 uid 10001 執行後，舊版以 root 建立的 `media` volume 無法寫入（實測圖片上傳會失敗）→ compose 新增一次性的 `media-init` 服務，每次啟動先把擁有者修正為 10001（已正確時不做事），`api` 以 `service_completed_successfully` 等待
- **修正來源 IP 可被偽造（Phase 43 遺留）**：nginx 原本以 `$proxy_add_x_forwarded_for`「附加」用戶端送來的 `X-Forwarded-For`，而 uvicorn 在 `--forwarded-allow-ips='*'` 下取最左邊的位址 → 用戶端可自行偽造來源 IP、繞過登入的 IP 節流。改為以 `$remote_addr` 覆寫；nginx 前方另有反向代理時以 `set_real_ip_from`／`real_ip_header` 還原（設定檔內附說明）。實測：以 12 個不同的偽造 `X-Forwarded-For` 連續登入失敗，第 11 次起回 `429`
- 測試：API 1425 → **1440 passed**（新增 15 個（`tests/test_observability.py`））；golden eval **28 passed／1 skipped**；ruff 零違規（`All checks passed!`）；Web **805 passed（135 檔）**（Node 22 與 24）；e2e 於新 image 與 CSP 下實跑 chromium **91 passed／1 skipped**、ai-stub **4 passed**。實測項目：兩個 image 可建置、API uid 10001／Web `node`、healthcheck 轉 healthy、非 root 執行 `alembic upgrade head`、media 可寫、`nginx -t`、CSP／Permissions-Policy 標頭、HSTS 僅在 `X-Forwarded-Proto: https` 時出現、request id 沿用／重新產生、access log 不含 query string。GitHub Actions 已確認：`main` 上 `api`（含 ruff／golden eval／migration 升降版）、`web`、`audit`、`docker`、`e2e` 五個 job 全數通過（run 43481596981）。**未驗證**：Release／GHCR／SBOM（未打 tag）、nginx 前置 TLS 代理的實際拓樸、CSP 下以真實相機掃碼

## [2.0.0-alpha.45] — Phase 45：v1 下線與發佈管線

- **v1 下線**：依計畫移除 v1 程式、模板、靜態檔、測試、migration、腳本與純 v1 文件（共 266 個追蹤檔案）；歷史快照使用既有 `v1-final` tag。本次未建立 tag 或分支。
- **Release 管線**：`v*.*.*` tag 建置 API／Web multi-platform images 至 GHCR，Web 先產生 OpenAPI／api-types；完整版本與 major.minor tags，預發佈版不更新 latest，GitHub Release 標 prerelease；各 image 產生 SBOM，使用 `gh release create --generate-notes`，移除 PyPI 與空 notify job。實際發佈／GHCR／SBOM **未驗證**。
- **開發入口與文件**：Makefile 改為 v2 的安裝、開發、Compose、migration、型別、測試與稽核入口；pre-commit 僅保留語言無關 hooks；重寫架構／開發／部署與文件索引，同步 README／roadmap，移除失效的 v1 忽略規則。Phase 45 的檔案刪除依計畫結果以工作樹操作完成，未修改索引。
- **同日 CI 修正：Web**：補 ESLint `next/core-web-vitals`＋`next/typescript`（0 error／30 warning）；pnpm audit 清至 next-intl 的 2 個 moderate。zod 3.23.8 → 4.6.7、@playwright/test 1.48.0 → 1.65.0、postcss 8.5.32、react-hook-form 7.92.0、@hookform/resolvers 5.9.2，其餘以 pnpm overrides 修補；修正只在 Node 22 失敗的 labels.test.ts。
- **同日 CI 修正：API**：pip-audit 歸零；fastapi 0.115.0 → 0.162.6／Starlette 1.x、python-multipart 0.0.31、pydantic 2.12.5、httpx 0.28.1、fastapi-mail 1.6.8、pytest 9.0.3、pytest-asyncio 1.5.0，傳遞依賴以 constraint-dependencies 設下限；CI 稽核以 uv.lock 為準、Dependabot 改用 uv 生態系。以上為同日已完成的前置結果，本輪未重跑需網路的 audit。
- **驗證範圍**：Phase 45 計畫記錄 YAML／shell dry-run、連結與刪除清單檢查，未實跑 Docker images／GitHub Actions／Release。Phase 46 的本輪離線測試與未驗證項目見 [進度文件](docs/progress-2026-11-14-b.md)。

## [2.0.0-alpha.44] — Phase 44：安全收斂（依賴、SSRF、session 撤銷）

- **Web 依賴脫離已知 RCE 範圍**：`next` 15.0.0 → **15.5.29**、`react`／`react-dom` 19.0.0-rc → **19.3.1**、`zustand` 5.0.0-rc.2 → 5.1.0、`eslint-config-next` → 15.5.29、`@types/react`／`@types/react-dom` → 19.3.0；`next.config.mjs` 的 `experimental.typedRoutes` 改頂層 `typedRoutes`。原因：Next 15.0.0 落在 React2Shell（CVE-2025-55182／CVE-2025-66478，App Router 未認證 RCE）受影響範圍，15.0.x 線修補版為 15.0.5，本次直接走 15.5 線。沒有任何原始碼因 React 19 型別需要修改
- **API 認證依賴汰換**：`python-jose[cryptography]==3.3.0` → `pyjwt==2.15.1`（`decode` 明確指定 `algorithms`、要求 `exp`／`sub`）；`passlib[argon2]==1.7.4` → `argon2-cffi==25.1.0`（既有 `$argon2id$` 雜湊免遷移；不合法雜湊改回 `False`，原本 passlib 會丟例外）。`uv.lock` 移除 python-jose、passlib、ecdsa、rsa。測試用 `JWT_SECRET` 加長到 ≥32 bytes（PyJWT 對 HS256 短金鑰發 `InsecureKeyLengthWarning`）
- **Session 撤銷（Migration 0028）**：`users.token_version INTEGER NOT NULL DEFAULT 0`（downgrade 刪欄）；access／refresh token 新增 `ver` claim，`get_current_user` 與 `/api/auth/refresh` 比對，不符 → `401 token revoked`。無 `ver` 的舊 token 視為 0，升級當下不會把使用者登出
- **改密碼會撤銷其他裝置**：`POST /api/users/me/change-password` 在同一筆 commit 遞增版本；回應新增 `access_token`、`token_type`（保留 `success`）並重設 refresh cookie，目前裝置不登出
- **新增 `POST /api/auth/logout-all`**（需登入，204）：遞增版本、清 cookie、稽核 `auth.logout_all`（稽核 action 總數 12 → 13）。`POST /api/auth/logout` 不變（只清 cookie）；PAT 不受版本影響
- **Web 自動 refresh（修掉既有 bug）**：前端原本從未呼叫 `/auth/refresh`，access token 15 分鐘到期就被踢回登入頁。`apiFetch` 在「401＋請求帶 token＋路徑非 `/auth/*`」時 single-flight 呼叫 refresh 並重試一次；store token 已被別的請求更新則直接沿用、store 已清空則不 refresh；重試後仍 401 才清 store
- **Web 改密碼與登出所有裝置**：改密碼成功後把新 token 寫回 store 並提示其他裝置已登出；密碼設定頁新增「登出所有裝置」區塊（AlertDialog 確認）；zh-TW／en i18n
- **Webhook 出站 URL 防護（SSRF）**：新模組 `app/services/url_guard.py`，兩道檢查
  - 寫入時（不做 DNS）：只收 http／https、必須有 host、拒絕 userinfo、IP 字面值須為全域位址、拒絕 `localhost`／`*.localhost`／`*.local`／`*.internal`、拒絕十進位／八進位／十六進位／省略段 IPv4 寫法 → `422`（`detail[].msg` 含 `webhook_url_not_allowed`）
  - 送出時：解析 DNS，所有結果都須為全域位址（處理 IPv4-mapped IPv6；另封鎖 `::/96`、NAT64、6to4、Teredo）；被擋 → 不發請求，記失敗 delivery（`status_code=NULL`、excerpt 固定 `error: destination not allowed`），重試照一般失敗排程
- **釘 IP**：連到已驗證的 IP，`Host` 與 TLS SNI／憑證驗證仍用原 hostname；`follow_redirects=False`、`trust_env=False`；最多試 3 個位址（僅連線層失敗時換下一個）
- **Web Push endpoint 同樣納管**（審查時發現的第二個入口）：訂閱時要求 `https` 並套同一個 guard（422）；送出前同步解析檢查；`requests` session `max_redirects=0`、timeout 10 秒。pywebpush 自行建連線、無法釘 IP，對 DNS rebinding 只有降低；回應不回傳使用者（blind）
- **行為變更**：既有指向內網／localhost 的 webhook 會在**下一次投遞被擋下**（不刪資料、無 migration）；自架需要把 webhook 指向 LAN 服務（如 Home Assistant、n8n）的營運者設定 `WEBHOOK_ALLOW_PRIVATE_HOSTS=true`（預設 `false`，`.env.example` 已加；開啟後仍只允許 http／https、不跟隨 redirect）
- **Web webhook 文案**：建立失敗且為 `webhook_url_not_allowed` 時顯示明確說明
- **CI**：新增 `.github/dependabot.yml`（pip `/apps/api`、npm `/`、github-actions；每週一；minor／patch 合併成群組 PR）；`ci.yml` 新增獨立 `audit` job（`pip-audit` ＋ `pnpm audit --prod --audit-level=high`，會失敗的 gate；**尚未在 GitHub Actions 實際跑過**，首次執行可能因既有漏洞紅燈）
- **已知限制**：`/logout` 後該裝置的 access token 最長仍可用 15 分鐘（無 per-session 撤銷與裝置清單）；access token 仍存 `localStorage`、無 CSP（Phase 46）；Webhook 回應本文仍整份讀入後才截 500 字；版本遞增為 ORM 讀取後加 1（非 SQL 原子遞增，並行時可能只加一次，安全效果相同）；PAT 可呼叫 `/logout-all` 與改密碼（改密碼仍須舊密碼），延續「PAT 等同使用者權限」；正式環境 `JWT_SECRET` 少於 32 bytes 時 PyJWT 會發 warning（仍可運作，建議 `openssl rand -hex 32`；dev 預設 secret 為 30 bytes 會觸發）；升級後仍有升級前就存在的 peer 警告（`next-intl@3.21.1`、`next-themes@0.3.0` 未宣告支援 React 19／Next 15；`next@15.5.29` 要 `@playwright/test ^1.51.1`，目前 1.48.0）
- **`pnpm lint` 無法執行**：repo 從未有 ESLint 設定檔（`next lint` 卡在互動式設定提示），為既有缺口、與升級無關；CI 的 lint 步驟在非互動環境應也會失敗，排入 Phase 46
- **明確不做**：access token 移出 `localStorage`、CSP／HSTS／TLS（Phase 46）；MFA／WebAuthn、忘記密碼；per-session refresh token 表、重用偵測與裝置管理；v1 目錄下線與 release 管線（Phase 45）；Next 16 升級
- 測試：API 1272 → **1425 passed**；Web 790 → **805 passed（135 檔）**；typecheck 0 error；`next build` 成功（Next.js 15.5.29、37 個靜態頁）；golden eval 28 passed／1 skipped；api-types 重新產生（新增 path `/api/auth/logout-all`、schema `PasswordChangeResponse`）；Migration 0028 於一次性 PostgreSQL 16 容器實測 `0027 → 0028 → 0027 → 0028`（既有列回填 0、降級後欄位移除）；釘 IP 的 TLS 行為以自簽憑證＋本機 TLS server 實測（SNI 為原 hostname 時 200、為其他 hostname 時 `CERTIFICATE_VERIFY_FAILED`），此測試未納入 pytest（pytest 只驗證傳給 httpx 的 URL／`Host`／`extensions`）。**e2e 未執行**（需完整 docker stack）：`tests/webhooks.spec.ts` 改用 `http://webhook-unreachable.invalid/hook`，新增 `tests/session-security.spec.ts`（2 情境：改密碼後保持登入且舊 token 401、登出所有裝置後導回登入頁），其選擇器未對真實頁面驗證；e2e 基線仍為 Phase 43 的 29 spec／94 情境；e2e 於全新 docker stack 實跑：chromium **91 passed／1 skipped**（`--workers=1`）、ai-stub **4 passed**（新增 `session-security.spec.ts` 2 情境；`locations-tree.spec.ts` 的「真實遷移後的位置樹」依賴舊 dev 庫的 `phase26_demo` 遷移 fixture，全新資料庫不存在 → 改為明確 skip（原本會登入逾時失敗；與本期無關））

## [2.0.0-alpha.43] — Phase 43：登入防暴力破解

- **新增 `login_attempts`（Migration 0027）**：每次登入失敗寫入 account／ip 兩列；`key_hash` 為 HMAC-SHA256（`jwt_secret`），不保存原始使用者名稱或 IP；`(kind, key_hash, created_at)` 與 `created_at` 索引；每次失敗順便清理 24 小時前紀錄，downgrade 直接刪表（只影響節流紀錄）
- **帳號分級鎖定**：5 次／15 分 → 15 分；10 次／1 時 → 30 分；15 次／24 時 → 1 時。以 `username.strip()` 精確比對；第 5 次失敗仍回 `401`，第 6 次起回 `429`
- **來源 IP 分級鎖定**：10 次／1 分 → 1 分；30 次／15 分 → 15 分。Key 為 `request.client.host`；成功登入**不**清除 IP 計數，避免用已知密碼的帳號反覆重置
- **只計失敗，不計成功與被封鎖的嘗試**：成功登入不新增列，並刪除該帳號的失敗列；被封鎖的請求直接回 `429`、不再寫入，避免攻擊者無限延長受害者鎖定
- **對外一致**：既有／未知帳號、帳號鎖定／IP 鎖定都回 `429 too many login attempts`＋`Retry-After: <seconds>`；既有 `401 invalid credentials` 不變；被封鎖時不執行密碼驗證
- **隱私與清理**：不存原始 username／IP；HMAC 以 server secret 計算；24 小時 retention；成功登入只清帳號
- **Timing 防護**：未知帳號仍對固定 dummy Argon2 hash 驗一次密碼，降低帳號列舉的 timing 差異
- **Proxy headers**：compose 的 uvicorn 加 `--proxy-headers --forwarded-allow-ips='*'`，讓 nginx 後方的 `request.client.host` 是真實來源；API 仍只 `expose` 對內。**修正**：原本 compose 的折行命令會讓 shell 把 `--proxy-headers` 當成獨立命令，uvicorn 實際沒收到旗標；改單行並加引號後以 `/proc/1/cmdline` 與 live log 驗證
- **Fail-soft**：節流查詢／寫入／重置失敗只 log warning＋rollback，不讓登入變成 500；DB 正常時登入本身仍會失敗
- **Web**：`LoginForm` 對 `429` 顯示「嘗試次數過多，請稍後再試」，其餘錯誤維持「帳號或密碼錯誤」；zh-TW／en i18n；單元測試＋e2e（5 次錯密碼→第 6 次鎖定、鎖定期間正確密碼也被拒絕）
- **明確不做**：CAPTCHA／MFA／WebAuthn、註冊／refresh／忘記密碼 rate limit、管理員解鎖 UI、Redis 滑動視窗、稽核原始 IP／User-Agent、封鎖事件告警
- 測試：API 1248 → **1272 passed**；Web 787 → **790 passed（133 檔）**；typecheck 0 error；e2e chromium 89 → **90 passed**（`--workers=1`）；golden eval 28 passed／1 skipped；api-types 新增 login `429` response；Migration 0027 於獨立 PostgreSQL 容器實測 upgrade → downgrade → upgrade

## [2.0.0-alpha.42] — Phase 42：定期報表（週報）

- **新增 `report.weekly` job**：每週一生成**上一個完整 ISO 週**（週一 00:00 至週日 24:00，Asia/Taipei）；重用月報的 `reports` 資料表、`ReportPayload`、`GET /api/reports`、`/reports` UI、`report_ready` 通知與 Email 管線，不複製一套報表系統
- **Migration 0026**：`reports.period` 由 `varchar(7)` 放寬到 `varchar(10)`（容納 `2026-W42`）；新增 `reports.kind`（`monthly`／`weekly`，`NOT NULL DEFAULT 'monthly'`）；既有列自動視為月報，`UNIQUE(user_id, period)` 不變。**downgrade 會先刪除 `kind='weekly'` 的列**再縮回 7（destructive，僅在確定要放棄週報時使用）
- **API 契約（additive）**：`ReportRead` 新增 `kind`；`ReportPayload` 新增 `kind`（預設 `monthly`，舊快照自動補值，payload version 維持 1）；偏好新增 `report_weekly_enabled`（**預設 false**，opt-in）；不新增端點、不做 `?kind=` 篩選
- **清單排序修正**：混合 `YYYY-MM` 與 `YYYY-Www` 的字典序不是時間序 → `GET /api/reports` 改以 `generated_at DESC`（同時間再以 id）排序；`limit`／`offset`／`total` 不變
- **空週與冪等**：空週仍建列（`has_activity=false`）、不通知、不寄信；`UNIQUE(user_id, period)` 保證重跑不重複；逐使用者 commit／錯誤隔離與月報相同
- **渲染**：`report_render` 依 `payload.kind` 選字庫——`本週動態`／`到期狀態（週末）`／`週初`／`週末`／`本週無動態`；通知與 Email 標題／日期範圍改用 `period_start`／`period_end`（如 `2026 年 10 月 12–18 日`），HTML 結構與 escape 不變
- **附帶修正 per-job stale**：`JobSpec` 新增 `stale_after_hours`（預設 26）；`expiry-scan` 26h、`report.weekly` 170h、`report.monthly` 770h。修正月報每月 2 日起被固定 26h 門檻誤判「停跑」的既有 bug；`GET /api/jobs/{name}/status` 回傳對應門檻
- **Web**：`/reports` 清單混合顯示月報／週報（「週報」徽章＋日期範圍）、詳情頁週報 heading／`本週動態`／`週初`／`週末`、`/settings/reports` 改為「定期報表」雙開關（每月報表＋每週摘要，各自 PUT 對應 key）、空狀態分流（兩者皆關／只開週報／月報預設）；zh-TW／en i18n
- **明確不做**：自訂期間、日報、指定週／月 backfill、週報專屬指標、CSV／PDF 匯出、報表刪除／已讀、清單 kind 篩選 tabs、使用者時區偏好
- 測試：API 1219 → **1248 passed**；Web 769 → **787 passed（132 檔）**；typecheck 0 error；e2e chromium 88 → **89 passed**（`--workers=1`）；api-types 新增 `kind`／`report_weekly_enabled` 欄位（無新增 path）；Migration 0026 於獨立 PostgreSQL 容器實測 upgrade → downgrade → upgrade
- **SQLite migration 驗證限制**：既有 migration 0021 的 constraint ALTER 在 SQLite 直接 `NotImplementedError`，因此 0026 的 up/down 改以 PostgreSQL 實測；SQLite 測試仍以 `create_all` 覆蓋新 schema

## [2.0.0-alpha.41] — Phase 41：伺服器端標籤 PDF（A4 貼紙、QR＋Code128）

- **新的列印路徑**：`GET /api/items/labels.pdf?ids=…&start=0` → 一份 A4 PDF（3 欄 × 7 列＝21 張、63.5 × 38.1 mm），直接送標籤機或一般印表機；批量標籤頁新增「下載 PDF」按鈕，既有瀏覽器列印保留
- **版面固定、不靠瀏覽器縮放**：左右邊界 9.75 mm、上下 15.15 mm、欄列距 0、淺灰裁切線；`start=0..20` 可跳過前 N 格，**重用印過一半的貼紙**
- **每張內容與既有 QR 同口徑**：QR 深連結（`public_web_url` + `/items/{id}`）、名稱（CJK 2 行內截斷）、短 id／數量、Code128 圖與條碼數字；無條碼或不可編碼（非 ASCII）只省略條碼圖，整批不失敗
- **全有全無**：任一 id 不存在／已軟刪／非本人 → `404`；`ids` 去重後 1–100 筆、`start` 0–20，超出 → `422`；回應 `Content-Disposition: attachment; filename="item-labels-YYYYMMDD.pdf"`、`Cache-Control: private, no-store`
- **依賴**：`reportlab==5.1.0`（BSD-3）、`python-barcode==0.16.1`（MIT）；**不使用 reportlab 5.x 內建 barcode widget**（`QrCodeWidget` 等 API 與 4.x 文件不相容）
- **字型內嵌**：內附 Noto Sans TC 子集（OFL 1.1，約 6.6 MB），PDF 只嵌入實際用到的字形（字型子集約 20 KB／份）。實測 reportlab CID 字型（MSung-Light／STSong-Light）在 PDFium 下會缺「舊、電、風、臺、灣、櫃」等繁中字 → 改內嵌，確保 Docker／Linux／印表機結果一致
- **真值驗證**：`pypdfium2` raster PDF 後以 `zxing-cpp` 解 QR 與 Code128，斷言內容等於深連結／條碼值；另斷言 `/FontFile2`（字型確實內嵌）、頁數、A4 尺寸與文字內容
- **附帶修正**：批量標籤預覽卡片原本固定 `4cm` 高，內容遠超高度 → 名稱／短 id 被 flex 壓成 0 高度（畫面上看不到）；改 `min-h-[4cm]` 讓文字恢復可見（列印仍維持 6 cm 寬卡片）
- **明確不做**：位置標籤 PDF、版型自訂、物品照片、非同步 job → **無 migration**
- 測試：API 1206 → **1219 passed**；Web 765 → **769 passed（132 檔）**；typecheck 0 error；api-types 新增 1 個 path（另有 router 順序造成的 path 排序變動）；e2e chromium 87 → **88 passed**（`--workers=1`）；PostgreSQL 以 live stack 實測下載

## [2.0.0-alpha.40] — Phase 40：稽核覆蓋擴充（登入、物品刪除、權杖、密碼）

- **7 個新 action，總數 5 → 12**：`auth.login`、`auth.login_failed`、`item.deleted`、`item.bulk_deleted`、`token.created`、`token.deleted`、`user.password_changed`；查詢台、篩選、CSV 全部**零改動**（facets 動態產生，新事件自動出現）
- **登入事件**：成功登入記 `auth.login`（`/refresh` 不記，避免每 15 分鐘一列）。失敗登入的對外回應一律 `401 invalid credentials`，且**只記既有帳號**；同一帳號 **10 分鐘內只記第一筆**（先查 `action + resource_id + created_at`，查詢失敗寧可不寫）。陌生帳號完全不寫，避免匿名灌寫與帳號列舉訊號
- **為何不順便做 login rate limit**：本 phase 只確保「稽核寫入不成為新的洪水面」；真正的不存在帳號嘗試仍只付一次 bcrypt／查詢成本。帳號鎖定／CAPTCHA／Redis 滑動視窗列為獨立認證強化候選
- **物品刪除**：單筆記 `meta.name`（刪除後唯一還看得到名稱的地方）；批次**只寫 1 列摘要** `{"count": n, "item_ids": [...]}`（schema 上限 100 筆），不逐筆寫、不記 names，避免事件洗版與單列膨脹
- **權杖**：建立／撤銷各記 1 列，meta 只有人類可讀 `name`；**絕不記錄 PAT 原文或 `token_hash`**。撤銷改為先取列（404 不寫稽核）再刪除
- **密碼變更**：只記「發生了變更」，`meta=null`，不含明文／雜湊／演算法名稱
- **交易順序**：`audit_service.log()` 會 commit（既有 fail-soft），所有新呼叫點都放在主寫入 commit **之後**、webhook dispatch **之前**；稽核失敗不阻擋刪除／改密碼，另有測試以壞掉的 `AuditLog` 驗證
- **明確不做**：`backup.export`（本人匯出、高頻噪音，異常量體屬告警而非單列事件）、其他 CRUD 事件、`audit_logs` 表變更（IP／UA 欄位）→ **無 migration**
- **測試**：API 1192 → **1206 passed**（新增 14 個稽核覆蓋案例，含節流窗外／停用帳號／敏感值序列化比對／fail-soft）；Web 765 passed（無改動）；typecheck 0 error；api-types **零 diff**；e2e chromium **87 passed**（`--workers=1`，僅在既有稽核 spec 加 1 個「`auth.login` 自動出現在下拉」斷言）；PostgreSQL 實測去重、JSONB meta 與無敏感值落地

## [2.0.0-alpha.39] — Phase 39：稽核查詢 UI（篩選、分頁、詳情、CSV 匯出）

- **`/settings/audit` 從唯讀清單變成查詢台**：動作／資源類型下拉（選項來自資料庫 facets，**不寫死**）、關鍵字（300ms debounce）、日期起訖、清除篩選；總數與頁碼、上／下一頁；列內展開格式化 `meta`；CSV 匯出（伺服器產生檔名）
- **看得懂「是誰」**：`AuditLogRead` 新增 `user_email`（`LEFT JOIN users`；帳號已刪除或系統事件 → `null`，介面顯示 `—`），不再只給 UUID 前 8 碼
- **API 契約變更（有意）**：`GET /api/admin/audit-logs` 由 `list[AuditLogRead]` 改為**分頁信封** `{items,total,limit,offset,facets}`；`limit` 預設 50、上限 500。唯一消費者是本倉庫的稽核面板，已同批改寫（api-types 因此出現刪除行，屬預期）
- **關鍵字 `q`** 涵蓋 `action`／`resource_type`／`resource_id`／`meta`（`cast(meta, Text)`；SQLite 與 PostgreSQL 皆實測），`%`／`_`／`\` 會轉義，避免使用者輸入變成萬用字元
- **日期區間**：`created_from`／`created_to` 為 ISO datetime、**含頭不含尾**；`from >= to` → `422 invalid_date_range`；前端以「當地日界 → UTC」換算，避免 UTC 時差造成「今天看不到今天」
- **facets 為全域**（不受列表篩選影響）：每個維度取前 50，`count desc → value asc`；代價是每次列表多 2 個聚合查詢（此資料量可接受）
- **CSV 匯出**：`GET /api/admin/audit-logs/export.csv` 套用相同篩選；UTF-8 **BOM**（Excel 繁中不亂碼）、標準 `csv` 模組轉義（逗號／引號／換行）、`Content-Disposition: attachment; filename="audit-logs-YYYYMMDD.csv"`、上限 **10,000 列**；另中和試算表公式（`=`／`+`／`-`／`@` 起首加 `'`，CWE-1236）
- **明確不做**：稽核覆蓋擴充（目前僅 5 種 action，列為候選 #4／Phase 40）、即時 tail、稽核明細頁；**無 migration**（沿用既有索引）
- 測試：API 1161 → **1192 passed**（查詢服務 14、列表端點 10、CSV 8）；Web 752 → **765 passed**（面板 12、i18n 2）；e2e 85 → **87 passed**（篩選／搜尋／匯出、非管理員守衛）

## [2.0.0-alpha.38] — Phase 38：收據證據鏈（算術驗證＋缺價待補＋幣別待確認＋不確定欄位）

- **收據算術驗證**（移植 [itemly](https://github.com/Kamitoad/itemly)（MIT）的驗證語意，改寫為本專案的 Decimal 實作）：`calculated_total = Σ品項小計 − 折扣 + 稅 + 運費`，與收據總額比對
- **對帳由兩態升為四態**：`balanced`（相符）／`discrepancy`（有差額，保留正負號）／`incomplete`（缺總額、缺價品項或幣別未知 → **無法判斷**，不呈現差額數字）／`unknown`（舊資料 → 不顯示判讀）
- **抽取欄位擴充**：收據層級 `subtotal`／`discount`／`tax`／`shipping`，品項層級 `discount`／`tax`；缺值一律 `null`（**不猜測**）
- **AI 誠實標示**：抽取可回 `uncertain_fields`（讀不確定的欄位路徑，白名單過濫、上限 20）→ 群組標頭顯示「N 個欄位待確認」
- **幣別不再假設**：讀不到幣別 → `XXX`（ISO 4217 無幣別代碼）→「幣別待確認」；缺價品項 → 「N 項待補價」
- **群組標頭升級**：顯示算術拆解（品項合計 − 折扣 + 稅 + 運費 = 應付）與三個旗標；**舊快照沿用 Phase 33 呈現**（不誤導）
- **仍不阻擋接受**（維持 Phase 33 決策）：itemly 的「未平衡收據只能存草稿」不移植——本專案為逐品項接受模型、無整張收據確認流程
- **API 契約變更（純新增）**：`ReceiptSnapshot` 新增 8 個欄位（皆為選填 → 相容舊資料），api-types 重生成為**零破壞性**（107 行新增、0 刪除）
- 測試：API 1141 → **1161 passed**；Web 742 → **752 passed**（132 檔；新增算術驗證 20 項、群組標頭 3 項、i18n 2 項）；e2e 85（live）＋4（stub，含新增算術拆解斷言）

## [2.0.0-alpha.37] — Phase 37：標籤列印加印條碼（Code128）＋QR 內容真值驗證

- **物品標籤加印 Code128 條碼圖**：標籤不再只有 QR 與條碼**數字**，現在另有可被一般掃描器（不支援 QR 的機型）讀取的條碼圖；套用於單張標籤（`/items/{id}/label`）、批量標籤（`/items/labels`）與物品詳情頁
- **以成熟函式庫取代自造輪子**：`bwip-js`（MIT）產生 Code128 **SVG**（可列印、體積小）；動態 `import()` 載入，不進首次繪製 bundle；不需後端新增端點，既有列印頁版面幾乎不變
- **可編碼性自行驗證**：Code128 僅能編碼可列印 ASCII，而 `bwip-js` 對中文等非法字元**不會報錯**而是產生內容不符的條碼（掃出是亂碼）→ 先擋掉並**退回純文字**，整張標籤仍可列印（不因一筆髒資料壞掉整批）
- **QR 內容改為真值驗證**：API 測試引入 `zxing-cpp`（Apache-2.0 wheel，無系統相依）**實際解碼** QR，斷言內容 == 預期深連結（位置 `/items?location={id}`、物品 `/items/{uuid}`）；取代 Phase 36 的「PNG 內容不同」近似斷言
- **補上 `LICENSE` 檔**：README 早已宣稱 MIT，但倉庫此前**缺少 LICENSE 檔** → 外部無法合法引用或貢獻（移植他人 MIT 程式碼時本專案自身授權也需明確）
- **無 API 契約變更**（`ItemLabel`／`LocationLabel` 欄位不變）；無 migration；位置標籤維持 QR ＋ 名稱 ＋ 路徑 ＋ 件數（位置無商品碼，不加條碼）
- 測試：Web 734 → **742 passed**（132 檔）；API 1139 → **1141 passed**；e2e 82 → **85 passed**（新增條碼 3 情境）

## [2.0.0-alpha.36] — Phase 36：位置 QR 標籤（貼在櫃子／箱子）

- **位置也可貼 QR 標籤**：掃描後直接開啟**該位置（含子孫）的物品清單**——貼在房間門口也會列出櫃子裡的東西
- **API（純新增 2 端點）**：`GET /api/locations/{id}/qr.png`（QR PNG，內容為 `/items?location={id}` 深連結）與 `GET /api/locations/{id}/label`（名稱／完整路徑／**含子孫**物品數／深連結）；他人或不存在的位置一律 `404`（不洩漏存在性）
- **深連結沿用既有物品列表位置篩選**（`location_scope` 預設 `subtree`）→ **不新增目的地頁**，直接複用篩選面板、搜尋與批次勾選
- **掃碼分流順序**（`item → location → 條碼 → 名稱`）：新增 `extractLocationIdFromPayload`（`/items?location={id}`）；手動輸入走同一分流；與物品深連結（`/items/{uuid}`）不衝突
- **列印頁** `/locations/labels`：`?ids=1,2` 直接產生標籤；**無 `ids` 時列出位置供勾選**（一次印多個櫃子／箱子）；版面沿用物品標籤頁（6cm 格、QR 2.65cm、`print:` CSS）
- **入口**：位置管理頁節點「⋯」選單「列印標籤」（單一位置）＋頁首「列印位置標籤」（勾選模式）
- **i18n**：`locations.labels.*`（9 鍵）＋`locations.tree.printLabel(s)`（2 鍵）（zh-TW／en 鍵集與行數一致）
- **無 migration**；api-types 重生成（**純新增**：`/api/locations/{location_id}/label`、`/api/locations/{location_id}/qr.png`、`LocationLabel`，258 行新增、0 刪除）
- 視覺走查發現並修正：標籤卡固定 4cm 高度容納 3 行文字會被裁切 → 改為內容驅動高度（`min-h-[4cm]`）
- 文件：[`User_Manual_zh-TW.md`](User_Manual_zh-TW.md) 新增「位置 QR 標籤」章節（列印與掃描動線、位置改名不需重印）

## [2.0.0-alpha.35] — Phase 35：AI stub 模式（可測的 AI 成功路徑）

- **`AI_MODE` 環境開關**（`live` 預設／`stub`）：`stub` 模式下**所有** LLM 呼叫改由確定性的 stub 供應器回應——不連外網、**不需 `GEMINI_API_KEY`**、**不消耗 AI 配額**；非 dev 環境啟用 stub **啟動即失敗**（避免正式環境誤回假資料）
- **攔截點在 LLM 唯一出口**（`ai_service` 的四個 `call_gemini_*`）：stub 回**原始 JSON 文字**，因此 live 的解析層、白名單驗證、名稱解析、對帳與引用映射路徑**完全相同**被執行（不是繞過驗證的假成功路徑）
- **stub 供應器**（`apps/api/app/services/ai_stub.py`）：建議（測試物品）、收據（測試商店／2 品項／對帳相符）、問答（依上下文產生可映射的 `[#n]` 引用）、搜尋（**確定性規則轉譯器**：目錄名稱最長匹配＋關鍵詞規則＋殘留關鍵字，只輸出白名單欄位）
- **統一啟用判定** `ai_enabled()`（`app/services/ai_mode.py`）：取代原本散落五處的 `if not settings.gemini_api_key`；live 模式（無 key）的 fallback／503 行為**完全不變**
- **新增唯讀端點** `GET /api/ai/status` → `{mode: "live"|"stub", enabled: bool}`（需登入）：部署者自我檢查是否誤開 stub；e2e 據此偵測模式
- **e2e 涵蓋 AI 成功路徑**（補上 Phase 32–34 最大測試缺口）：新增 Playwright 專案 `ai-stub` 與 `tests/ai-stub.spec.ts` 四情境——收據品項→對帳相符→接受入庫、AI 搜尋「理解為」chip（位置／到期／關鍵字）、問答回答附引用連結、批次辨識完成→接受入庫；spec 內以 `/api/ai/status` 自我防護（非 stub 模式自動略過）
- **Playwright 專案分流**：`chromium`（既有 live／fallback 路徑）＋ `ai-stub`（僅在 `E2E_AI_STUB=1` 註冊）；compose `api` 服務新增 `AI_MODE: ${AI_MODE:-live}` 供 shell 覆寫
- **既有缺陷修正**（非計畫內、全套驗證時以不同 `PYTHONHASHSEED` 重現）：問答上下文的關鍵字選取原以 `set` 迭代順序挑 3 個 bigram，同一問題在不同行程可能命中不同物品（`test_ask_without_item_ids_uses_keyword_context` 於 seed=1 失敗）→ 改以「出現位置」為唯一排序依據（CJK 長度 3 片段 → 拉丁整詞 → CJK 長度 2 片段，上限 12 筆）
- **Web**：無功能變更（成功路徑 UI 於 Phase 32–34 已完成，本期首次被 e2e 實際走過）
- **無 migration**；api-types 重生成（**純新增**：`/api/ai/status` 與 `AiStatusRead`，106 行新增、0 刪除）
- 文件：[`docs/ai.md`](docs/ai.md) 新增「AI stub 模式」章節（行為差異對照、stub 回應內容、啟用與自我檢查、e2e 執行方式）與疑難排解 2 列

### 本輪迭代完成（Phase 22–34，2026-10-19）

`docs/plans/2026-10-15-next-iteration-roadmap.md` 排定的 **13 個 phase 全數上線**（M1 到期與提醒 3／3、M2 輸入與結構 2／2、M3 治理與協作 5／5、M4 AI 深化 3／3）。逐 phase 變更見下方 `alpha.22`–`alpha.34`；整體狀態、驗證基線、已知限制與後續候選整理於 [`docs/progress-2026-10-19.md`](docs/progress-2026-10-19.md)。

- **測試規模**：API 912 → **1086**（＋ golden eval 28）、Web 560／111 檔 → **717／128 檔**、e2e 22 spec／68 情境 → **25 spec／79 情境**
- **Migration**：`0025 (head)`（`0019`–`0025` 皆於本輪新增）
- **既有缺陷修正**（非計畫內、走查發現）：
  - `<img src="/api/images/{id}">` 一律 401 破圖（自 Phase 1 起全站物品詳情／表單預覽／掃碼候選都看不到照片）→ `AuthImage`（`apiFetch` → blob URL）＋e2e `naturalWidth > 0` 守門
  - AI 搜尋結果數漏出原始 i18n 鍵 → `ai.search.resultCount`＋回歸測試
- **已知限制**：AI 成功路徑無法 e2e 覆蓋（`.env` 無 `GEMINI_API_KEY`）；`AuthImage` 無 blob 快取；AI 搜尋不分頁（上限 50）；問答為單輪；收據品項上限 50；`main` 尚未 push（local-only 流程）
- **後續候選**（未排程，建議優先序）：① `AI_MODE=stub` 讓 AI 成功路徑進 e2e ② 位置 QR 標籤 ③ 稽核查詢 UI ④ 週報 ⑤ 標籤列印加條碼 ⑥ 批次成本 ⑦ 分享唯讀連結 ⑧ 樓層平面圖互動 ⑨ Background Sync ⑩ v1 目錄下線 ⑪ `AuthImage` blob 快取

## [2.0.0-alpha.34] — Phase 34：AI 自然語言搜尋＋物品問答

- **既有搜尋 API 擴充**（皆 optional，省略時行為不變）：`GET /api/items` 新增 `loan=borrowed|overdue`（未歸還／未歸還且已過歸還日；未填歸還日不算逾期）、`min_quantity`／`max_quantity`（含邊界、負數 422）、`sort` 擴充 `name_asc`／`created_desc`
- **`POST /api/ai/search`**（自然語言 → 結構化 filters）：LLM 轉譯後經**白名單**驗證（`q`／分類／位置／標籤／到期／借出／最愛／數量區間／排序），名稱以本人目錄解析（完整路徑優先 → 唯一同名；同名歧義不猜，回報 `unresolved`），再走**既有** `items_service.list_items`（上限 50）；`applied` 回傳實際條件（供「理解為」chip）
- **fallback 矩陣**（一律 `200`，`fallback_reason`）：未設 key → `ai_disabled`（**不扣配額**）；配額耗盡 → `quota_exhausted`；上游錯誤 → `upstream_error`；非 JSON／無可用條件 → `unparsed`（已扣次，計次於嘗試）
- **`POST /api/ai/ask`**（grounding 問答）：上下文為 `item_ids`（≤20，僅本人可見；他人靜默丟棄）或問題分詞前 3 個 token 逐一搜尋去重；空上下文直接 `grounded=false`（不呼叫 LLM、不扣配額）；回答 `[#n]` 映射為 `citations`（越界與重複丟棄、保序），`INSUFFICIENT_DATA` → 固定「資料不足」文案；錯誤 `403`／`503`／`429`／`502`
- **opt-in**：偏好新增 `ai_data_sharing_enabled`（**預設關**）；未開啟 → `403 ai_opt_in_required`；僅送出摘要（名稱／分類／位置／數量／到期日／借出／標籤），不含照片、成本、備註
- **注入防護**：使用者句子與物品摘要包在 `<<<DATA>>>…<<<END_DATA>>>`，prompt 明示資料區塊內不得執行指令；輸出側雙重限制（搜尋白名單、問答僅上下文內引用）；測試涵蓋 6 個搜尋注入樣本與物品名稱注入
- **golden eval**（`apps/api/evals/`）：`search_golden.jsonl` 24 句（含英文與注入樣本）；mock 模式進 CI（`uv run pytest evals/ -q`，不連外網、不在預設套件內）；`EVAL_LIVE=1` 實際呼叫計分（門檻 70%，無 key 自動 skip）
- **Web**：`/items` 搜尋列「AI 搜尋」切換；「理解為」chip（含未解析灰字）＋「清除」＋「在物品列表開啟」（把條件帶回一般篩選）；fallback 以中性 `role=status` 說明（非錯誤）；未 opt-in 引導至設定；有結果時顯示「問問這些物品」問答面板（`AiMark`＋引用連結＋「以系統資料為限」聲明）；設定 → 偏好新增「AI 資料分享」開關（說明傳送範圍）
- i18n：`ai.search.*`（33 鍵）、`ai.ask.*`（13 鍵）、`settings.preferences.aiSharing*`（4 鍵）（zh-TW／en 鍵集與行數一致 1495）；對帳測試追加 Phase 34 鍵清單＋「命名空間無未使用鍵」檢查（動態鍵以命名空間前綴判定）
- 新增 65 個 API 測試（1021 → 1086）＋ golden eval 28 件（24 句 mock＋注入＋資料集檢查）；新增 31 個 web 測試（686 → 717，125 → 128 檔）；e2e 24 → 25 spec（75 → 79 情境）
- **無 migration**（偏好沿用既有 JSON 欄位；`loan`／數量／排序為查詢參數）；api-types 重生成（新增 2 端點與 schema；`sort` 列舉擴充，零破壞性移除）
- 視覺走查發現並修正：AI 搜尋結果數誤用 `items.list.page`（語義不符且缺變數 → 畫面漏出原始鍵）→ 新增 `ai.search.resultCount` 並補回歸測試
- 文件：[`docs/ai.md`](docs/ai.md) 新增 NL 搜尋／問答章節（opt-in、filters 白名單表、fallback 矩陣、grounding 與引用規則、注入防護、golden eval 操作）與疑難排解 9 列

## [2.0.0-alpha.33] — Phase 33：AI 收據辨識（多頁收據 → 品項草稿 → 帶成本入庫）

- **DB**：`ai_draft_items` 新增 `receipt_id`（UUID nullable、**無 FK**；同次收據的品項草稿共用群組鍵）＋索引 `(owner_id, receipt_id)`（Alembic `0025`；既有列為 `NULL`，無需回填）
- **抽取**（`POST /api/ai/receipts`，同步）：多頁**一次**送交 Gemini（每頁一個 Part、單一請求、`temperature=0`）→ 嚴格 JSON（商家／購買日期／幣別／總額／品項）；**一次呼叫＝1 次配額**（與頁數、品項數無關）；失敗**不落地任何列**（重試＝重送同一組圖片）
- **金額補齊**（伺服器端、決定性）：單價缺→小計/數量（2 位四捨五入）；小計缺→單價×數量；兩者皆缺→`null`（接受時成本留空）；兩者都有但不一致→保留原值（差異由對帳呈現）；日期非 ISO→`null`；無名稱列略過；品項上限 50（超出截斷並回 `truncated`）
- **草稿落地**：每個品項一列 `source='receipt'`、`status='ready'`、共用 `receipt_id`、`image_id`＝第一頁；payload 新增 `receipt`（商家／日期／幣別／總額／品項合計／差額／頁數／截斷）與 `receipt_item`（index／quantity／unit_price／subtotal）快照；`DraftRead` 新增 `receipt_id`
- **對帳**：`item_total`＝品項小計合計、`discrepancy = total - item_total`；`|差額| ≥ 0.01` → 群組標頭警示（**不阻擋接受**）；相符／未標示總額各有文案
- **狀態機邊界**：`process` 對收據草稿一律 `409`（建立即抽取完成）；`accept` 對收據草稿**不綁**收據照片為物品圖片（照片草稿行為不變）；同圖去重限定 `source='batch_photo'`（收據照片不誤擋一般照片草稿）
- **規則引擎批次化**：新增 `suggest_for_names`（單次掃描歷史、歷史 token 只算一次），供收據最多 50 品項使用；與逐次呼叫 `suggest_for_name` **結果完全相同**（含排序與分數），後者改為薄包裝
- **Web**：上傳區 `Tabs` 切換照片／收據；收據模式多頁上傳→一次抽取（「辨識收據中…」）→失敗以代碼文案＋「重試」（保留已上傳頁面）；`truncated` info toast。佇列以 `groupDrafts` 分組（照片原位、收據同組、組內依行序），群組標頭 `ReceiptGroupHeader` 顯示商家 · 日期 · N 頁 · M 品項＋對帳三態（相符／差額／無總額）；收據卡片右上「小計 {金額}」，`quantity`／`cost` 預填收據值
- **錯誤碼契約**（新端點以代碼字串回 `detail`）：`503 ai_disabled`／`429 quota_exhausted`／`502 upstream_error`／`422 no_items`／`404`（圖片不可見）／`403`（viewer）
- i18n：`ai.receipts.*`（22 鍵：模式切換、上傳、錯誤碼、群組標頭、對帳、小計、截斷）（zh-TW／en 鍵集與行數一致 1428）；對帳測試追加 Phase 33 鍵清單＋「收據命名空間無未使用鍵」檢查（並據此移除 2 個冗餘鍵）
- 新增 37 個 API 測試（984 → 1021）；新增 37 個 web 測試（649 → 686，121 → 125 檔）；e2e 23 → 24 spec（71 → 75 情境；新增「收據模式無 key 失敗且不產生草稿」「失敗後保留頁面可重試」「切回照片模式行為不變」「收據失敗後入口徽章仍為 0」）
- **Migration 0025**（`receipt_id`＋索引；Postgres up／down／up 驗證）；api-types 重生成（**純新增**：`/api/ai/receipts`、`ReceiptSnapshot`／`ReceiptItemSnapshot`、`DraftRead.receipt_id`；既有契約零變動）
- 文件：[`docs/ai.md`](docs/ai.md) 新增收據章節（端點、抽取欄位、金額補齊表、對帳語義、配額計次、錯誤碼表、e2e 無 key 限制）與疑難排解 7 列

## [2.0.0-alpha.32] — Phase 32：AI 批次入庫（草稿佇列＋智慧分類建議）

- **DB**：新增 `ai_draft_items`（Alembic `0024`；`status` CHECK `pending/processing/ready/failed/accepted/discarded`、`payload` JSON 快照、`error_code`、`item_id` 回連建立的物品、索引 `(owner_id, status)`）與 `ai_usage`（`UNIQUE(user_id, day)`，per-user 每日 LLM 計次；`day` 為 Asia/Taipei 當地日期）
- **伺服器端狀態機**（不引入背景 worker；`POST /{id}/process` 於請求內完成）：非終態皆可進入（`processing` 可重入＝卡住復原），終態 `409`；一律 `200` 回最終狀態；失敗以代碼寫入 `error_code`（`ai_disabled`／`quota_exhausted`／`upstream_error`／`image_missing`）；`failed → accepted` 允許（展開「手動填寫」直接完成＝人工補齊），`pending`／`processing` → accept `409`
- **端點**：`POST /api/ai/drafts`（1–10 張；同圖活動草稿去重回 `skipped_image_ids`）、`GET /api/ai/drafts`（省略 `status` → 活動四態、`created_at DESC`、六態 `counts`）、`POST /{id}/process`、`POST /{id}/accept`（`ACCEPTABLE_STATUSES=(ready, failed)`；以 `items_service.create_item` 建立物品，成功後才回寫草稿狀態與 `item_id`）、`POST /{id}/discard`、`POST /api/ai/drafts/discard`（批量 1–50：逐筆隔離，終態／不存在入 `skipped`，不整批失敗）；`/api/ai/drafts` 全端點掛 `WriterGuardRoute`（viewer `403` 於路由依賴階段）
- **智慧分類建議**（`POST /api/ai/suggest-classification`，唯讀、不消耗配額、不掛 guard）：以**本人歷史資料**的純規則引擎生成——NFKC＋lower 分詞（拉丁／數字 ≥2、CJK bigram）、與歷史物品名稱 token 交集評分、`(score, item_count)` 聚合、`score → item_count → id/name` 決定性排序；僅掃本人未刪除物品（`LIMIT 2000` 護欄），**LLM 不可用／配額耗盡時仍可運作**
- **配額**（`AI_DAILY_QUOTA`，預設 50、`<=0` 不設限）：per-user、Asia/Taipei 換日、**計次於嘗試**（呼叫前扣並 commit，上游失敗亦計）；耗盡時既有 `suggest-from-image` → `429`、批次流程以 `quota_exhausted` 進失敗態（行為變更，見 `docs/ai.md`）
- **Web ＞ 佇列 `/items/drafts`**：上傳區（拖放／多檔、單次上限 10 並提示略過張數、單檔失敗列內重試、建立失敗區塊重試不清空已上傳清單）、逐張序列處理迴圈（`pending` 自動續行、`processing` 不自動重送、業務失敗不中斷、傳輸錯誤停止＋「繼續處理」、已嘗試集合防重送）、四態草稿卡（AI 欄位 `AiMark`、歷史徽章「依歷史：{名稱}」、「依歷史建議」按鈕、`failed` 展開手動填寫、接受／丟棄僅本卡 loading）、批量條（全選／取消、「全部接受」僅 `ready` 其餘跳過、「全部丟棄」走批量端點）；四態頁面契約（skeleton ×3／空狀態引導／清單錯誤重試）；viewer 顯示 `ViewerNotice` 且不發出草稿查詢
- **入口**：`/items/new` 頁首「AI 批次入庫」卡＋「N 筆待審核」徽章（`activeDraftTotal` 僅計活動四態；計數失敗僅少徽章、不擋動線）；**不新增首層導覽**（計畫 D9），佇列頁提供「改為手動新增」互達
- i18n：`ai.mark.tooltip`＋`ai.drafts.*`（59 鍵）＋`items.new.batchEntry.*`（5 鍵）（zh-TW／en 鍵集與行數一致 1398）；新增 `lib/i18n/messages.test.ts` 對帳（鍵集一致／行數一致／Phase 32 齊全／無空字串）
- **修正（視覺走查發現的既有全站缺陷）**：`GET /api/images/{id}` 只接受 Bearer，`<img src>` 帶不了 token（自 Phase 1 起物品詳情／物品表單預覽／掃碼候選一律破圖）→ 新增 `components/common/auth-image.tsx`（`apiFetch` 取 blob → object URL；卸載與換圖時撤銷；失敗／未登入顯示 fallback、載入中顯示 placeholder），套用上述四處＋草稿卡；`lib/api/images.ts` 移除已無使用的 `imageUrl`；e2e 追加縮圖 `naturalWidth > 0` 守門
- 新增 72 個 API 測試（912 → 984）；新增 89 個 web 測試（560 → 649，111 → 121 檔）；e2e 22 → 23 spec（68 → 71 情境；新增「無 key：上傳→失敗→依歷史建議→手動接受入庫」「批量丟棄回空狀態」「入口卡徽章」）
- **Migration 0024**（`ai_draft_items`＋`ai_usage`；Postgres up／down／up 驗證）；api-types 重生成（`/api/ai/drafts` 系＋`/api/ai/suggest-classification`；既有契約零變動）
- 文件：新增 [`docs/ai.md`](docs/ai.md)（設定／狀態機／端點／規則引擎／狀態契約／疑難排解）

## [2.0.0-alpha.31] — Phase 31：定期報表（月報）

- **DB**：新增 `reports` 表（Alembic `0023`；`UNIQUE(user_id, period)`、`payload` JSON 快照、`generated_at`）；月報是**不可變快照**，生成後物品異動不回寫
- **排程 job** `report.monthly`：生成**上一個完整月**（Asia/Taipei）的月報；沿用 `POST /api/jobs/{job_name}/run`（admin）與 `job_runs` 觀測；每位使用者獨立 commit、錯誤隔離進 `result.errors`；`processed`＝新建列數、`emitted`＝實際通知數
- **資格與冪等**：帳號啟用＋`/settings/reports` 月報開關開啟＋至少 1 件可見（未刪除）物品；不符者整月跳過。`UNIQUE(user_id, period)` 保證同日重跑／跨日補跑不重複建列或重複發送。**空動態月**仍建列（`has_activity=false`，詳情頁標示「本月無動態」）但不通知、不寄信
- **指標口徑**：totals＝當前可見未刪；created／deleted 依 `created_at`／`updated_at` 落於期間；quantity_in／out 取 `quantity_logs` 正負 delta；loans_out／returned／overdue 依 `lent_at`／`returned_at`／期末未還且逾期；expiry 以 `EXPIRING_HORIZON_DAYS=30`（30 天內到期）與 `expiry_date ≤ 期末`（已過期）；top 3 分類／位置（未分類／未指定以 null 標示）；估值以「期末 − 期間新增 + 期間刪除 − log 淨值變化」重建月初值，Decimal 2 位字串輸出、幣別取使用者偏好
- **交付**：站內通知 `report_ready`（deep link `/reports/{id}`）＋雙語 Email（zh-TW／en；HTML＋純文字 fallback、使用者可控字串一律 escape、金額格式與 Web `formatCurrency` 對齊）；Email fail-soft 且尊重偏好矩陣（`report_ready → Email` 預設開）與管道綁定；通知以 `exclude_channels={"email"}` 避免與 Email 重複
- **API**：`GET /api/reports`（period DESC、limit／offset／total；僅本人）、`GET /api/reports/{id}`（他人／不存在一律 404）；`preferences.report_monthly_enabled`（GET 預設 true、PUT `bool|None`）
- **Web ＞ 報表**（`/reports`、`/reports/{id}`）：清單週期卡（在地化年月標題、摘要、產生時間、無動態徽章）＋四態（skeleton／首月空／月報關閉空＋設定連結／錯誤重試）；詳情區塊卡（庫存現況／本月動態／到期狀態（月底）／庫存估值（變化正負色、未設定成本註記）／熱門分類／熱門位置）＋ 404 與一般錯誤各自的返回／重試；行動優先 grid
- **設定 ＞ 通知與提醒 ＞ 月報**（`/settings/reports`，群組第 4 頁）：月報總開關（非樂觀更新＋成功／失敗 toast）、排程說明、報表歷史連結
- **導覽**：首層維持 11 項；桌面「統計」改下拉（統計／報表；`/statistics` 與 `/reports` 皆為 active）；行動 drawer 改「群組標題＋二層展開」（物品／分析／協作／系統；預設展開、可收合、active 高亮）
- i18n：`reports.*`（含 `detail.*`／`empty.*`）＋`settings.reports.*`＋`nav.reports`／`nav.groups.*`（zh-TW／en 鍵集與行數一致）
- 新增 48 個 API 測試（864 → 912；含月報 job 的冪等、空月、錯誤隔離與 rollback）；新增 58 個 web 測試（502 → 560，99 → 111 檔）；e2e 21 → 22 spec（65 → 68 情境；新增「生成→通知 deep link→詳情→冪等重跑」「空資料與開關關閉／重新開啟」「桌面下拉與行動群組導覽」3 情境）
- **Migration 0023**（`reports`；Postgres up／down 驗證）；api-types 重生成（`/api/reports`、`ReportPayload` 系、`report_monthly_enabled`）

## [2.0.0-alpha.30] — Phase 30：成員權限細化（角色模型＋viewer 唯讀）

- **角色模型**：`group_members.role`（Alembic `0022`，`String(16)` NOT NULL default `editor`＋CHECK `admin/editor/viewer`）；既有成員 backfill `editor`（零回歸）。**owner 不落庫**——由 `groups.owner_id` 判定（單一事實來源）；API `GroupMemberRead.role` 對 owner 列回傳有效角色 `owner`，`GroupDetail.my_role` 揭露呼叫者於該群組的角色
- **群組管理權限**：owner／admin 可改名、加入成員、變更角色、移除成員；刪群組維持 owner-only。admin 不得變更／移除 owner（409）、owner 自身 role 列亦 409；`role=owner` 一律 422；非成員 404、editor／viewer 403（成員越權由 404 收斂為 403）。角色變更寫 audit log（`group.member_role_changed`；加入／移除為 `group.member_added`／`group.member_removed`）
- **新端點** `PATCH /api/groups/{id}/members/{user_id}`（body `{role}`）；`POST /api/groups/{id}/members` 支援 `{username, role}`（預設 `editor`）
- **viewer 判定**：`is_read_only ⇔ 有 ≥1 筆 membership 且全部為 viewer`（owner 絕不唯讀；跨群組 editor 不唯讀）；`UserPublic.is_read_only` 隨登入／`/users/me` 回傳，離開群組後即恢復可寫
- **唯讀防線（403）**：`require_writer`＋`WriterGuardRoute` 套 14 個寫入 router（items 含 favorite／bulk、batches、items_bulk import、images、loans、lists、stocktake、transfers、backup import、categories、locations、warehouses、tags、customization）；403 發生於路由依賴階段（早於 body 解析與資源查詢，不洩漏資源存在性）。不擋：users／notifications／webhooks／external_channels／stats／barcodes／labels／item_history／jobs／admin／ai／groups（leave 需開放）
- **Web 唯讀（不渲染，非禁用）**：`useReadOnly`＋`<EditableOnly>`；items 列表／詳情／新增／編輯、清單 detail（勾選改為狀態顯示）、盤點、掃碼外查「帶入新增」、低庫存補貨、CSV／備份「匯入」、分類／標籤／位置樹／自訂面板、新增群組；**列印標籤與匯出維持可用**（讀取性操作，登錄決策）；位置樹拖放停用、F2 不進改名，方向鍵導覽與展開保留
- **§5.5 一次性 banner**：viewer 首次登入顯示（偏好 `viewer_notice_dismissed`，關閉即持久化、reload 不再出現）；物品詳情底部固定句；`/items/new`、`/items/[id]/edit` 直達顯示「檢視者無法編輯」提示卡且表單不渲染
- **群組角色管理 UI**：成員列角色 Select（`my_role ∈ {owner, admin}`；admin／editor／viewer 三選）＋角色說明；owner 列固定「擁有者」徽章不可改；editor／viewer 僅角色徽章、無成員管理入口；加入成員對話框可選角色（預設 editor）；成功 toast＋群組 query invalidate、失敗 toast（Select 由伺服器資料控制，自動回復原值）
- i18n：`viewer.*` 8 鍵＋`collab.roles.*`（含說明）＋`collab.groups.detail.roleFor`／`memberRole`／`roleChanged`／`changeRoleFailed`（zh-TW／en 鍵集一致）
- 新增 74 個 API 測試（790 → 864）；新增 51 個 web 測試（451 → 502，89 → 99 檔）；e2e 20 → 21 spec（62 → 65 情境；新增 viewer 旅程／角色管理／越權 3 情境）
- **Migration 0022**；api-types 重生成（`GroupMemberRoleUpdate`、`my_role`）

## [2.0.0-alpha.29] — Phase 29：備份與還原

- **匯出 v4（當期 schema 全量）**：`GET /api/backup/export` `format_version` 3 → 4——items 加 `barcode`／`track_batches`；新增 `preferences`（幣別）、`item_custom_values`、`item_batches`、`loans`、`quantity_logs`、`item_versions`、`stocktakes`、`webhooks`、`notification_preferences`；各清單穩定排序（同資料 → 同檔案）；`audit_logs`／`api_tokens` 永不匯出
- **`POST /api/backup/import`**（multipart：`file`／`mode`／`dry_run`／`confirm`）：`MAX_BACKUP_BYTES` 20 MiB → 413；硬錯誤 400（JSON 無效／root 非物件／`format_version` 缺失或非整數或 <1 或 >4；`mode=replace && !dry_run` 需 `confirm="REPLACE"`）；**plan（純讀）／apply 兩段式**——`dry_run=true` 只回摘要、零寫入
- **create_only（預設）**：新 id；分類／位置／標籤／倉庫以名稱匹配沿用（`reused`）；`item_types`／`custom_fields`／`item_templates` 重名加後綴（`renamed`）；列級錯誤容忍（`status="partial"`）
- **replace**：單一交易「依賴序 delete 清空（不用 DB cascade）＋匯入」，任何列錯誤即中止且零寫入（`deleted_total=0`）、例外全回滾；清空範圍不含 `audit_logs`／`api_tokens`／images／notifications／外部綁定／transfers／他人群組 membership；UI 需確認字串＋提示先匯出
- **還原範圍與降級規則**：webhooks 以停用狀態還原、`items.image_id` 設 null、幣別僅 replace 還原、群組僅還原群組殼、借用人不存在改標籤、未知參照清空——皆附 `warnings[]`（如「N 件物品的圖片不還原」、「N 個 Webhook 已以停用狀態還原」）
- **關聯重建與對帳**：loans／quantity_logs／item_batches 以 id-map 重建；匯入後逐 item 對帳 `items.quantity == Σ 未耗盡批次`，不一致進 `reconciliation[]`；`entities[]` per-entity 計數（existing／imported／created／reused／renamed／skipped／errors，`imported = created + reused + renamed + skipped + errors`）＋`errors`（上限 100）與 `errors_total`；成功匯入（非 dry-run）於 commit 後寫稽核 `backup.import`
- **Web ＞ 設定 ＞ 備份**（integrations 群組第 4 位／`/settings/backup`；設定索引頁達 6 頁上限）：匯出卡（下載＋`Content-Disposition` 檔名 fallback、loading「準備中…」）；匯入卡——選檔自動 dry-run（`aria-busy`「解析與比對中…」）、模式 RadioGroup（切 replace 立即重跑）、per-entity 摘要表（現有／匯入後／建立／沿用／後綴／略過／錯誤，replace 之「匯入後」＝建立＋後綴）、列級錯誤前 5 筆＋「還有 N 筆」、warnings、對帳橙區、replace 紅警示「將刪除 N 筆」＋「先下載備份」＋確認字串（完全相符 `REPLACE` 才啟用）；結果報告 `role="status"`＋icon 三態（綠「匯入完成：建立 X 筆、刪除 Y 筆」／橙＋失敗清單／紅「匯入失敗，未變更任何資料」）＋「重新比對」；成功後 invalidate 全站查詢、失敗 inline 可重試；摘要表 `md` 斷點桌機表格／行動卡片（§5.7 寬表格卡片化）、行動按鈕 ≥44px
- 新增 40 個 API 測試（750 → 790）；新增 22 個 web 測試（429 → 451，89 檔）；e2e 19 → 20 spec（59 → 62；新增匯出下載＋create_only round-trip／replace 確認字串把關與清空／無效 JSON 與缺 `format_version` 錯誤態）
- **無 migration**（alembic 維持 0021）；api-types 重生成（`BackupImportResult` 系契約）

## [2.0.0-alpha.28] — Phase 28：Webhook 管理 UI

- **API**：`GET /api/webhooks/{id}/deliveries` 新增 `offset` 分頁與 `status`（`success`＝2xx；`failed`＝非 2xx 含網路失敗 `status_code=null`；`pending`＝`next_retry_at` 非空，為 failed 子集）、`event` 篩選；新增 `GET /api/webhooks/{id}/deliveries/stats`（`total`／`succeeded`／`failed`／`pending`／`last_success_at`，獨立於列表篩選、不隨篩選變）
- **Web ＞ 設定 ＞ webhooks**：deliveries 改雙版型——桌機 `<Table>`（時間／事件／狀態／嘗試／下次重試／操作）＋行動卡片（`md` 斷點切換）；狀態篩選 chips（全部／成功／失敗／待重試；`aria-pressed`、tap target ≥44px）；「載入更多」infinite 分頁（PAGE_SIZE 20、回傳數＝limit 才續頁）；response excerpt 列內展開／收合；概覽（成功率整數％＋最近成功時間，`total=0` 或查詢失敗時不顯示）
- **錯誤態**：deliveries／webhooks 清單查詢失敗皆為卡內錯誤＋重試；deliveries 載入改 Skeleton
- 新增 11 個 API 測試（739 → 750）；新增 13 個 web 測試（416 → 429，87 檔）；e2e 18 → 19 spec（57 → 59；新增 deliveries 桌面主流程與行動卡片／空態）
- **無 migration、無破壞性 schema 變更**（alembic 維持 0021）；api-types 重生成（deliveries 查詢參數＋`WebhookDeliveryStats`）

## [2.0.0-alpha.27] — Phase 27：成本與庫存估值

- **DB**：`items.cost` `Numeric(12,2)` nullable（單價；`ck_items_cost_nonneg`）；Alembic `0021_item_cost`；null＝未填成本（估值以 0 計）
- **帳號層級幣別**：`users.preferences.currency`（白名單 TWD／USD／EUR／JPY／CNY／HKD，預設 TWD，**不做匯率換算**）；`GET/PUT /api/users/me/preferences` 帶 `currency`
- **`GET /api/stats/value`**：`{currency, total_value, priced_items, unpriced_items, total_items, by_category[], by_location[], by_warehouse[]}`；`value`＝`Σ(cost × quantity)`（`quantize(0.01)` `ROUND_HALF_UP`）；bucket 含 `count`；`location.label`＝樹路徑；已刪除排除；**金額一律 JSON 字串**（`"12.30"`）
- **Web 金額格式**：`apps/web/lib/format/currency.ts`（`formatCurrency`＋`CURRENCY_SYMBOLS`）——TWD 於 zh-TW／en 均 `NT$` 前綴；整數 0 位、有小數 2 位、JPY 0 位（§5.6）
- **物品**：表單成本欄（客戶端驗證：數字 ≥0、最多 2 位小數；空＝清除；錯誤態行內顯示）＋詳情頁成本顯示
- **設定 ＞ 偏好**：幣別選擇＋即時預覽；儲存後統計／估值即時更新
- **統計頁**：置頂「庫存估值」區塊——摘要（總值、已填／未填比例、「未填成本以 `NT$0` 計入」說明；全無成本引導文案）＋依分類 Pie＋依位置橫向 Bar（0 值桶排除、長路徑截斷＋tooltip 全路徑）；載入失敗卡內重試
- **儀表板**：庫存估值卡（金額＋未填註記＋「查看統計」連結；全無成本引導補成本）——**排在行動卡群組之後**（§5.1）
- **CSV**：匯出 `min_quantity` 後新增 `cost`／`currency`；匯入驗證（`cost` ≥0 最多 2 位小數、`currency` 須符合帳號幣別，不符為列級錯誤）
- **備份**：`format_version` 2 → 3（含 `cost`／`currency`）；`_serialize` 補 `Decimal → str`（同時修 `lists.budget`／`price` 有值時匯出 500 的潛在 bug）
- 新增 48 個 API 測試（691 → 739）；新增 40 個 web 測試（376 → 416，79 → 87 檔）；e2e 17 → 18 spec（新增 4 情境：估值摘要／幣別切換／表單成本驗證／儀表板卡序；統計空態 5 → 7）

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
