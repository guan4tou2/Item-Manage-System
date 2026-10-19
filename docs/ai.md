# AI 功能（Gemini 辨識＋批次入庫＋收據辨識＋智慧分類建議）

本文件說明 Phase 3 起的 AI 辨識端點、Phase 32 的「AI 批次入庫（草稿佇列）」與「智慧分類建議」，以及 Phase 33 的「AI 收據辨識」。
相關程式：`apps/api/app/services/ai_service.py`、`ai_drafts_service.py`、`ai_quota.py`、`classification_service.py`；
Web：`apps/web/app/(app)/items/drafts/`、`apps/web/components/ai/`。

## 設定

| 環境變數 | 預設 | 說明 |
|----------|------|------|
| `GEMINI_API_KEY` | 空字串 | 未設定＝**AI 停用**。影像辨識一律失敗（`error_code=ai_disabled`）；歷史規則與手動填寫不受影響 |
| `AI_DAILY_QUOTA` | `50` | 每位使用者每日 LLM 呼叫上限（Asia/Taipei 換日）；`<= 0` 表示不設限 |

- 兩者皆由 `apps/api/app/config.py`（`Settings`）讀取；`.env` 會被 compose 的 `api`／`worker` 服務載入。
- 沒有新增排程 job：草稿處理一律由使用者請求觸發（前端逐張序列送出），故 `docs/scheduling.md` 不需變更。

## 草稿生命週期與狀態機

```
pending ──process──▶ processing ──▶ ready ──accept──▶ accepted
   ▲                     │              │
   └──process（可重入）────┘            ├──discard──▶ discarded
                        └──▶ failed ────┴──accept（手動完成）／process（重試）
```

- 狀態值：`pending`／`processing`／`ready`／`failed`（活動四態）＋ `accepted`／`discarded`（終態）。
- **伺服器端為唯一事實來源**（計畫 D1）：處理在請求內完成（同步；不引入背景 worker）。
- `POST /api/ai/drafts/{id}/process`：
  - 非終態皆可進入（`processing` 可重入，用於前端卡住時的「重新辨識」復原）；終態 → `409`。
  - 一律以 `200` 回最終狀態（業務性失敗不是 HTTP 錯誤）。
  - 失敗寫入 `error_code`：`ai_disabled`（缺 API key）／`quota_exhausted`（當日額度用完）／`upstream_error`（上游錯誤）／`image_missing`（圖片已不存在）。
- **手動完成**：`failed → accepted` 允許（使用者在卡片展開「手動填寫」後直接接受，代表人工補齊）；`pending`／`processing` → accept 為 `409`。
- 接受時以 `items_service.create_item` 建立物品（沿用欄位驗證、`item.created` webhook、低庫存通知）；物品建立成功後才把草稿寫為 `accepted` 並回填 `item_id`（同一 transaction）。

### 狀態契約（Web，計畫 D11）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 入口卡（`/items/new`） | 計數「確認中…」 | 僅入口與一行引導 | 計數失敗隱藏徽章、入口仍可用 | 「N 筆待審核」＋CTA | — |
| 上傳區（`/items/drafts`） | 逐檔上傳中 | 拖放／選檔引導（一次最多 10 張） | 單檔失敗列內重試；建立失敗區塊重試 | 清空選取、草稿入列並自動處理 | 部分檔成功／失敗各自標示 |
| 草稿佇列 | skeleton ×3 | 引導自上方開始 | 清單錯誤＋重試 | 卡片＋批量條 | 逐張處理互不阻擋 |
| 草稿卡 | 辨識中（spinner） | — | 錯誤碼文案＋重試＋手動填寫 | AI 欄位＋「依歷史」徽章＋接受／丟棄 | 接受中／丟棄中僅本卡 loading |
| 批量條 | 接受進度「3/5」 | 未選取 → disabled | 逐筆失敗 toast | 「已接受 N 筆／已丟棄 N 筆」 | 含非 `ready` → 跳過並提示 |

- 自動續行只針對 `pending`；`processing` 不自動重送；`failed` 一律手動重試。
- 處理迴圈嚴格序列（同時 1 張）；傳輸層錯誤（斷網等）→ 停止＋「繼續處理」；業務失敗（200＋`failed`）不中斷。

## API 端點

