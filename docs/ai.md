# AI 功能（Gemini 辨識＋批次入庫＋智慧分類建議）

本文件說明 Phase 3 起的 AI 辨識端點，以及 Phase 32 新增的「AI 批次入庫（草稿佇列）」與「智慧分類建議」。
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

## 智慧分類建議（規則引擎）

`app/services/classification_service.py`——純規則、決定性、不呼叫 LLM，因此 LLM 不可用或配額耗盡時仍可運作。

- **分詞**：NFKC 正規化 ＋ lower；拉丁／數字連續片段（長度 ≥ 2）取整段；CJK 取 bigram（單一 CJK 字元保留）。
- **評分**：與歷史物品名稱的 token 交集大小；分類／位置／標籤以 `(score, item_count)` 聚合，完全決定性排序（`score` desc → `item_count` desc → `id`／`name` asc）。
- **護欄**：僅掃描 `owner_id` 本人、未刪除物品，`ORDER BY items.id LIMIT 2000`；**不含**群組可見的他人物品。
- **隱私**：建議只來自本人歷史資料；`category_id`／`location_id` 為 `null` 的物品不產生「未分類／未指定」建議。
- Web 端使用時機：草稿卡「依歷史建議」按鈕（以卡片名稱即時查詢）；AI 辨識成功時，`process` 亦會以 AI 名稱查一份歷史建議存入 payload（`ai` 與 `history` 同時存在），作為卡片預設值（歷史優先，歷史缺分類時退回 AI 建議的完整同名分類）。

## Web 動線

- 入口：`/items/new` 頁首的「AI 批次入庫」卡（徽章「N 筆待審核」只計活動四態）；**不入首層導覽**（計畫 D9）。
- 佇列：`/items/drafts`（物品域子路由）——上傳區（拖放／多檔、單次上限 10、單檔失敗重試、建立失敗區塊重試）、逐張處理迴圈、四態草稿卡、批量條；頁首「改為手動新增」回到 `/items/new`。
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
| e2e／CI 全數失敗 | 預期行為：`.env` 無 key 時走 `ai_disabled` 路徑，`tests/ai-drafts.spec.ts` 正是驗證此路徑（上傳→失敗→依歷史→手動接受） |

## 測試

- API：`cd apps/api && uv run pytest -q`（草稿狀態機、配額、規則引擎、權限與批量丟棄）。
- Web：`cd apps/web && pnpm vitest run`（客戶端／hooks／四態卡／佇列迴圈／入口卡／i18n 對帳）。
- E2E：`cd apps/web && pnpm exec playwright test`（`tests/ai-drafts.spec.ts`：無 key 失敗路徑、批量丟棄、入口徽章）；機器負載高時可加 `--workers=2` 降低 UI timeout 型 flake。
