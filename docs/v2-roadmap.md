# v2 重構路線圖

> **狀態：全部 10 個基礎子專案完成，之後追加 16 個進階 phase（Phase 1–16）也全部上線。** v2 已於 `main` 分支進入維護期。逐 phase 變更請看 [CHANGELOG.md](../CHANGELOG.md)。

參見 [`docs/superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md`](superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md) 了解基礎決策。

## 基礎子專案

| # | 主題 | 狀態 |
|---|------|------|
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 完成 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ✅ 完成 |
| 2 | 資訊架構與全域導航 | ✅ 完成 |
| 3 | 物品 CRUD + 搜尋 | ✅ 完成 |
| 4 | 儀表板與統計 | ✅ 完成（見下方 Phase 12 擴充） |
| 11 | 通知中心 | ✅ 完成（見下方 Phase 7 外部管道） |
| 6 | 清單類（旅行、購物、收藏） | ✅ 完成 |
| 7 | 協作（群組、借用、轉移） | ✅ 完成 |
| 8 | 管理與設定 | ✅ 完成 |
| 9 | 行動/PWA 體驗 | ✅ 完成（見下方 Phase 16 polish） |

## 進階 Phase 1–16（v1 功能補齊 + 增強）

| Phase | 主題 | 狀態 | 關鍵能力 |
|-------|------|------|----------|
| 1 | 收藏 + API Tokens + 稽核 | ✅ | `ims_pat_` PAT、audit log |
| 2 | 圖片上傳 | ✅ | MIME 允許清單、每用戶目錄 |
| 3 | Gemini AI 辨識 | ✅ | `gemini-2.0-flash`、繁中提示 |
| 4+5 | 自訂欄位 + 物品歷史 | ✅ | item types / custom fields / quantity logs / versions |
| 6 | 盤點 | ✅ | Session 盤點 → quantity log 自動寫入 |
| 7 | 外部通知 | ✅ | Email / LINE / Telegram / Web Push fail-soft |
| 8 | 倉庫 | ✅ | 跨實體場所隔離 |
| 9 | 備份匯出 | ✅ | JSON dump，含 `format_version` |
| 10 | Webhooks | ✅ | HMAC-SHA256、delivery log |
| 11 | 位置進階 | ✅ | 手動排序、樓層平面圖 |
| 12 | 儀表板 v2 | ✅ | 低庫存 / 借出逾期 / 30 天趨勢 / 活動流 |
| 13 | QR 標籤產生 | ✅ | 物品 PNG label + A4 列印預覽 |
| 14 | CSV 批次匯入/匯出 | ✅ | dry-run、per-row 驗證、query 匯出 |
| 15 | 相機 QR 掃描 | ✅ | `/scan` 頁、裸 UUID fallback |
| 16 | PWA polish | ✅ | shortcuts、iOS meta、SW v2 |
| 17 | 文件同步 | ✅ | CHANGELOG、README、FEATURES 對齊實作 |
| 18 | SW 更新提示 | ✅ | 偵測 waiting SW → sonner toast → skipWaiting |
| 19 | CSV tags round-trip | ✅ | export/import `tag_names`，pipe-delimited、dedup、per-owner 隔離 |
| 20 | Tag 管理 UI | ✅ | `/tags` 端點群 + taxonomy 頁籤：rename / merge / delete / prune-orphans |
| 21 | Webhook 重試 | ✅ | exponential backoff (30s/2m/8m/30m)、manual retry、process-retries endpoint |
| 22 | 批次庫存＋到期管理 | ✅ | 批次 CRUD／FEFO 消耗／到期篩選＋到期模式／儀表板到期行動卡 |
| 23 | 通知偏好中心 | ✅ | 設定頁索引＋子路由（10 面板零回歸）、`notification_preferences` 表、偏好矩陣 API＋設定頁 |
| 24 | 排程自動化＋到期提醒 | ✅ | 外部 cron ＋冪等 job 端點（admin）、`expiry-scan` 摘要提醒（冪等 dedupe）、`/settings/reminders` 停跑觀測、到期卡註記 |
| 25 | 條碼掃描（內查＋外查） | ✅ | `items.barcode`＋`barcode_lookups`（TTL 30 天）、provider 抽象（Open Food Facts／Open Library）、`/scan` 多格式引擎（QR＋1D）、表單 prefill、行動 FAB |
| 26 | 多層位置樹重建 | ✅ | `locations` 樹化（parent_id／kind／同層同名唯一）、migration 0020＋一次性遷移（保證無孤兒＋報告／dry-run）、樹 API（tree／path／move／reorder／刪除 409）、`location_scope` 預設含子孫、樹管理頁（拖放／鍵盤／行動搬移）、樹狀選擇器、CSV `location_path`、backup v2 |
| 27 | 成本與庫存估值 | ✅ | `items.cost`（Decimal 12,2 nullable）＋migration 0021、帳號層級 `currency` 偏好（六幣別、無匯率換算）、`GET /api/stats/value`（總值＋分類/位置/倉庫分布＋未填比例）、統計頁估值區塊（摘要＋兩圖）、儀表板估值卡（行動卡群組之後）、`formatCurrency`（TWD→`NT$` 雙語）、CSV `cost`／`currency`、backup `format_version` 3 |
| 28 | Webhook 管理 UI | ✅ | deliveries 篩選（`status`／`event`）＋`offset` 分頁＋統計端點（成功率、最近成功）；面板桌機表格／行動卡片、篩選、載入更多、excerpt 展開、概覽與查詢錯誤態；無 migration |
| 29 | 備份與還原 | ✅ | 匯出 v4（當期 schema 全量：barcode／批次／借還／歷程／盤點／webhooks／通知偏好／幣別、穩定排序）；`POST /api/backup/import`（multipart；20 MiB／413；`format_version` 1–4 相容）；plan／apply 兩段式——dry-run 零寫入；create_only 名稱匹配沿用＋重名後綴＋列級容忍；replace 單一交易清空＋全有全無＋`REPLACE` 確認字串；id-map 關聯重建＋批次對帳 invariant；warnings／errors／稽核 `backup.import`；Web「設定 → 整合與資料 → 備份」頁（匯出＋匯入三態）；無 migration |
| 30 | 成員權限細化 | ✅ | `group_members.role`（admin／editor／viewer，owner＝`groups.owner_id`）＋migration 0022；viewer 定義（全部 membership 為 viewer）→ `require_writer`＋`WriterGuardRoute` 套 14 routers（403 早於 body／資源查詢）；owner／admin 成員管理＋角色變更端點＋audit；Web 唯讀一律不渲染入口（一次性 banner／固定句／標籤列印與匯出保留）；群組角色管理 UI |
| 31 | 定期報表（月報） | ✅ | `reports`（`UNIQUE(user_id, period)`、JSON 快照）＋migration 0023；`report.monthly` job 生成上一個完整月（Asia/Taipei；冪等、空月建列不通知、逐使用者隔離）；指標口徑（可見範圍、期間界、quantity_logs delta、借還與逾期、30 天到期、估值月初重建）；`GET /api/reports`／`{id}`（僅本人；他人 404）；`preferences.report_monthly_enabled`；站內 `report_ready`＋雙語 Email（fail-soft、純文字 fallback）；Web `/reports` 清單與詳情、`/settings/reports` 開關、桌面統計下拉＋行動二層群組導覽 |
| 32 | AI 批次入庫＋智慧分類建議 | ✅ | `ai_draft_items`＋`ai_usage`（migration 0024）；伺服器端狀態機（非終態可重入、終態 409、錯誤碼化）＋逐張序列處理（不引入背景 worker）；`/api/ai/drafts` 建立／清單／process／accept／discard／批量 discard（writer guard、僅本人）；`suggest-classification` 純規則引擎（分詞／交集評分／決定性排序；僅本人資料、不耗配額）；`AI_DAILY_QUOTA` per-user 每日配額（既有 `suggest-from-image` 額度耗盡轉 429）；Web `/items/drafts` 佇列（上傳區＋四態卡＋批量條＋四態頁面契約）、`AiMark` 記號、`/items/new` 入口卡與待審核徽章（不入首層導覽）；`AuthImage`（既有全站 `<img>` 無 Bearer 破圖之修正）；`docs/ai.md` |
| 33 | AI 收據辨識 | ✅ | `ai_draft_items.receipt_id` 群組鍵＋索引（migration 0025）；`POST /api/ai/receipts` 多頁一次抽取（單一請求、一次配額、失敗不落地）；金額補齊規則（缺單價／缺小計／皆缺／不一致）；每品項一列 `ready` 草稿＋`receipt`／`receipt_item` 快照；對帳（品項合計 vs 收據總額，差額警示不阻擋）；`process` 對收據 409、`accept` 不綁收據照片；同圖去重限定 `batch_photo`；`suggest_for_names` 批次化（與逐次呼叫等價）；Web 上傳區照片／收據 Tabs、佇列分組與群組標頭、卡片小計與數量／成本預填；`docs/ai.md` 收據章節 |
| 34 | AI 自然語言搜尋＋物品問答 | ✅ | `GET /api/items` 擴充 `loan`／`min_quantity`／`max_quantity`／`sort(name_asc,created_desc)`；`POST /api/ai/search`（LLM → 白名單 filters → 名稱解析 → 既有搜尋；`applied`／`unresolved`；fallback 一律 200：`ai_disabled`／`quota_exhausted`／`upstream_error`／`unparsed`，未呼叫 LLM 不扣配額）；`POST /api/ai/ask`（`item_ids` 或分詞上下文、`[#n]` 引用映射、`grounded=false`、403／503／429／502）；偏好 `ai_data_sharing_enabled`（預設關，未開啟 403；僅送摘要）；`<<<DATA>>>` 注入防護＋白名單＋引用邊界；golden eval 24 句（mock 進 CI、`EVAL_LIVE=1` 手動）；Web AI 搜尋列與「理解為」chip、問答面板、設定開關；`docs/ai.md` 搜尋／問答章節 |
| 35 | AI stub 模式（可測的 AI 成功路徑） | ✅ | `AI_MODE=live|stub`（非 dev 環境啟用 stub 啟動即失敗）；攔截點在 LLM 唯一出口（`ai_service` 四個 `call_gemini_*`）且 stub 回**原始 JSON 文字** → 解析／白名單／名稱解析／對帳／引用映射路徑完全相同；stub 供應器（建議／收據／問答／搜尋確定性規則轉譯器）；`ai_enabled()` 統一啟用判定（取代五處 key 檢查）；stub 不需 key、不消耗配額、**不豁免** opt-in；`GET /api/ai/status`（純新增唯讀端點）；Playwright 專案 `ai-stub`＋4 情境（收據品項→對帳→入庫、搜尋 chip、問答引用、批次入庫）→ 補上 Phase 32–34 最大測試缺口；一併修正問答上下文選取非決定性（`PYTHONHASHSEED` 相關 flake）；`docs/ai.md` stub 章節 |
| 36 | 位置 QR 標籤 | ✅ | `GET /api/locations/{id}/qr.png`＋`/label`（純新增；含子孫物品數；他人位置 404）；深連結 `/items?location={id}`（沿用既有物品列表位置篩選，含子孫 → 不新增目的地頁）；掃碼分流 `item → location → 條碼 → 名稱`（手動輸入同）；列印頁 `/locations/labels`（`?ids=` 直接產生／無 ids 列出位置供勾選一次印多個）；位置樹節點選單「列印標籤」＋頁首入口；`locations.labels.*` i18n 9 鍵 |
| 37 | 標籤列印加印條碼 | ✅ | 物品標籤加印 **Code128 條碼圖**（`bwip-js` 產生 SVG，動態載入；單張／批量標籤與物品詳情頁）；條碼數字仍以文字呈現；**可編碼性自行驗證**（僅可列印 ASCII；`bwip-js` 對中文不報錯但會產生亂碼條碼 → 擋掉並退回純文字，標籤仍可列印）；QR 內容改以 `zxing-cpp` **真值解碼**驗證（取代近似比對）；補上倉庫缺失的 `LICENSE` 檔（README 已宣稱 MIT） |
| 38 | 收據證據鏈 | ✅ | 移植 itemly（MIT）驗證語意：`calculated_total = Σ品項小計 − 折扣 + 稅 + 運費`；對帳四態（balanced／discrepancy／incomplete／unknown）；抽取擴充 subtotal／discount／tax／shipping＋品項 discount／tax；`uncertain_fields`（AI 自述不確定，白名單過濾）；幣別未知 → `XXX`；缺價品項 → 待補價數；群組標頭顯示算術拆解與旗標（舊快照相容）；`ReceiptSnapshot` 純新增 8 欄位（api-types 零破壞性） |
| 39 | 稽核查詢 UI | ✅ | `GET /api/admin/audit-logs` 改分頁信封（`items`／`total`／`limit`／`offset`／`facets`；`limit` 預設 50、上限 500）；篩選 `action`／`resource_type`／`user_id`／`q`（涵蓋 action／resource_type／resource_id／meta，LIKE 萬用字元轉義）／`created_from`／`created_to`（含頭不含尾、顛倒 → 422）；`user_email` 以 LEFT JOIN 取得；facets 為全域（每維度前 50，count desc → value asc）；`GET /api/admin/audit-logs/export.csv`（UTF-8 BOM、csv 轉義、上限 10,000 列）；Web 查詢台（debounce／當地日界 → UTC／分頁／meta 展開／CSV 下載／行動卡片／錯誤重試）；**無 migration** |
| 40 | 稽核覆蓋擴充 | ✅ | 新增 7 種 action（共 12 種）：`auth.login`／`auth.login_failed`（只記既有帳號、同一帳號 10 分鐘去重；陌生帳號不寫）／`item.deleted`（meta 記名稱）／`item.bulk_deleted`（1 筆摘要、`count`＋`item_ids`）／`token.created`／`token.deleted`（只記 name，不記原文或雜湊）／`user.password_changed`；呼叫點一律在主寫入 commit 後、webhook 前；`backup.export` 明確不納入；無 migration、無 Web 改動（facets 自動出現新值） |
| 41 | 伺服器端標籤 PDF | ✅ | `GET /api/items/labels.pdf?ids=…&start=0`（純新增）：A4 3×7＝21 張、63.5×38.1 mm、淺灰裁切線；每張 QR（既有深連結）＋Code128＋名稱（2 行截斷）＋短 id／數量；`start` 0–20 可重用部分貼紙；ids 去重 1–100、任一筆不可見 → 404（全有全無）；`reportlab`＋`python-barcode`；內嵌 Noto Sans TC 子集（OFL）→ PDF 只嵌用到的字形；`pypdfium2` raster＋`zxing-cpp` 真值解碼 QR／Code128；Web 批量標籤頁「下載 PDF」；**無 migration** |
| 42 | 定期報表（週報） | ✅ | `reports.kind`＋`period` 放寬至 10（migration 0026；downgrade 刪週報列後縮回 7）；`report.weekly` 每週一生成上一個完整 ISO 週（Asia/Taipei；冪等、空週建列不通知、逐使用者隔離、無可見物品跳過）；`report_weekly_enabled` 預設 **false**（opt-in）；週報／月報共用 `build_payload`、`ReportPayload`（新增 `kind`，舊快照預設 monthly）、`report_ready`＋Email 管線；`ReportRead.kind`；清單改 `generated_at DESC`；`JobSpec.stale_after_hours`（expiry 26h／weekly 170h／monthly 770h）修正月報誤判停跑；Web 清單徽章＋日期範圍、詳情週報文案、設定雙開關、空狀態分流；**無新增端點** |

