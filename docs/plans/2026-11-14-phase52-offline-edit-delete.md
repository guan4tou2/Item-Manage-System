# Phase 52：離線編輯／刪除與背景同步

- **狀態**：✅ 完成
- **日期**：2026-11-14
- **基線**：`main`（Phase 51＋大版本升級）；Alembic head `0033`，本期**不新增 migration**
- **來源**：roadmap 最後一個候選「離線編輯／刪除與分頁關閉後的背景同步」

---

## 目標與範圍

Phase 51 做到「開著 App 時斷線仍可新增物品」。本期補上另外兩個動作與一個時機：

- **做**：開著物品編輯表單或物品詳情頁時斷線，仍可「儲存修改」與「刪除」；動作先存在裝置上，連線後送出。
- **做**：伺服器端偵測「離線期間這個物品被別人（或另一台裝置）改過」，不靜默覆蓋，交給使用者決定。
- **做**：支援的瀏覽器（Chromium 系）在分頁關閉後，由 service worker 於恢復連線時把佇列送出。
- **不做**：離線瀏覽沒開過的物品（資料不在記憶體就無從編輯）、欄位層級的自動合併、離線批次操作／收藏／批次（batch）／清單／圖片上傳／AI。

---

## 設計決策

### 伺服器端：不靜默覆蓋

- **D1 `If-Match`**：`PATCH /api/items/{item_id}` 與 `DELETE /api/items/{item_id}` 接受選填的 `If-Match` 標頭，值為用戶端手上那份物品的 `updated_at`（ISO 8601，原樣回傳即可；可帶雙引號）。
  - 沒帶標頭 → 行為完全不變（線上操作不受影響）。
  - 解析不出時間 → `422`。
  - 與資料庫目前的 `updated_at` 不同（統一轉成 UTC、比到微秒）→ **`412`**，`detail = {"code": "item_modified", "current": <ItemRead>}`，不做任何修改、不寫稽核、不派送 webhook。
  - 相同 → 照常執行。
- **D2 `updated_at` 一定前進**：`update_item` 每次成功都要推進 `updated_at`，即使只改了標籤（關聯表變更不會觸發欄位的 `onupdate`）。其他寫入路徑（收藏、批次操作、盤點、batch）不在本期調整——它們若剛好推進了 `updated_at`，離線修改會被視為衝突並詢問使用者，屬於保守方向。
- **D3 已刪除的物品**：維持既有的 `404`。用戶端對「刪除」動作把 `404` 視為已完成；對「修改」動作視為失敗（物品已不存在）。
- **D4 不加 migration**：以既有的 `updated_at` 當版本，不新增欄位。

### 佇列項目

- **D5 三種動作**：佇列項目新增 `kind`：`create`（Phase 51 既有，舊資料沒有這個欄位時視為 `create`）、`update`、`delete`。IndexedDB 沿用 `ims-offline`／`pending-items`、**版本維持 1**（只加欄位，不改結構，避免頁面與 service worker 互搶升級）。
- **D6 新欄位**：`item_id`、`item_name`（顯示用）、`base_updated_at`（當作 `If-Match`）、`values`（`update` 時的表單值，供「編輯後重送」）、`steps`（見 D8）、`api_base`（絕對網址，供 service worker 使用）、`server`（衝突時伺服器回傳的目前內容）。`status` 新增 `conflict`。
- **D7 同一個物品只留一筆**：
  - 已有待送的 `update`，再次離線儲存 → 取代內容，**保留最早的 `base_updated_at`**（否則第一筆送出後第二筆會被誤判為衝突）。
  - 已有待送的 `update`，接著離線刪除 → 以 `delete` 取代，保留最早的 `base_updated_at`。
  - 物品已有待送的 `delete` → 清單中隱藏，無法再操作；要反悔就在待同步區塊「捨棄」。

### 重放引擎（頁面與 service worker 共用）

