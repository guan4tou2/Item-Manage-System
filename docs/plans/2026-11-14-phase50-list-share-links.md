# Phase 50：清單分享唯讀連結

- **狀態**：✅ 完成
- **日期**：2026-11-14
- **基線**：`main` `d3e258e`（Phase 47）；本期於獨立分支進行，與 Phase 48（Migration 0030）、Phase 49（Migration 0031）平行，合併時接在其後
- **來源**：roadmap 候選「分享唯讀連結」——roadmap 註明「隱私設計需先定案」，本文件即為定案

---

## 目標

讓使用者把**一份清單**（旅行／購物／收藏／一般）用一條連結分享給沒有帳號的人看。只能看、不能改；隨時可以撤銷。

這是本系統**第一個不需登入的資料端點**，設計以「預設最少揭露」為原則。

---

## 隱私與安全設計（定案）

- **D1 分享範圍＝單一清單**：一條連結對應一份清單，不會連帶揭露物品庫存、位置、其他清單或帳號資訊。清單的條目本來就是獨立資料（名稱、數量、備註、連結、完成狀態），不引用庫存物品。
- **D2 預設不揭露金額**：`budget` 與條目的 `price` 預設**不**出現在公開回應中；建立連結時可逐條連結選擇「顯示價格」（`show_prices`，預設 false）。
- **D3 不揭露擁有者身分**：公開回應不含使用者名稱、email、任何使用者或清單的內部 id、建立／更新時間。
- **D4 token**：`secrets.token_urlsafe(32)`（256 bit）。資料庫只存 **SHA-256 雜湊**（比照既有 PAT 的做法）與前 6 碼（供管理介面辨識）；完整連結**只在建立當下顯示一次**，之後無法再取回——遺失就撤銷重建。
- **D5 token 不進任何 URL 路徑或 query**：分享網址為 `https://{host}/share#{token}`。fragment 不會送到伺服器，所以 token 不會出現在 nginx／應用程式的 access log，也不會經由 `Referer` 外洩。公開頁以 JavaScript 讀取 fragment，再用 **`X-Share-Token` 標頭**呼叫 API。
- **D6 效期**：建立時必選 1 天／7 天／30 天／永久，預設 7 天。過期、已撤銷、不存在一律回同樣的 `404`（不區分，不洩漏連結是否曾經存在）。
- **D7 撤銷**：擁有者可隨時撤銷（刪除該列）；刪除清單時連結一併刪除（FK CASCADE）。
- **D8 數量上限**：每份清單最多 5 條有效連結，超過回 `409`。
- **D9 公開端點的回應標頭**：`Cache-Control: no-store`、`X-Robots-Tag: noindex, nofollow`、`Referrer-Policy: no-referrer`。
- **D10 條目中的連結**：條目的 `link` 是使用者自由輸入的字串。公開頁**只有** `http:`／`https:` 開頭的才渲染成超連結（`rel="noopener noreferrer nofollow"`、`target="_blank"`），其餘一律顯示為純文字——避免 `javascript:` 之類的 scheme。伺服器端在公開回應中同樣把非 http(s) 的 `link` 設為 null（雙重防護）。
- **D11 稽核**：建立與撤銷各寫一筆稽核（`list.share_created`／`list.share_revoked`；`meta` 只記清單 id、效期、是否顯示價格與 token 前 6 碼，**不記 token 或其雜湊**）。公開存取不寫稽核，只更新連結的 `last_accessed_at` 與 `access_count`（fail-soft：更新失敗不影響回應）。
- **D12 權限**：只有清單擁有者可以建立／列出／撤銷；viewer 角色受既有 writer guard 限制（`403`）。他人的清單一律 `404`。
- **D13 不進備份**：分享連結屬於憑證性質，不納入備份匯出／匯入。

---

## API

- **D14 資料表 `list_shares`（Migration 0032，接在 0031 之後）**：`id`（GUID PK）、`list_id`（FK lists，CASCADE，index）、`owner_id`（FK users，CASCADE）、`token_hash`（char 64，unique）、`token_prefix`（varchar 6）、`show_prices`（bool，預設 false）、`expires_at`（timestamptz，nullable）、`created_at`、`last_accessed_at`（nullable）、`access_count`（int，預設 0）。
- **D15 管理端點**（需登入；掛在既有 `/api/lists` 之下）：
  - `POST /api/lists/{list_id}/shares`，body `{expires_in_days: 1|7|30|null, show_prices?: bool}` → `201`，回傳連結資訊與**完整 token（僅此一次）**。
  - `GET /api/lists/{list_id}/shares` → 該清單的有效連結（不含 token；含 `token_prefix`、`show_prices`、`expires_at`、`created_at`、`last_accessed_at`、`access_count`）。已過期的不列出，並順手刪除。
  - `DELETE /api/lists/{list_id}/shares/{share_id}` → `204`。