## 測試規模

- API 測試：1248 passed（pytest-asyncio + FastAPI TestClient + aiosqlite）＋ golden eval 28（mock 模式）
- Web 測試：787 passed（132 檔；vitest + @testing-library/react + jsdom）
- Playwright e2e：**29 spec／93 情境**（`chromium` 專案 28 spec／89 情境：登入／物品／批次到期／清單／通知／通知偏好／提醒排程／月報／**週報**／AI 批次入庫／AI 收據辨識／AI 自然語言搜尋與問答／位置 QR 標籤／標籤條碼／**標籤 PDF 下載**／掃碼／位置樹／估值／webhook 管理／備份還原／成員角色權限／**稽核查詢台**／主題等關鍵流程；`ai-stub` 專案 1 spec／4 情境：Phase 35 新增的 **AI 成功路徑**——收據品項→對帳→入庫、搜尋「理解為」chip、問答引用連結、批次入庫）

## 下一輪（未排程）

Phase 22–42 已全部上線；整體狀態、驗證基線與已知限制見 [`docs/progress-2026-10-23.md`](progress-2026-10-23.md)。

候選項目（依建議優先序，粗估含測試與 i18n）：

| # | 項目 | 說明 | 粗估 |
|---|------|------|------|
| 1 | 收據人工核對流程 | 借 itemly 的「使用者確認收據」概念：群組層可標記已人工核對（差額不再警示）＋整張收據視圖 | M |
| 2 | 批次成本（per-batch cost） | Phase 27 延伸；需 migration 與估值口徑調整 | M |
| 3 | 分享唯讀連結 | 對外展示清單；**隱私設計需先定案**（token 範圍／到期／撤銷） | M |
| 4 | 樓層平面圖互動 | 點熱區篩選位置物品（`floor_plan_image_id` 已存在） | S–M |
| 5 | Background Sync（離線新增） | IndexedDB 佇列＋SW sync；衝突處理複雜 | L |
| 6 | v1 目錄下線 | 打 `v1-final` tag 後移除 `app/`、`templates/`、`static/`、`run_worker.py` | S |
| 7 | `AuthImage` blob 快取 | 記憶體快取避免同一圖片重複下載 | S |
| 8 | 登入防暴力破解 | 帳號鎖定／指數退避／CAPTCHA（目前僅稽核去重，無 rate limit） | S–M |