- **D8 步驟清單**：進佇列時由頁面把要送的請求算好，存成 `steps: [{ method, path, body?, headers? }]`，`path` 相對於 API 根（如 `/items/{item_id}`），`{item_id}` 在 `create` 時由第一步的回應填入。
  - `create`：`POST /items`（帶 `Idempotency-Key`）→ 需要時 `POST /items/{item_id}/batches` → 自訂欄位值的寫入／刪除請求。
  - `update`：`PATCH /items/{id}`（帶 `If-Match`）→ 自訂欄位值的寫入／刪除請求。
  - `delete`：`DELETE /items/{id}`（帶 `If-Match`）。
  - 第一步是主要動作；其後是補充步驟，失敗不重試（與 Phase 51 一致），結果標為「部分完成」並提示到物品頁補上。
- **D9 單一實作**：引擎寫成不依賴任何模組的 `lib/offline/engine.ts`，只接受注入的 `request(step) → { status, body }`（網路層失敗時丟例外）。它負責：依序執行步驟、判定結果、算出項目的下一個狀態。頁面端的 `OfflineQueue` 與 service worker 都呼叫它；`OfflineQueue` 原本的 single-flight、使用者切換、回報邏輯保留。
  - service worker 不能載入 TypeScript：以腳本 `scripts/build-offline-engine.mjs`（`typescript.transpileModule`）產生 `public/offline-engine.js`（掛在 `self.imsOfflineEngine`），**產物提交進版本庫**，並有測試在產物與原始碼不同步時失敗。
- **D10 結果分類**（主要動作）：
  - 網路層失敗 → 維持 `pending`，結束本輪。
  - `401` → 維持 `pending`，結束本輪（等重新登入）。
  - `412` → `conflict`，把 `detail.current` 存進 `server`。不自動合併。
  - `404`：`delete` → 視為完成；`update` → `failed`（`item_gone`）。
  - 其他 `4xx`（`403`／`409`／`410`／`422`…）→ `failed` 並記 `error_code`（沿用 Phase 51 的代碼判定）。
  - `5xx` → `attempts` 加一維持 `pending`，連續 5 次後 `failed`。
  - `2xx` → 執行補充步驟；全部成功 → 移出佇列；任一失敗 → 移出佇列並回報「部分完成」。
- **D11 舊資料**：Phase 51 留下、沒有 `steps` 的項目，頁面端在同步時補算；service worker 略過（留給頁面）。

### 介面

- **D12 進佇列時機**：與 Phase 51 D7 相同——`navigator.onLine` 為 false，或請求因網路層失敗。拿到 HTTP 回應的錯誤照原本處理。
- **D13 離線儲存修改**：toast「已存在這台裝置，連線後自動同步」，回到物品詳情頁；詳情頁與編輯表單顯示離線期間改過的值（更新記憶體中的查詢快取），並標示「有尚未同步的修改」。
- **D14 離線刪除**：確認框照舊；確認後 toast 並回到清單，清單隱藏該物品。
- **D15 待同步區塊**：每筆顯示動作（新增／修改／刪除）與物品名稱。
  - `conflict`：說明「這個物品在你離線期間被修改過」，動作「查看目前內容」（連到物品頁）、「用我的版本」（以伺服器目前的 `updated_at` 當 `If-Match` 重送；`delete` 則為「仍要刪除」）、「捨棄」。
  - `failed` 的 `update`：「編輯後重送」（帶著離線時的值開編輯表單，送出後取代原項目）與「捨棄」。
  - 「捨棄」`update`／`delete` 時要還原畫面（重新抓取該物品與清單）。
- **D16 離線時不可用**：編輯表單的圖片上傳、AI 入口、「啟用批次追蹤」在離線時停用並說明原因（與 Phase 51 D8 一致）。
- **D17 其餘沿用 Phase 51**：離線提示列、導覽徽章（計入所有動作）、登出提示、IndexedDB 不可用／空間不足的訊息、viewer 沒有入口、token 化的視覺、zh-TW／en 同步、`aria-live`。