- **D16 公開端點**：`GET /api/public/list`（不需登入），token 由 `X-Share-Token` 標頭帶入；缺少或無效 → `404`。回應只含：`kind`、`title`、`description`、`start_date`、`end_date`、條目（`name`、`quantity`、`note`、`link`、`is_done`，依 `position` 排序），以及 `show_prices` 為 true 時的 `budget`、條目 `price` 與帳號幣別。使用獨立的 response model（**白名單**，不重用內部的 `ListDetail`）。
- **D17 token 比對**：以雜湊查詢（unique index），不做逐筆字串比較。

## 介面

- **D18 管理**：清單詳情頁加「分享」按鈕 → 對話框：
  - 建立：效期選擇、顯示價格開關 → 建立後顯示完整網址與「複製」按鈕，並明示「這個連結只會顯示這一次」。
  - 既有連結列表：前 6 碼、建立時間、到期時間（或「永久」）、是否顯示價格、最後存取時間、存取次數，各有「撤銷」（AlertDialog 確認）。
  - 空狀態、載入、錯誤、達上限（`409`）各有呈現。viewer 不渲染分享按鈕。
- **D19 公開頁 `/share`**：位於登入區之外的獨立路由（不套用 app 的導覽列、不在 middleware 的保護清單內）。唯讀呈現清單標題、說明、日期與條目；完成的條目以文字＋樣式標示（不只靠顏色）。狀態：載入中、連結無效或已過期（同一個訊息）、網路錯誤可重試、fragment 缺少 token。頁面加 `noindex` meta。頁尾一行小字說明這是唯讀的分享頁。行動裝置優先（收到連結的人多半用手機開）。
- **D20 視覺與無障礙**：依 `DESIGN.md`；公開頁沿用同一套 token 與 light／dark；語言依瀏覽器語言在 zh-TW／en 間選擇（沿用專案既有的語系判定方式）。

---

## 明確不在本期範圍

- 分享物品庫存、位置、報表
- 密碼保護的連結、允許對方編輯或勾選
- 公開存取的速率限制（token 為 256 bit，無法猜測；濫用防護交由前置代理）
- 連結預覽（Open Graph）——刻意不做，避免內容被第三方服務抓取

---

## 驗證

- API：建立／列出／撤銷；token 只在建立回應出現、資料庫不存明文（直接查表斷言）；效期四種選項與過期後 `404`；撤銷後 `404`；刪除清單後 `404`；上限 `409`；他人清單 `404`、viewer `403`；公開回應的**欄位白名單**（對整個回應序列化後斷言不含擁有者 email／使用者名稱／任何 UUID／`budget`／`price`）；`show_prices` 開啟後才有金額；非 http(s) 的 `link` 為 null；回應標頭；無標頭／錯誤 token `404`；存取計數與 fail-soft；稽核兩種 action 且不含 token
- Migration 0032：PostgreSQL 升降版（CI）
- Web 單元：對話框各狀態、建立後只顯示一次、複製、撤銷；公開頁各狀態、`javascript:` 連結不成為超連結、未開啟價格時不顯示金額欄
- e2e：建立清單與條目 → 建立分享連結 → 在**未登入**的瀏覽器 context 開啟 `/share#token` 看到內容且沒有價格 → 撤銷 → 重新整理後顯示連結無效
- 實際操作：桌面與手機寬度；確認伺服器 log 中沒有出現 token

## 實作結果

### 完成項目

