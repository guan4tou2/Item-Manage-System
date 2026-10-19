# Phase 33 — AI 收據辨識（多頁收據 → 品項草稿 → 帶成本入庫）

- **日期**：2026-10-19
- **狀態**：規劃完成，待執行
- **依據**：`docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 33、§5.4（互動狀態契約）、§5.6（AI 標記／金額格式）、§九風險 3（Gemini 成本／配額）
- **依賴**：Phase 32（草稿表、狀態機、`DraftCard`／`DraftUploadZone`／批量條、`classification_service`、`ai_quota`）、Phase 27（`items.cost` 與 `formatCurrency`）
- **規模**：M（API 1 個新端點＋LLM 抽取層＋規則引擎批次化＋migration 0025；Web 上傳區模式切換＋佇列分組標頭；e2e 1 spec）

---

## 目標

拍（或選）一至多張同次採購的收據 → Gemini 一次抽取商家、日期、總額與品項（名稱／數量／單價／小計）→ **每個品項一列 `ready` 草稿**，進 Phase 32 同一套草稿佇列與卡片審核 → 確認後建立物品並帶入 `cost`／`quantity`。分類／位置／標籤建議沿用 Phase 32 的本人歷史規則；收據品項合計與收據總額不符時顯示**對帳提示**（不阻擋）。

---

## 範圍

### 收據抽取（API）

- `POST /api/ai/receipts`：body `{image_ids: [uuid, ...]}`（1–10 頁）→ **同步**呼叫 Gemini（多頁一次送出）→ 每個品項建立一列 `source='receipt'`、`status='ready'` 草稿（共用 `receipt_id`）
- 抽取欄位：商家、購買日期、幣別、收據總額、品項（名稱、數量、單價、小計）
- 失敗語義（HTTP 錯誤＋`detail` 代碼）：`ai_disabled` 503／`quota_exhausted` 429／`upstream_error` 502／`no_items` 422
- 品項上限 50：超出時**截斷**並以 `truncated=true` 回報（不靜默、不整批失敗）

### 草稿佇列（Web，重用 Phase 32）

- 佇列頁新增「收據」模式：多頁選取 → 抽取中 → 成功後群組入列／失敗顯示錯誤區塊＋重試
- 收據草稿依 `receipt_id` **分組**，群組標頭顯示商家 · 日期 · 頁數 · 品項數 · 對帳結果（相符／差額警告）
- 收據卡片沿用 `DraftCard`：帶入 `quantity`／`cost`、顯示「收據小計」、可編輯後接受或丟棄
- 批量條沿用（收據草稿為 `ready`，可被「全部接受」涵蓋）

### 明確不在本期範圍

- 收據 PDF／掃描檔（僅影像）、QR／條碼自動帶入載具或發票號碼
- 自動建立不存在的分類／位置（僅建議既有項目）
- 幣別換算（收據幣別僅記錄與顯示；物品成本以使用者偏好幣別語義儲存，與 Phase 27 一致）
- 跨收據去重、收據群組的整體操作（一次接受全部品項／整組丟棄）——仍以逐張與既有批量條為準
- 收據原檔保存期限管理、匯出
- 背景 worker／串流（與 Phase 32 同：請求內完成）
- 新排程 job（`docs/scheduling.md` 不動）

---

## 關鍵設計決策

### D1 資料模型：品項草稿＋群組鍵（migration 0025）

- `ai_draft_items` 新增 `receipt_id UUID NULL`（**無 FK**；同次收據的群組鍵）＋索引 `(owner_id, receipt_id)`
- 每個收據品項一列草稿：`source='receipt'`、`status='ready'`、`image_id`＝收據照片（供卡片縮圖）、`receipt_id` 相同
- 不新增 `ai_receipts` 父表：群組沒有獨立生命週期（全部品項進入終態後群組自然消失），避免「父列孤兒」與額外清理邏輯；收據中繼資料以**快照**存於每列 payload（Phase 31／32 快照慣例）
- `source` CHECK 已允許 `receipt`（Phase 32 預留）→ 0025 只加欄位與索引

### D2 payload 契約（version 1 向後相容擴充）

```json
{
  "version": 1,
  "ai": {
    "name": "鮮乳",
    "description": null,
    "category_suggestion": "食品",
    "tag_suggestions": ["乳製品"]
  },
  "history": { "category": null, "location": null, "tags": [] },
  "receipt": {
    "merchant": "全聯福利中心",
    "purchased_at": "2026-10-18",
    "currency": "TWD",
    "total": "1250.00",
    "item_total": "1240.00",
    "discrepancy": "10.00",
    "page_count": 2,
    "truncated": false
  },
  "receipt_item": {
    "index": 0,
    "quantity": 2,
    "unit_price": "620.00",
    "subtotal": "1240.00"
  }
}
```

- `receipt`／`receipt_item` 為**必填可為 `null`**（`batch_photo` 草稿為 `null`）；`to_read` 以 `.get()` 正規化 Phase 32 既有列（缺鍵 → `null`），**不做資料回填**
- 金額一律 Decimal 字串（2 位）；`purchased_at` 為 `YYYY-MM-DD`；`currency` 為 ISO 4217 或 `null`
- `receipt.item_total`＝伺服器計算的品項小計合計；`discrepancy`＝`total - item_total`（`total` 缺 → `null`）
- `receipt_item.index`＝收據上的行序（0 起），供同組內排序與顯示

### D3 抽取層（`ai_service.call_gemini_receipt`）

- 新 prompt `_RECEIPT_PROMPT`（**不改動**既有 `_PROMPT`）：要求 strict JSON、zh-TW 品名、ISO 日期、十進位字串；明確指示「同一張收據的多頁請合併為一組品項」
- 多頁一次送出（同一請求的多個 `Part.from_bytes`）；回傳 `ReceiptExtraction`（`merchant`／`purchased_at`／`currency`／`total`／`items`）
- **金額補齊規則**（伺服器端，決定性）：
  - 單價缺、小計有 → `unit_price = subtotal / quantity`（四捨五入 2 位）
  - 小計缺、單價有 → `subtotal = unit_price × quantity`
  - 兩者皆缺 → `unit_price = null`、`subtotal = null`（接受時 `cost` 留空，不阻擋）
  - 兩者都有但不一致 → **保留原值**，`item_total` 以 `subtotal` 計（不覆寫 LLM 結果，差異由對帳提示呈現）
- 解析失敗（非 JSON／缺 `items`／`items` 空）→ `no_items`／`upstream_error`

### D4 端點語義（同步建立，不走狀態機）

`POST /api/ai/receipts`

| 情況 | 回應 |
|------|------|
| 成功（1–50 品項） | `201 {receipt_id, created: [DraftRead], truncated: bool}` |
| 圖片不可見／不存在 | `404`（不洩漏存在性） |
| `GEMINI_API_KEY` 未設 | `503`，`detail="ai_disabled"` |
| 當日配額耗盡 | `429`，`detail="quota_exhausted"` |
| 上游錯誤／非 JSON／空回應 | `502`，`detail="upstream_error"` |
| 抽取不到品項 | `422`，`detail="no_items"` |
| `image_ids` 非 1–10 | `422`（Pydantic） |

- **配額**：一次收據＝1 次呼叫（與頁數、品項數無關）；於呼叫前扣並 commit（沿用 `ai_quota.consume`）
- **不建立失敗草稿**：抽取失敗時不落地任何列（重試＝重新送出同一組圖片），因此收據草稿永遠是 `ready`
- `detail` 為**代碼字串**（新端點契約），Web 以 `ai.receipts.errors.*` 對照；其餘既有端點不動
- 端點掛 `WriterGuardRoute`（viewer 403 於路由依賴階段）

### D5 與 Phase 32 狀態機的邊界

- `POST /api/ai/drafts/{id}/process` 對 `source='receipt'` → **409**（`detail="receipt drafts are extracted at creation"`）；避免單張重跑把收據當成物品照片再抽取一次
- 佇列處理迴圈只自動送 `pending`；收據草稿為 `ready` → **不會被自動處理**（零改動即正確）
- `accept`／`discard`／批量 discard 完全不變；「全部接受」對 `ready` 的收據草稿同樣有效（各自帶入 seeding 後的 `cost`／`quantity`）

### D6 accept 語義調整（收據照片不成為物品圖片）

- `accept_draft` 建立物品時：`image_id = None if draft.source == "receipt" else draft.image_id`
- 理由：收據照片不是商品照片；避免物品詳情頁出現收據圖
- 其餘沿用 `items_service.create_item`（`item.created` webhook、低庫存通知、欄位驗證）

### D7 同圖去重（回歸修正）

- Phase 32 的建立去重（同圖活動草稿）加上 `source='batch_photo'` 條件
- 否則「收據照片同時被當一般照片上傳」會互相誤擋；收據端點本身不去重（重送＝新的一組草稿，可丟棄）

### D8 規則引擎批次化（`classification_service.suggest_for_names`）

- 收據一次最多 50 品項；逐品項呼叫 `suggest_for_name` 會掃描歷史 50 次
- 新增 `suggest_for_names(session, owner_id, names) -> list[ClassificationSuggestions]`：**單次**載入歷史列（同一 `MAX_SCAN` 護欄）與標籤，逐一比對名稱 token
- `suggest_for_name` 改為 `(await suggest_for_names(..., [name]))[0]`（單一行為來源）
- **等價性測試**：同一組歷史下，批次結果與逐次呼叫完全相同（含排序）

### D9 佇列分組與對帳顯示（Web）

- 純函式 `groupDrafts(drafts)`（`lib/ai/receipts.ts`）：
  - `batch_photo` 草稿維持原位、無標頭
  - 同 `receipt_id` 的草稿聚為一組，組內依 `receipt_item.index` 升冪；組的順序＝其**第一列在原始清單中的位置**（清單本身 `created_at DESC`，組內 index 升冪＝收據行序）
  - 回傳 `Array<{receiptId: string | null, snapshot: ReceiptSnapshot | null, drafts: DraftRead[]}>`
- 群組標頭 `ReceiptGroupHeader`：商家（缺 → 「未標示商家」）· 日期（缺 → 「未標示日期」）· 「N 頁」· 「M 品項」
  - 對帳：`total` 與 `item_total` 皆存在且 `|discrepancy| ≥ 0.01` → 警示列「品項合計 NT$1,240，與收據總額 NT$1,250 差 NT$10」；相符 → 「與收據總額相符」；`total` 缺 → 「收據未標示總額」（中性）
  - 金額以收據 `currency` 顯示（缺 → 使用者偏好幣別），沿用 `formatCurrency`
- 收據卡片：`DraftCard` 增加可選 `receiptItem` 顯示（「小計 NT$1,240」＋品名旁的 `AiMark` 不變）；`seedDraftValues` 以 `receipt_item.quantity`／`unit_price` 作為預設 `quantity`／`cost`

### D10 上傳區模式切換（Web）

- `DraftUploadZone` 增 `mode: "photo" | "receipt"` 切換（頁面層持有；`Tabs` 兩個分頁）
- 照片模式：行為與 Phase 32 完全相同（逐檔上傳 → 一次建草稿 → 自動處理）
- 收據模式：多頁選取 → 逐檔上傳 → **一次** `createReceipt(image_ids)` → 抽取中顯示「辨識收據中…」→ 成功清空並重整佇列／失敗顯示錯誤區塊（代碼文案）＋「重試」（保留已上傳圖片）
- 收據模式上限同為 10 頁；單檔上傳失敗仍可列內重試

### D11 權限與隱私

- 收據端點：`WriterGuardRoute`；圖片僅限本人可見（`images_service.get_visible`）；草稿僅本人可讀寫（沿用 `get_owned` 404 語義）
- 歷史建議僅本人未刪除物品（沿用 Phase 32 D6）
- 收據內容（商家／品項）僅存於本人草稿 payload；不寫入 log（上游錯誤僅記錄例外訊息）

### D12 i18n 與型別

- 新鍵：`ai.receipts.*`（模式切換、上傳提示、抽取中、錯誤碼、群組標頭、對帳、小計、截斷提示）；zh-TW／en 同鍵同行數
- `DraftPayload` 新增 `receipt`／`receipt_item` → 重生成 api-types（既有 `batch_photo` 契約僅多兩個 nullable 欄位）
- 金額一律 `formatCurrency`；日期用 locale 短格式（`purchased_at` 為純日期，不做時區轉換）

---

## 資料模型（migration 0025）

```
ai_draft_items（既有表）
  + receipt_id  UUID NULL          -- 同次收據群組鍵（無 FK）
  + INDEX ix_ai_draft_items_owner_receipt (owner_id, receipt_id)