### 背景同步（分頁關閉後）

- **D18 觸發**：進佇列後、以及 App 載入時仍有待送項目，頁面呼叫 `registration.sync.register("ims-offline-sync")`（先檢查支援；失敗忽略）。不支援的瀏覽器（Safari、Firefox）維持 Phase 51 的行為：下次開啟 App 時同步。
- **D19 service worker 的登入憑證**：access token 存在頁面端，service worker 拿不到；改以 httpOnly 的 refresh cookie 呼叫 `POST {api_base}/auth/refresh`（`credentials: "include"`）換一個 access token。refresh token 是無狀態 JWT、以 `token_version` 撤銷，並行換發不會互相作廢。
  - `401`（已登出／已撤銷）→ 不處理、不重試。
  - 換到的 token 其 `sub` 必須等於項目的 `owner_user_id` 才處理（同一台裝置換了帳號時不可送出別人的項目）。
- **D20 不與頁面重複送出**：頁面與 service worker 都以 Web Locks（`navigator.locks`，名稱 `ims-offline-sync`，`ifAvailable`）包住一輪同步；拿不到鎖就跳過。不支援 Web Locks 的環境不加鎖（此時也沒有背景同步）。
- **D21 完成後通知**：service worker 處理完向所有開著的頁面 `postMessage({ type: "ims-offline-synced" })`，頁面重新讀取佇列並更新清單。網路層失敗時讓 `sync` 事件失敗，由瀏覽器稍後重試。
- **D22 不顯示系統通知**：背景同步的結果（含衝突與失敗）留在佇列，下次開啟 App 時在待同步區塊看到。

---

## 明確不在本期範圍

- 離線瀏覽未曾載入的物品、預先快取資料
- 欄位層級的自動合併（衝突一律整筆詢問）
- 離線批次操作、收藏、batch、清單、盤點、圖片上傳、AI
- iOS／Safari／Firefox 的背景同步（平台不支援 Background Sync API）
- 背景同步完成的系統通知

---

## 驗證

- API：沒帶 `If-Match` 行為不變；相符可改／可刪；不符 `412` 且內容含目前物品、資料未變、無稽核與 webhook；格式錯誤 `422`；帶引號與不帶引號都接受；只改標籤也會推進 `updated_at`；viewer 仍為 `403`；刪除後再刪 `404`
- Web 單元：引擎每一類結果（D10）；`{item_id}` 代入；補充步驟失敗為部分完成；D7 的合併規則；舊資料補算步驟；產物與原始碼同步；service worker 的同步流程（以記憶體版 IndexedDB 與假的 `fetch`）：換 token、`sub` 不符略過、`401` 不處理、網路失敗讓事件失敗、完成後通知頁面
- e2e（Playwright）：離線修改 → 連線後同步；離線期間由 API 改同一物品 → 出現衝突 → 「用我的版本」；離線刪除 → 連線後物品不存在；背景同步以 CDP 觸發 `sync` 事件（若環境做不到則明示）
- 實際操作：桌面與手機寬度

## 實作結果（前端）

### 已完成項目