- 新增 `ListShare` model 與 Migration 0032（`down_revision = "0031"`）；FK CASCADE、唯一 token 雜湊與清單索引均已設定。
- 新增分享建立／列出／撤銷與獨立公開讀取 router；建立時鎖定清單列，於同一交易檢查五條有效連結上限。過期清理由管理列表與建立流程執行。
- 公開資料使用獨立白名單 schema，預設不序列化金額、幣別、身分、內部 id 與時間；非 http(s) 連結清成 null。公開成功與 404 均送出 D9 的三個標頭。
- 建立／撤銷寫入最小稽核資料，公開存取僅以原子更新維護計數與最後存取時間，寫入／提交失敗可回滾並繼續回應。
- 清單詳情新增分享對話框，提供效期、價格選項、一次性網址、複製與手動選取後備、有效連結資訊及撤銷確認；viewer 不渲染入口。
- 新增 `/share` 唯讀頁，從 fragment 取 token，使用獨立 fetch 與 `X-Share-Token`，明確省略 cookie 並禁止快取；提供載入、缺 token、無效／過期、網路重試與空清單狀態。金額沿用既有格式、連結前端再次檢查，完成狀態同時使用文字與刪除線。
- 公開頁設定 `noindex, nofollow` 與 `no-referrer` metadata；保留現有 middleware 的公開路由行為，並讓根層 Provider 在 `/share` 略過登入、語系與主題偏好的 API 同步元件，避免間接觸發 refresh 或清除登入狀態。
- 同步 zh-TW／en 訊息與 OpenAPI／TypeScript 型別，新增 API、Vitest 與 `tests/list-share.spec.ts`。

### 與計畫的差異

- D1–D20 無放寬；除計畫指定的公開 fetch 隔離外，另外隔離根層 Provider 的登入偏好同步，維持公開頁的請求邊界。
- 主工作樹 venv 的 editable import 路徑會影響直接執行匯出腳本，因此以 `PYTHONPATH=.` 搭配指定直譯器，從本 worktree 的 `apps/api` 匯出；未修改腳本或依賴。
- Vitest 預設並行執行曾使既有測試 timeout；兩個 worker 重跑仍有既有測試超時，最後以 `--maxWorkers=1 --minWorkers=1` 執行全套。未調整任何既有斷言或 timeout。

### 主代理的審查與實際操作

- 以 API 建立清單（含預算、一個帶價格的條目、一個 `javascript:` 連結的條目）與分享連結 → 公開端點回應只含白名單欄位、沒有 `budget`／`price`、`javascript:` 連結為 null、三個標頭（`Cache-Control: no-store`、`X-Robots-Tag: noindex, nofollow`、`Referrer-Policy: no-referrer`）都在；沒帶 token 與錯誤 token 都是 404；**伺服器 log 中搜尋不到 token**。
- 未登入的瀏覽器以 375px 開啟 `/share#token` 正常顯示、無水平溢出、有 `noindex` meta、合法連結帶 `rel="noopener noreferrer nofollow"`、惡意連結未成為超連結；清單頁的分享對話框顯示效期選擇、顯示價格開關與既有連結（前 6 碼、建立／到期時間、存取次數、撤銷）。

### 驗證

- 已確認 `app.__file__` 指向本 worktree。
- API 測試涵蓋 CRUD、四種效期、過期清理、一次性 token／直接查表雜湊、欄位白名單（整份序列化文字否定斷言）、價格 opt-in、危險連結、權限、上限、FK CASCADE、成功／404 標頭、存取計數與 fail-soft、稽核與 access log 不含 token，以及備份匯出／匯入排除憑證。**API 1474 passed**。
- Web 單元涵蓋對話框各狀態、一次性網址與 mutation cache、複製與後備、撤銷確認／失敗、公開頁各狀態與重試、連結安全／價格隱藏、公開 fetch 不附登入憑證／不 refresh／不清除 store，以及 middleware 與 Provider 的公開頁隔離。**Web 859 passed（144 檔）**。
- 指定的 pytest、evals、ruff、tsc、Vitest、Next lint 與 `git diff --check` 均已通過。全套 API 測試啟動後補增的安全案例，已另以分享測試檔全數驗證；合併 Phase 48＋49＋50＋維護項目後的 main：**API 1524 passed、Web 926 passed（148 檔）**。

### 未驗證項目

- Playwright e2e 未在本機執行（本機 Docker 未啟動）：Phase 50 的 `list-share.spec.ts` 交由 CI 的 `e2e` job。
- **Migration 0032 的 PostgreSQL 升降版未在本機執行**，交由 CI。
- 公開存取沒有速率限制（token 為 256 bit，無法猜測；濫用防護交由前置代理）。
- 本機實測用的是 SQLite，時間欄位在本機顯示為無時區（正式環境為 PostgreSQL timestamptz）。
- CI 結果在撰寫時尚未確認，push 後由 CI 確認。

