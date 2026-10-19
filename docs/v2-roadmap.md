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
| 5 | 通知中心 | ✅ 完成（見下方 Phase 7 外部管道） |
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

## 測試規模

- API 測試：1086 passed（pytest-asyncio + FastAPI TestClient + aiosqlite）＋ golden eval 28（mock 模式）
- Web 測試：717 passed（128 檔；vitest + @testing-library/react + jsdom）
- Playwright e2e：25 spec／79 情境（登入／物品／批次到期／清單／通知／通知偏好／提醒排程／月報／AI 批次入庫／AI 收據辨識／AI 自然語言搜尋與問答／掃碼／位置樹／估值／webhook 管理／備份還原／成員角色權限／主題等關鍵流程）
- 兩套測試套件都是每次 phase 推進 main 前必綠條件

## 下一輪（未排程）

Phase 22–34 已全部上線；整體狀態、驗證基線與已知限制見 [`docs/progress-2026-10-19.md`](progress-2026-10-19.md)。

候選項目（依建議優先序，粗估含測試與 i18n）：

| # | 項目 | 說明 | 粗估 |
|---|------|------|------|
| 1 | **AI stub 模式** | `AI_MODE=stub` 環境開關，讓 e2e 驗證 AI 成功路徑（收據品項／搜尋 chip／問答引用），補上最大測試缺口 | S–M |
| 2 | 位置 QR 標籤 | 掃碼 → 該位置物品清單（貼櫃子／箱子）；平面圖欄位與掃碼流程已在 | S |
| 3 | 稽核查詢 UI | 後端 audit 資料已在，只缺查詢／篩選頁 | S–M |
| 4 | 週報 | 重用月報 job 與 payload 渲染（`report.weekly`） | S–M |
| 5 | 標籤列印加印條碼 | Phase 25 stretch；列印頁已有 | S |
| 6 | 批次成本（per-batch cost） | Phase 27 延伸；需 migration 與估值口徑調整 | M |
| 7 | 分享唯讀連結 | 對外展示清單；**隱私設計需先定案**（token 範圍／到期／撤銷） | M |
| 8 | 樓層平面圖互動 | 點熱區篩選位置物品（`floor_plan_image_id` 已存在） | S–M |
| 9 | Background Sync（離線新增） | IndexedDB 佇列＋SW sync；衝突處理複雜 | L |
| 10 | v1 目錄下線 | 打 `v1-final` tag 後移除 `app/`、`templates/`、`static/`、`run_worker.py` | S |
| 11 | `AuthImage` blob 快取 | 記憶體快取避免同一圖片重複下載 | S |

> 建議節奏：先做 #1（把三個 AI phase 的成功路徑納入 e2e，之後任何 AI 改動都有網），再做 #2–#4（皆 S–M、可獨立驗收）；#6、#7 需設計決策，建議單獨開 phase 並先寫決策段；#9 成本最高，建議最後或另開里程碑。

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