| 方法／路徑 | 語義 |
|-----------|------|
| `POST /api/ai/suggest-from-image` | Phase 3 既有：單張圖片 LLM 建議（`{image_id, hint?}`）；消耗配額，額度耗盡 → `429` |
| `POST /api/ai/suggest-classification` | 智慧分類建議（規則式，唯讀）：`{name}` → `{category, location, tags}`；**不呼叫 LLM、不消耗配額、不掛 writer guard** |
| `POST /api/ai/drafts` | 批次建立草稿：`{image_ids: [1–10]}` → `201 {created, skipped_image_ids}`；同一圖片已有活動草稿（`pending`／`processing`／`ready`）→ 略過 |
| `GET /api/ai/drafts` | 清單：`?status=&limit=&offset=`（省略 `status` → 活動四態）；`created_at DESC`；回應含 `total` 與**六態** `counts` |
| `POST /api/ai/drafts/{id}/process` | 辨識（狀態機見上） |
| `POST /api/ai/drafts/{id}/accept` | 接受並建立物品：`{name(必填), description?, category_id?, location_id?, tag_names?, quantity?(預設 1), cost?}` → `{draft, item}`；`ACCEPTABLE_STATUSES=(ready, failed)`，其餘 `409` |
| `POST /api/ai/drafts/{id}/discard` | 丟棄單張 → `200 DraftRead`（`discarded`） |
| `POST /api/ai/drafts/discard` | 批量丟棄：`{ids: [1–50]}` → `{discarded, skipped:[{id, reason}]}`；終態或不存在者入 `skipped`（`not found`／`already accepted`／`already discarded`），逐筆隔離不整批失敗 |
| `POST /api/ai/receipts` | **收據辨識**：`{image_ids: [1–10 頁]}` → `201 {receipt_id, truncated, created}`；每個品項一列 `ready` 草稿（詳見下節） |

- 所有草稿讀寫僅限本人（他人／不存在一律 `404`）。
- `/api/ai/drafts` 全部端點掛 `WriterGuardRoute`（viewer → `403`，於路由依賴階段，不洩漏資源存在性）；`suggest-classification` 維持開放（唯讀）。
- 批量「全部接受」沒有專屬端點：前端對選取的 `ready` 草稿逐一呼叫 accept，逐筆錯誤隔離。

### 草稿 payload（`version=1`）

```json
{
  "version": 1,
  "ai": {"name": "咖啡濾杯", "description": "陶瓷手沖濾杯",
         "category_suggestion": "廚房用品", "tag_suggestions": ["咖啡"]},
  "history": {"category": {"id": 3, "name": "廚房用品", "item_count": 12, "score": 4},
              "location": {"id": 7, "name": "廚房", "item_count": 9, "score": 3},
              "tags": [{"name": "咖啡", "item_count": 6, "score": 3}]}
}
```

- `ai` 在 AI 停用／失敗時為 `null`；`history` 只在 **AI 成功**時以 AI 名稱查詢填入（無 key 時為空結構 `{"category": null, "location": null, "tags": []}`）。
- **無 API key 時佇列仍可用**：卡片可即時按「依歷史建議」（呼叫 `suggest-classification`，帶入使用者輸入的名稱）或直接展開「手動填寫」完成入庫。
- 全欄位必填（`null` 代表「無建議」），沿用 Phase 31 的 payload 契約慣例。
- 收據草稿另有兩個欄位（照片草稿為 `null`）：

```json
{
  "receipt": {"merchant": "全聯福利中心", "purchased_at": "2026-10-18",
              "currency": "TWD", "total": "1250.00", "item_total": "1240.00",
              "discrepancy": "10.00", "page_count": 2, "truncated": false},
  "receipt_item": {"index": 0, "quantity": 2, "unit_price": "620.00", "subtotal": "1240.00"}
}
```

## AI 收據辨識（Phase 33）

`POST /api/ai/receipts`——多頁收據**一次**送交 Gemini 結構化抽取，每個品項建立一列 `source='receipt'`、`status='ready'` 的草稿，進入 Phase 32 同一套佇列與卡片審核。