- 完成 D5–D22 的前端與 service worker 實作；僅修改 `apps/web`，另於本文件末尾附加本節。未修改 `apps/api`、`packages/` 或其他文件。
- `updateItem`／`deleteItem` 支援選填 `If-Match`，原樣傳送 `updated_at`；一般線上呼叫維持不帶標頭。依 D1 的 `412 detail.current` 契約保存衝突內容。
- 新增完全無 import 的共用重放引擎、純狀態轉換函式與步驟模組；覆蓋成功、401、412、修改／刪除的 404 差異、其他 4xx、5xx 五次上限、網路失敗、物品 ID 代入與補充步驟部分完成。新增送出與步驟模組共用建立內文；編輯頁與步驟模組共用修改內文，追蹤批次時省略 quantity。自訂欄位的順序、內文、清除及容忍刪除 404 均與原線上流程一致。
- 佇列新增 create／update／delete、conflict、API 絕對根網址與相關欄位；IndexedDB 仍為 `ims-offline`／`pending-items`／版本 1。入列套用 D7 合併並保留最早版本；舊資料由頁面補算步驟與 API 根網址，worker 略過沒有步驟的資料。保留 single-flight、帳號切換、編輯中略過、同步前重讀紀錄與結果回報。
- 完成編輯頁離線保存、網路失敗入列、快取與讀取結果的離線值覆蓋、詳情／編輯頁未同步提示、記憶體帶值編輯後重送；離線停用圖片上傳、AI 與啟用批次追蹤，提供原因。
- 完成確認後離線刪除、回清單、隱藏待刪物品；已排隊刪除的物品禁止繼續修改。待同步區塊顯示動作與名稱、白話失敗原因、衝突的查看目前內容／用我的版本（仍要刪除）／捨棄，以及失敗修改的編輯後重送。捨棄修改／刪除會重新抓取物品查詢（含非作用中的詳情與清單）。
- 頁面與 worker 都使用 `ims-offline-sync` Web Lock／`ifAvailable`。App 載入有待送資料及入列後嘗試註冊背景同步；收到 worker 訊息會重讀佇列並 invalidate 相關查詢。
- worker 以 `importScripts` 載入產物，直接操作原 IndexedDB；以 refresh cookie 換 token、檢查 token sub 與 owner、依建立順序處理 pending／syncing 且具有步驟的紀錄，保存結果並通知所有 window clients。網路失敗使 sync event 失敗；不新增系統通知。既有 install／activate／fetch／push／notificationclick handler 未變更。
- 新增 `gen:offline-engine`、產生腳本與 `public/offline-engine.js`；產物有「自動產生，勿手改」檔頭並排除 ESLint。測試重新轉譯比對產物，亦在假的 self 上實際執行產物。
- zh-TW／en 以文字插入同步新增鍵，沿用既有格式與 UI token。新增互動採既有 UI 元件與至少 44px 按鈕，狀態兼具文字與顏色。
- 增加引擎、產物、步驟與實際線上請求比對、合併、舊資料補算、Web Locks、背景註冊、查詢資料穩定性、編輯／刪除頁面、衝突／捨棄等單元測試。worker 測試以原始碼＋假的全域環境、fake-indexeddb 與假的 fetch 實際執行，涵蓋換 token、owner 隔離、401、網路失敗、持久化、通知、鎖及建立順序。原測試保留；重放測試改注入 HTTP 步驟回應，維持原本對順序、key、隔離、狀態、single-flight 與回報的斷言目的。
- 新增 `tests/offline-edit.spec.ts`：離線修改後自動同步（1280px／375px）、另一裝置修改造成衝突後用我的版本、離線刪除後 API 為 404。

### 與計畫的差異／釐清

- 清單隱藏待刪物品及詳情的離線值覆蓋放在既有 `useItems`／`useItem` hook，避免重複頁面邏輯；保留資料物件參照穩定，避免觸發清單既有的選取校正迴圈。未修改清單頁本身。
- 引擎的部分完成結果額外標示補充步驟是否遇到網路失敗。主要動作仍依 D8 移出佇列、不重試補充步驟；worker 同時依 D21 讓事件失敗，留待瀏覽器處理其餘未完成項目。不同 API 根網址的紀錄仍維持整體建立順序，每個根網址各自換取並沿用該輪 token。
- 共用新增內文與修改內文；原線上新增的後續步驟、部分完成回饋與自訂欄位失敗行為保留。背景部分完成依設計移出佇列，不發送系統通知。
- 伺服器端 D1–D4 由另一位實作者負責，本次僅實作契約呼叫及假的 HTTP 回應測試，未將單元測試視為後端整合驗證。

### 實際驗證結果（均於 apps/web）