> 建議節奏：下一棒是 **#8 登入防暴力破解**（使用者指定，與 Phase 40 的稽核互補：一個負責「看得到」，一個負責「擋得住」）；#1、#2 需設計決策，建議單獨開 phase 並先寫決策段；#5 成本最高，建議最後或另開里程碑；#6、#7 可合併成一個「收尾清理」phase。

## 快速啟動（v2）

```bash
cp .env.example .env
pnpm install
docker compose up --build
# 開啟 http://localhost/
```

首次啟動需跑一次 Alembic：容器內會自動執行 `alembic upgrade head`；若本機跑則：

```bash
cd apps/api
.venv/bin/alembic upgrade head
```

詳細部署步驟見 [Deployment_Guide_zh-TW.md](../Deployment_Guide_zh-TW.md)。

## 與 v1 的關係

v1（Flask + Jinja2）程式碼仍保留於 `app/`、`templates/`、`static/` 等目錄作為唯讀參考。

- **不接受新功能**：所有新功能都進 `apps/web` + `apps/api`
- **沒有資料遷移**：採 Big Bang 切換，v1 使用者需在 v2 重新註冊。v1 的 CSV/JSON 匯出可匯入到 v2（見 Phase 14）
- **legacy tag**：未來會打 `v1-final` tag 保留 v1 快照，再從 main 移除這些目錄

## 後續候選（尚未排程）

> **2026-10-15 更新**：新一輪規劃（Phase 22–34）已移至 [`plans/2026-10-15-next-iteration-roadmap.md`](plans/2026-10-15-next-iteration-roadmap.md)，涵蓋批次到期管理、通知偏好、排程自動化、條碼掃描、位置樹重建、估值、Webhook UI、備份還原、權限細化、定期報表與 AI 深化。原候選處置如下：

1. **Background Sync**：本次未排入，保留於新 roadmap 的〈未排程候選〉
2. **多 location 階層**：已排入 → 新 roadmap Phase 26（多層位置樹重建）
3. **Webhook retry UI**：已排入 → 新 roadmap Phase 28（Webhook 管理 UI）
4. **備份還原**：已排入 → 新 roadmap Phase 29（備份與還原）

排程時請把選定項目升成正式 phase，走既有的 worktree → 測試 → merge 節奏。