```

- 模型：`app/models/ai_draft.py` 新增 `receipt_id` 欄位
- `upgrade`：`add_column` ＋ `create_index`；`downgrade`：`drop_index` ＋ `drop_column`
- 不需資料回填（既有列為 `NULL`）

---

## API payload 範例

### `POST /api/ai/receipts`

```
{ "image_ids": ["<uuid-page1>", "<uuid-page2>"] }
```

```json
201
{
  "receipt_id": "6f1c…",
  "truncated": false,
  "created": [
    {
      "id": "…", "source": "receipt", "status": "ready", "receipt_id": "6f1c…",
      "image_id": "<uuid-page1>", "item_id": null, "error_code": null,
      "payload": { "version": 1, "ai": {...}, "history": {...},
                   "receipt": {...}, "receipt_item": {"index": 0, ...} },
      "processed_at": null, "created_at": "…"
    }
  ]
}
```

- `created` 依 `receipt_item.index` 升冪回傳
- `DraftRead` 新增 `receipt_id`（`null` 表示一般照片草稿）

### 錯誤範例

```json
503 { "detail": "ai_disabled" }
429 { "detail": "quota_exhausted" }
502 { "detail": "upstream_error" }
422 { "detail": "no_items" }
409 { "detail": "receipt drafts are extracted at creation" }   // process 收據草稿
```

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 DB：`receipt_id` ＋ migration 0025

- RED：`tests/test_ai_draft_models.py` 追加（`receipt_id` 可為 `NULL`；同 `receipt_id` 可多列；索引存在）
- GREEN：模型欄位＋`alembic/versions/0025_receipt_drafts.py`
- 驗證：Postgres 容器 `0024 → 0025 → 0024 → 0025`

### T1.2 規則引擎批次化 `suggest_for_names`

- RED：`tests/test_classification_rules.py` 追加（多名稱單次掃描結果；與逐次呼叫等價；空名稱跳過）
- GREEN：`suggest_for_names`＋`suggest_for_name` 改為薄包裝

### T1.3 LLM 收據抽取層

- RED：`tests/test_ai_receipts.py`（mock `google.genai.Client`）
  - 多頁 → 一個請求、多個 Part；strict JSON 解析
  - 金額補齊：缺單價→以小計推、缺小計→以單價推、兩者皆缺→null、不一致→保留原值
  - 非 JSON／空 `items`／SDK 例外 → `AiUpstreamError`
  - `purchased_at` 非 ISO → `null`（不因單一欄位壞掉整批失敗）
- GREEN：`ai_service.call_gemini_receipt`＋`_RECEIPT_PROMPT`＋`ReceiptExtraction` 資料類

### T1.4 `POST /api/ai/receipts`

- RED：`tests/test_ai_receipts.py`
  - 成功：N 品項 → N 列 `ready`、同 `receipt_id`、payload 完整（receipt／receipt_item／history）、`created` 依 index 升冪
  - 配額：一次收據扣 1 次（多頁不多扣）；耗盡 → 429 且不建列
  - 錯誤：未設 key → 503；上游錯誤 → 502；`no_items` → 422；圖片不可見 → 404；>10 頁 → 422
  - 截斷：>50 品項 → 建 50 列、`truncated=true`
  - 權限：viewer → 403；他人圖片 → 404
- GREEN：`app/routes/ai_receipts.py`（或 `ai.py` 擴充）＋`ai_drafts_service.create_receipt_drafts`

### T1.5 狀態機邊界與 accept 調整

- RED：
  - `process` 對 `source='receipt'` → 409
  - `accept` 收據草稿 → 建立的物品 `image_id` 為 `null`（照片草稿仍綁圖）
  - 建立去重只擋 `batch_photo`（收據照片不誤擋）
- GREEN：`process_draft`／`accept_draft`／`create_drafts` 條件調整

### T1.6 api-types 重生成

- `uv run python scripts/export_openapi.py` ＋ `node generate.mjs`；確認既有端點零變動、新增 `/api/ai/receipts` 與 `receipt_id`／`receipt`／`receipt_item`

### T2.1 Web client／hooks／分組純函式

- RED：`lib/api/ai-receipts.test.ts`（`createReceipt` 錯誤碼映射）、`lib/ai/receipts.test.ts`（`groupDrafts`：混合順序、同組 index 排序、缺 snapshot、空清單）
- GREEN：`lib/api/ai-receipts.ts`、`lib/hooks/use-ai-receipts.ts`、`lib/ai/receipts.ts`

### T2.2 `seedDraftValues` 支援收據

- RED：`lib/ai/draft-values.test.ts` 追加（`quantity`／`cost` 來自 `receipt_item`；單價缺 → `cost` 空字串；`batch_photo` 行為不變）
- GREEN：`seedDraftValues` 條件分支

### T2.3 收據上傳區（模式切換）

- RED：`components/ai/draft-upload-zone.test.tsx` 追加
  - 切到收據模式：文案與多頁提示、上限 10
  - 抽取中 → 按鈕 disabled＋「辨識收據中…」
  - 成功 → 清空選取＋重整佇列
  - 失敗（`ai_disabled`／`quota_exhausted`／`upstream_error`／`no_items`）→ 區塊錯誤文案＋重試（保留已上傳圖片）
  - 截斷 → info toast
- GREEN：`mode` 分支＋`createReceipt` 呼叫

### T2.4 群組標頭與收據卡

- RED：`components/ai/receipt-group-header.test.tsx`（相符／差額／未標示總額／缺商家日期／幣別）、`components/ai/draft-card.test.tsx` 追加（收據小計顯示；quantity／cost 預設）
- GREEN：`ReceiptGroupHeader`＋`drafts-client` 分組渲染＋`DraftCard` 小計列

### T2.5 i18n 補齊與對帳

- RED：`lib/i18n/messages.test.ts` 追加 Phase 33 鍵清單
- GREEN：`messages/zh-TW.json`／`en.json` 逐鍵插入（行數一致）

### T3.1 E2E `tests/ai-receipts.spec.ts`

- 情境 1（無 key 路徑）：登入 → `/items/drafts` → 切「收據」→ 選 2 張圖 → 抽取失敗（`ai_disabled` 文案）→ 區塊重試可見 → **不產生任何草稿**（佇列仍為空）
- 情境 2（回歸）：照片模式仍可上傳→失敗→手動接受（Phase 32 行為不變；直接沿用既有 spec，不重複）
- 情境 3：`/items/new` 入口徽章在收據流程失敗後仍為 0
- 註記：成功路徑需 LLM key，e2e 環境無 key → 以 API／元件測試（mock LLM）＋視覺走查（DB 直插 `ready` 收據草稿）覆蓋；計畫收尾記錄此限制

### T3.2 文件收尾

- `docs/ai.md`：收據章節（端點、抽取欄位、金額補齊規則、對帳語義、配額計次、失敗代碼、e2e 無 key 限制）
- `CHANGELOG.md`：`alpha.33`（DB／API／Web／i18n／測試數／migration 0025）
- `docs/v2-roadmap.md`：Phase 33 ✅＋測試規模更新
- 本計畫 Final Verification 實測記錄＋收尾環境註記

---

## 狀態契約（Web，roadmap §5.4）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 收據模式上傳區 | 逐檔上傳＋「辨識收據中…」 | 多頁選取引導（一次最多 10 頁） | 單檔失敗列內重試；抽取失敗區塊（代碼文案）＋重試 | 清空選取、群組入列 | 部分檔上傳失敗仍可重試；截斷以 info toast 告知 |
| 收據群組標頭 | — | — | — | 商家 · 日期 · N 頁 · M 品項＋對帳結果 | 差額 ≥ 0.01 → 警示列（不阻擋接受） |
| 收據卡片 | （不適用：建立即 `ready`） | — | — | 品名＋小計＋數量／單價預填＋`AiMark` | 單價缺 → 成本留空可手動填 |
| 佇列整體 | skeleton ×3 | 引導自上方開始 | 清單錯誤＋重試 | 混合（照片卡＋收據群組） | 逐張處理互不阻擋 |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → ___ passed
- [ ] Web：`pnpm vitest run` → ___ passed（___ 檔）；`pnpm typecheck` → 0 error
- [ ] api-types 重生成零 diff
- [ ] Migration 0025 up／down／up（Postgres 容器）
- [ ] e2e：重建 image 後 `pnpm exec playwright test` → ___ spec／___ passed
- [ ] 視覺走查：桌機 1440×900＋行動 390×844（收據模式上傳區、抽取失敗態、收據群組標頭（相符／差額）、收據卡、批量條）——人工檢視無破版
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

### 收尾環境註記（2026-10-19 起填）

- （待填：worktree 名稱、stack 狀態、e2e 前置與資料種子、無 key 路徑說明）

## 測試基線（main，Phase 32 完成）

- API：984 passed
- Web：649 passed（121 檔）＋typecheck
- E2E：23 spec／71 情境