- **一次呼叫＝1 次配額**（與頁數、品項數無關）；於呼叫前扣並 commit。
- **同步完成**（不引入背景 worker）；抽取失敗時**不落地任何列**，重試＝重新送出同一組圖片。
- **群組**：同次收據的所有品項草稿共用 `receipt_id`（`ai_draft_items.receipt_id`，無 FK；migration `0025`）；佇列頁以群組標頭呈現商家、日期、頁數、品項數與對帳結果。
- **抽取欄位**：商家、購買日期（ISO）、幣別、收據總額、品項（名稱／數量／單價／小計）。
- **金額補齊**（伺服器端，決定性）：
  | 情況 | 處理 |
  |------|------|
  | 單價缺、小計有 | `unit_price = subtotal / quantity`（2 位四捨五入） |
  | 小計缺、單價有 | `subtotal = unit_price × quantity` |
  | 兩者皆缺 | 皆 `null`；接受時成本留空（可手動填，不阻擋） |
  | 兩者都有但不一致 | **保留原值**，差異由對帳提示呈現 |
- **對帳**：`item_total`＝各品項小計合計；`discrepancy = total - item_total`。`|discrepancy| ≥ 0.01` → 群組標頭顯示警示列（**不阻擋接受**）；相符 → 顯示「與收據總額相符」；`total` 缺 → 「收據未標示總額」。
- **品項上限 50**：超出截斷並回 `truncated=true`（前端以 info toast 告知）。
- **狀態機邊界**：`POST /api/ai/drafts/{id}/process` 對收據草稿一律 `409`（建立即抽取完成，避免把收據當單品照片重跑）。
- **accept 語義**：收據草稿建立的物品**不帶** `image_id`（收據照片不是商品照片）；`quantity`／`cost` 由卡片預填收據數量與單價。
- **同圖去重**：Phase 32 的「同圖活動草稿略過」只套用 `source='batch_photo'`，收據照片不會誤擋一般照片草稿。

### 錯誤代碼（`detail` 為代碼字串）

| HTTP | `detail` | 意義 |
|------|----------|------|
| `503` | `ai_disabled` | `GEMINI_API_KEY` 未設定 |
| `429` | `quota_exhausted` | 當日配額耗盡 |
| `502` | `upstream_error` | 上游錯誤／非 JSON／空回應 |
| `422` | `no_items` | 抽取不到可用品項（無名稱或 `items` 為空） |
| `404` | — | 圖片不可見／不存在／檔案不在磁碟 |
| `409` | `receipt drafts are extracted at creation` | 對收據草稿呼叫 `process` |
| `403` | — | viewer（`WriterGuardRoute`） |

## 智慧分類建議（規則引擎）

`app/services/classification_service.py`——純規則、決定性、不呼叫 LLM，因此 LLM 不可用或配額耗盡時仍可運作。

- **分詞**：NFKC 正規化 ＋ lower；拉丁／數字連續片段（長度 ≥ 2）取整段；CJK 取 bigram（單一 CJK 字元保留）。
- **評分**：與歷史物品名稱的 token 交集大小；分類／位置／標籤以 `(score, item_count)` 聚合，完全決定性排序（`score` desc → `item_count` desc → `id`／`name` asc）。
- **護欄**：僅掃描 `owner_id` 本人、未刪除物品，`ORDER BY items.id LIMIT 2000`；**不含**群組可見的他人物品。
- **隱私**：建議只來自本人歷史資料；`category_id`／`location_id` 為 `null` 的物品不產生「未分類／未指定」建議。
- Web 端使用時機：草稿卡「依歷史建議」按鈕（以卡片名稱即時查詢）；AI 辨識成功時，`process` 亦會以 AI 名稱查一份歷史建議存入 payload（`ai` 與 `history` 同時存在），作為卡片預設值（歷史優先，歷史缺分類時退回 AI 建議的完整同名分類）。
- **批次化**：`suggest_for_names(session, owner_id, names)` 供收據使用——單次掃描歷史（同一 `MAX_SCAN` 護欄）、歷史名稱 token 只算一次，結果與逐次呼叫 `suggest_for_name` **完全相同**（含排序與分數）。

## Web 動線

- 入口：`/items/new` 頁首的「AI 批次入庫」卡（徽章「N 筆待審核」只計活動四態）；**不入首層導覽**（計畫 D9）。
- 佇列：`/items/drafts`（物品域子路由）——上傳區（拖放／多檔、單次上限 10、單檔失敗重試、建立失敗區塊重試）、逐張處理迴圈、四態草稿卡、批量條；頁首「改為手動新增」回到 `/items/new`。
- **上傳區兩種模式**（`Tabs`）：
  - **照片**：Phase 32 行為（逐檔上傳 → 建草稿 → 自動逐張辨識）
  - **收據**：多頁上傳 → 一次抽取（顯示「辨識收據中…」）→ 群組入列；失敗以代碼文案＋「重試」（保留已上傳頁面）；`truncated` 以 info toast 告知