- `./node_modules/.bin/tsc --noEmit`：exit 0，0 error。
- `./node_modules/.bin/eslint . --max-warnings 0`：exit 0，0 error／0 warning。
- `./node_modules/.bin/vitest run`：exit 0，**1033 passed／160 檔**（原基線 975 passed／154 檔）。Vite 仍輸出既有 configLoader 原生載入相容性提示，不影響通過。
- `node scripts/build-offline-engine.mjs`：exit 0；重新產生前後逐位元組相同，SHA-256 為 `52189dab8899fe19561db4579c436825d726acbdb0173bb05dd95f5d0fa34644`。隨後 `git diff --stat -- public/offline-engine.js`：exit 0，無輸出；另外的逐位元組比對與產物單元測試確認同步，避免未追蹤新檔不顯示在 diff 的限制。
- `./node_modules/.bin/playwright test --list tests/offline-edit.spec.ts`：exit 0，成功收集 **4 tests／1 file**。
- 額外檢查兩份語系完整葉節點鍵集合：各 **1395** 個，集合一致。

### 未驗證的部分

- 依本次限制未啟動伺服器、未執行 next build、未安裝套件，也未執行 Playwright e2e；API 的真實 If-Match／refresh-cookie 整合仍待有伺服器的環境驗證。
- 桌面／375px 的真實瀏覽器操作、水平溢出、觸控與鍵盤操作尚未實測；新 e2e 已加入桌面／手機情境及寬度斷言，尚待執行。單元測試通過不等於瀏覽器版面驗證。
- 分頁關閉後 Chromium 的實際 Background Sync 排程、CDP 觸發 sync、真實跨分頁 Web Locks 與 cookie／service worker 生命週期未實測；目前以假的全域環境、IndexedDB、fetch 和鎖驗證流程。

## 主代理的審查與實際操作

- API 部分由 codex 實作：`If-Match` 檢查、`update_item` 一律推進 `updated_at`，新增 56 個測試；全套 **1593 passed**、ruff 零違規。
- 前端與 service worker 由 codex 實作（見上節）。主代理審查後的修改：
  - **離線時不導頁**：原實作離線儲存後導回詳情頁、離線刪除後導回清單。以 Docker stack 跑 e2e 時發現 Next.js 換頁需要連線抓頁面資料，離線下出現「This page couldn’t load」。改為離線（或伺服器連不上）時留在原頁：編輯表單顯示「有尚未同步的修改」，詳情頁顯示「已排入刪除」。連得上伺服器時才導頁。
  - **service worker 載入引擎失敗不影響安裝**：`importScripts` 包在 try／catch，失敗時只是沒有背景同步。
  - **多個分頁**：兩個分頁同時開著時，一個分頁同步完，另一個分頁的待同步區塊不會更新。加上 `BroadcastChannel` 通知。
  - 離線提示列文字改為涵蓋新增、修改與刪除；「已排入刪除」的說明改寫得更白話。
- 實際驗證（Docker Compose 重建的完整 stack，PostgreSQL）：
  - `tests/offline-edit.spec.ts` 五個情境全數通過：離線修改後自動同步（1280px 與 375px，含水平溢出檢查）、離線期間由 API 修改同一物品 → 衝突 → 「用我的版本」、離線刪除 → 連線後 API 為 `404`、**關掉分頁後以 CDP 送出 `sync` 事件，由 service worker 換 token 並送出修改**。
  - 完整 Playwright（chromium）：**104 passed／1 skipped**。
  - Web：`tsc` 0 error、`eslint` 0 warning、vitest **1034 passed（160 檔）**（Node 22 與 24）。
- 未驗證：
  - 測試用的 Chromium 停用了 Background Sync 的排程（`sync.register` 回報 disabled），所以「瀏覽器在恢復連線時自己觸發 `sync`」沒有實測；真實 Android Chrome 未實測。
  - 重新整理頁面後，離線狀態下沒有物品資料可顯示（資料只在記憶體）；佇列本身存在 IndexedDB，不會遺失。
