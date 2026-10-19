# Changelog

本專案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式與 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

v2 為全面重寫版（Next.js + FastAPI monorepo，位於 `apps/`），v1 為 Flask + Jinja2（保留於 `app/`、`templates/` 目錄；參見 [`legacy-v1` 章節](#legacy-v1-保留))。

## [Unreleased]

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