- **收據群組**：同 `receipt_id` 的卡片聚為一組，組內依收據行序；群組標頭顯示商家 · 日期 · N 頁 · M 品項＋對帳結果；卡片右上顯示「小計 {金額}」。
- viewer（唯讀）在兩頁皆顯示 `ViewerNotice`，不發出草稿查詢。
- AI 產出欄位以 `AiMark`（`sparkles` 記號＋tooltip「由 AI 產生，可編輯」）標示；歷史建議以文字徽章「依歷史：{名稱}」標示（禁用漸層／發光動畫）。

## 疑難排解

| 症狀 | 原因與處理 |
|------|-----------|
| 卡片全部「辨識失敗」＋「AI 未設定（缺少 API 金鑰）」 | `.env` 的 `GEMINI_API_KEY` 為空。設好 key 後重啟 `api`／`worker` 容器，或在卡片上「重試辨識」 |
| 失敗訊息「今日 AI 額度已用完」 | 當日 `AI_DAILY_QUOTA` 用盡（per-user、Asia/Taipei 換日）。調高 `AI_DAILY_QUOTA` 或隔日再試；歷史建議與手動填寫不受影響 |
| 失敗訊息「AI 服務暫時無法使用」 | 上游（Gemini）錯誤或超時；直接重試即可（重試會再次計次） |
| 失敗訊息「照片已不存在」 | 圖片被刪除；重新上傳照片建立新草稿 |
| 舊端點 `suggest-from-image` 回 `429` | 配額耗盡（Phase 32 起既有端點亦受配額限制） |
| 「依歷史建議」沒有結果 | 本人歷史中沒有 token 交集的名稱；先建立幾筆同名／近名物品，或直接手動選分類 |
| 上傳後沒出現卡片 | 同一圖片已有活動草稿會被略過（上傳區會提示略過張數）；重新整理佇列確認 |
| 收據模式顯示「AI 未設定（缺少 API 金鑰）；無法辨識收據」 | 與照片模式同因：`GEMINI_API_KEY` 為空。**失敗不產生任何草稿**，設好 key 後直接按「重試」（已上傳頁面保留） |
| 收據模式顯示「這些頁面讀不到品項」 | 抽取不到可用品項（`no_items`）：影像過暗／模糊／非收據，或品項全無名稱。改拍清晰頁面後重試 |
| 收據群組顯示差額警示 | 品項小計合計與收據總額不同（≥ 0.01）。**不阻擋接受**：可先修正數量／成本再接受，或直接接受（例如運費／折扣未列為品項） |
| 收據卡片「成本」是空的 | 該品項單價與小計皆無法讀取；手動填入即可（不阻擋接受） |
| 收據品項只進來 50 筆 | 伺服器品項上限 50（`MAX_RECEIPT_ITEMS`）；超出截斷並以 toast 告知，可拆成多次收據 |
| 對收據草稿呼叫 `process` 回 `409` | 預期行為：收據於建立時即抽取完成，不支援單張重跑 |
| e2e／CI 全數失敗 | 預期行為：`.env` 無 key 時走 `ai_disabled` 路徑，`tests/ai-drafts.spec.ts`（照片）與 `tests/ai-receipts.spec.ts`（收據）正是驗證此路徑 |

## 測試

- API：`cd apps/api && uv run pytest -q`（草稿狀態機、配額、規則引擎、收據抽取與金額補齊、權限與批量丟棄）。
- Web：`cd apps/web && pnpm vitest run`（客戶端／hooks／四態卡／佇列迴圈／收據上傳與分組／對帳／入口卡／i18n 對帳）。
- E2E：`cd apps/web && pnpm exec playwright test`（`tests/ai-drafts.spec.ts`：照片無 key 失敗路徑、批量丟棄、入口徽章；`tests/ai-receipts.spec.ts`：收據無 key 失敗、重試、模式切換、徽章）；機器負載高時可加 `--workers=2` 降低 UI timeout 型 flake。
- **e2e 限制**：CI／本機 `.env` 無 `GEMINI_API_KEY`，收據成功路徑（品項草稿、對帳、成本預填）以 API 測試（mock `google.genai.Client`）＋元件測試＋視覺走查（DB 直插 `ready` 草稿）覆蓋。
