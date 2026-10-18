# Phase 32 — AI 批次入庫＋智慧分類建議

- **日期**：2026-10-19
- **狀態**：規劃完成，待執行
- **依據**：`docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 32、§5.2（設定／入口）、§5.3（導覽契約）、§5.4（互動狀態契約）、§5.6（AI 標記）、§九風險 3（Gemini 成本／配額）
- **依賴**：Phase 25（條碼，選配）、Phase 27（成本欄位，accept 可帶 `cost`）
- **規模**：M–L（API 約 8 端點＋規則引擎＋配額；Web 新頁面與共用元件；e2e 新 spec）

---

## 目標

多張照片一次建立物品草稿：上傳即建 `pending` 草稿 → 前端逐張觸發辨識（伺服器端狀態機）→ 卡片式審核（可編輯）→ 逐張或批量建立物品。AI 建議融入本人歷史偏好（「名稱關鍵詞 → 分類／位置／標籤」規則），**LLM 不可用時規則仍生效**。

---

## 範圍

### 批次入庫流程
- 多圖上傳（多選檔案／行動連續拍照）→ 每張圖建立 `pending` 草稿（伺服器端持久化，刷新不丟）
- **處理模型**：伺服器端狀態機＋前端逐張觸發 `POST /api/ai/drafts/{id}/process`（伺服器單張呼叫既有 Gemini suggest）；**不引入背景 worker**
- **草稿審核 UI**（卡片式）：縮圖、AI 名稱／描述／分類／標籤建議、可編輯、接受／丟棄；四態卡（排隊／辨識中／失敗重試／完成）＋頂部批量條（全選／全部接受／全部丟棄）；狀態以伺服器為唯一來源，離開恢復＝重載後依狀態續行
- 審核完成 → 建立物品（可逐張編輯後接受）
- 失敗可重試；速率控制＝per-user 每日配額（Gemini 配額保守策略）

### 智慧分類建議
- 以本人歷史資料生成「名稱關鍵詞 → 分類／位置／標籤」局部規則（純函式＋本人資料查詢）
- AI 建議附 ✦ `AiMark`；歷史建議附文字徽章「依歷史：廚房」；**歷史優先**（分類／位置／標籤預設值取歷史，AI 建議為次）
- `process` 成功時以 AI 名稱為關鍵詞預先算好歷史建議；使用者手動改名時可呼叫 `POST /api/ai/suggest-classification` 隨時取回
- **隱私**：規則引擎僅使用本人（`owner_id = 自己`）未刪除物品

### DB／API
- `ai_draft_items`（`source: batch_photo | receipt`，為 Phase 33 預留）、`ai_usage`（每日配額計數）
- 端點：建立／清單／process／accept／discard／批量 discard／suggest-classification

### 明確不在本期範圍
- 收據辨識（Phase 33；本 phase 只保留 `source=receipt` 的欄位與共用元件彈性）
- NL 搜尋／問答（Phase 34）、AI 傳送 opt-in 開關（Phase 34，設定「個人＞偏好」）
- 背景 worker／佇列服務、SSE／串流、批次進度通知
- 前端編輯值持久化（編輯只存在瀏覽器；接受時一次送出——「伺服器端狀態為唯一來源」指**狀態**）
- prompt 變更：沿用既有 `_PROMPT`（未變更 → 本 phase 不新增 `apps/api/evals/` case；evals 於 Phase 34 建立）
- hint 參數 UI（既有 `suggest-from-image` 的 `hint` 維持 API-only）
- item-form 既有單張 AI 按鈕的 ✦ 標記（roadmap §5.6 標記清單未含；避免動到既有表單）

---

## 關鍵設計決策

### D1 處理模型與狀態機（伺服器端唯一來源）

- 狀態：`pending → processing → ready | failed`；終態 `accepted | discarded`
- `POST /api/ai/drafts/{id}/process`：
  - 允許進入：`pending | failed | ready | processing`（**非終態皆可**；`processing` 可重入＝卡住復原、重複點擊安全）
  - 終態（`accepted | discarded`）→ **409**（`detail` 說明目前狀態）
  - 流程：先將 `status=processing` 落地 commit（讓並行讀取看到辨識中）→ 執行管線 → 終態落地 commit → 回應更新後草稿
  - 回應一律 200（結果在 body 的 `status`／`error_code`）；配額耗盡、AI 未設定等「業務性失敗」不轉為 HTTP 錯誤，交由四態卡呈現
- **不引入背景 worker**；Gemini 呼叫同步進行（既有 `suggest-from-image` 同慣例）

### D2 草稿建立與冪等

- `POST /api/ai/drafts`：body `{image_ids: [uuid, ...]}`（1–10 張，順序保留）
  - 每張 image 必須為呼叫者可見（沿用 `images_service.get_visible`；不可見／不存在 → 404，不洩漏存在性）
  - 同一張 image 已有**活動草稿**（`pending | processing | ready`）→ 跳過不重建（回傳 `skipped_image_ids`），避免重送造成重複草稿（`failed` 不算活動：允許重新上傳）
  - 回應 201 `{created: [DraftRead], skipped_image_ids: [uuid]}`
- 圖片上傳走既有 `POST /api/images`（multipart、單檔）；前端逐檔上傳後以一次建立呼叫建草稿；上傳失敗的檔案留在前端清單可重試（孤兒圖片與既有 item-form 行為一致，列為已知行為）
- 無 DB 層唯一約束（單人使用情境；重複僅造成多餘草稿，可丟棄）

### D3 終態語義與「手動完成」

- `accepted`／`discarded` 為終態：`process`／`accept`／`discard` 於終態 → 409
- **`failed → accepted` 允許**：AI 不可用（未設 key／配額耗盡／上游失敗）時，使用者仍可手動填名稱並接受（草稿卡「失敗」態提供手動填寫區），此即「LLM 不可用時規則仍生效」的落地路徑；`pending`／`processing` → accept 409（尚未辨識完）
- `discard` 允許：`pending | processing | ready | failed`；終態 409

### D4 錯誤模型（代碼化，i18n 由前端對照）

- DB 欄位 `error_code`（nullable）：`ai_disabled`（未設 `GEMINI_API_KEY`）／`quota_exhausted`／`upstream_error`（連線、非 JSON、空回應）／`image_missing`（圖片列已刪或檔案不在磁碟）
- API 回 `error_code`；原始上游訊息只進 server log（不進 DB／不回傳）
- 前端 `ai.drafts.errors.*` 對照文案；重試按鈕對所有代碼一致可用（重試本身冪等）

### D5 草稿 payload 契約（全欄位必填，Phase 31 慣例）

```json
{
  "version": 1,
  "ai": {
    "name": "咖啡濾杯",
    "description": "陶瓷手沖濾杯，適合 1-2 杯",
    "category_suggestion": "廚房用品",
    "tag_suggestions": ["咖啡", "陶瓷"]
  },
  "history": {
    "category": {"id": 3, "name": "廚房用品", "item_count": 12, "score": 4},
    "location": {"id": 7, "name": "廚房", "item_count": 9, "score": 3},
    "tags": [{"name": "咖啡", "item_count": 6, "score": 3}]
  }
}
```

- `ai`：`AiSuggestResponse`（沿用既有 schema）或 `null`
- `history`：`category`／`location` 為 `BucketSuggestion`（`{id, name, item_count, score}`）或 `null`；`tags` 最多 3 筆
- `pending` 草稿 payload 為空結構（`ai: null`、`history` 空）；`failed` 草稿 `ai: null`、`history` 可能為空（AI 失敗時無名稱關鍵詞可用，改由 `suggest-classification` 補）
- 子模型不使用預設值（顯式必填）→ OpenAPI／api-types 契約穩定

### D6 智慧分類規則（純函式＋確定性排序）

- **分詞**（`classification_service.tokenize`）：NFKC 正規化＋lower；
  - 拉丁／數字連續片段長度 ≥ 2 → 一個 token（如 `hario`、`v60`）
  - CJK 連續片段：逐字 bigram（`陶瓷咖啡杯` → `陶瓷`、`瓷咖`、`咖啡`、`啡杯`）；整段長度 1 → 該單字元成 token
- **評分**：對本人未刪除物品逐一比對名稱 token 交集；`score = |交集|`；分類／位置以 `(score_sum, item_count)` 聚合，標籤以 `(score_sum, item_count)` 聚合
- **排序**：`score` desc → `item_count` desc → `id`／`name` asc（完全決定性，測試可鎖定）
- **輸出**：top1 分類、top1 位置、top3 標籤；`score ≥ 1` 才輸出；`category_id`／`location_id` 為 `null` 的物品**不**產生「未分類／未指定」建議
- 查詢護欄：`ORDER BY items.id LIMIT 2000`（超過仍為決定性；家用量級遠低於此）
- 只讀本人資料（不含群組可見他人物品）

### D7 配額（per-user 每日，Asia/Taipei）

- 表 `ai_usage(id, user_id, day, calls)`；`UNIQUE(user_id, day)`；`day` 為 **Asia/Taipei 當地日期**（UTC 16:00 換日）
- 設定 `AI_DAILY_QUOTA`（env，預設 50；`<= 0` 表示無限制）
- **計次於嘗試**（呼叫前先扣；上游失敗亦計）；`SELECT → INSERT/UPDATE` 泛用寫法（PG／SQLite 相容；單人競態風險可接受）
- 讀寫分工：`ai_service.suggest_from_image`（既有端點）與 `ai_drafts_service.process` 皆先扣配額；耗盡時
  - 既有端點 → **429**（`detail` 說明額度；行為變更，屬風險 3 的落地）
  - 草稿 process → 業務失敗（`status=failed`、`error_code=quota_exhausted`），歷史規則與手動完成不受影響
- per-user 隔離：他人耗盡不影響自己

### D8 accept 語義（伺服器端建立物品）

- `POST /api/ai/drafts/{id}/accept`：body＝編輯後欄位
  ```
  {name(必填 1–200), description?, category_id?, location_id?,
   tag_names?: [..], quantity?: int(預設 1), cost?: Decimal|null}
  ```
- 伺服器以 `items_service.create_item(ItemCreate(...))` 建立（沿用欄位驗證、`item.created` webhook、低庫存通知）；`image_id`＝草稿圖片（圖片已被刪則不帶）
- 成功：`status=accepted`、`item_id=<新物品>`、回應 `{draft: DraftRead, item: ItemRead}`（同一 transaction）
- 重複 accept → 409；`warehouse_id` 不開放（建立後於物品頁編輯，維持卡片精簡）
- 批量「全部接受」＝前端對選取的 `ready` 草稿**逐一**呼叫 accept（各自 payload、錯誤隔離；跳過非 `ready` 並提示）；僅「批量丟棄」有端點（無參數、可一次完成）
- `POST /api/ai/drafts/discard`：body `{ids: [uuid, ...]}`（1–50）→ `{discarded: int, skipped: [{id, reason}]}`（終態或不存在者入 `skipped`，不整批失敗）

### D9 入口與導覽（roadmap §5.2／§5.3）

- **不新增首層導覽項目**；佇列頁為物品域子路由 `/items/drafts`
- `/items/new` 頁首加入口卡：標題「AI 批次入庫」＋一行說明＋CTA「開啟草稿佇列」→ `/items/drafts`；活動草稿數 > 0 時顯示徽章「N 筆待審核」（`GET /api/ai/drafts?limit=1` 的 `counts`）；計數載入中顯示「…」、失敗時只顯示入口（不擋動線）
- `/items/drafts` 頁首提供「改為手動新增」→ `/items/new`（互相可達）
- viewer（唯讀）：`/items/new` 與 `/items/drafts` 皆顯示 `ViewerNotice`（沿用 `useReadOnly`）；入口卡隱藏

### D10 權限

- 新 router `app/routes/ai_drafts.py`（prefix `/api/ai/drafts`）掛 `WriterGuardRoute`：viewer 之建立／process／accept／discard → 403（路由依賴階段，不洩漏資源存在性）
- `POST /api/ai/suggest-classification` 置於既有 `app/routes/ai.py`（唯讀計算、不掛 guard）：viewer 呼叫無害；既有 `suggest-from-image` 維持不擋（Phase 30 既定，零回歸）
- 所有草稿讀寫僅限本人（他人／不存在一律 404）

### D11 Web 互動狀態契約（roadmap §5.4 必填表）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 入口卡（`/items/new`） | 計數顯示「…」 | 無活動草稿 → 僅顯示入口與一行引導 | 計數失敗 → 隱藏計數，入口仍可用（不擋動線） | 「N 筆待審核」徽章＋CTA | — |
| 上傳區（`/items/drafts`） | 逐檔上傳進度（檔名列＋狀態） | 未選檔 → 拖放／選檔引導＋「一次最多 10 張」 | 單檔上傳失敗 → 該檔列內錯誤＋「重試」；建立草稿失敗 → 區塊內錯誤＋重試（不清空已上傳清單） | 建立後清空選取、草稿入列並自動開始逐張處理 | 部分檔成功／失敗各自標示，成功者照常入列 |
| 草稿佇列 | 卡片 skeleton ×3 | 無活動草稿 → 引導自上方開始（下一步動作） | 清單載入失敗 → 區塊內錯誤＋重試（不整頁壞） | 卡片就緒＋頂部批量條 | 逐張處理進行中：卡片各自排隊／辨識中，互不阻擋 |
| 草稿卡（四態） | 辨識中 → 縮圖＋spinner＋「辨識中…」 | — | 失敗 → `error_code` 文案＋「重試辨識」＋可展開的手動填寫 | 完成 → AI 欄位（✦ 標記）＋「依歷史」徽章／chips＋編輯＋接受／丟棄 | 接受中／丟棄中 → 該卡按鈕 loading，其他卡不受影響 |
| 批量條 | 「全部接受」執行中：進度文字「3/5」 | 未選取 → 動作為 disabled | 逐筆失敗 → 個別 toast；成功者照常移除 | 「已接受 N 筆／已丟棄 N 筆」toast＋清單更新 | 選取含非 `ready` → 接受跳過並提示「已跳過 M 筆」 |

- 語意補充：頁面載入時**只自動續行 `pending`**（逐張序列），`processing` 不自動重送（提供卡片內「重新辨識」補救，允許伺服器端重入）；`failed` 一律手動重試
- 處理迴圈嚴格序列（同時 1 張）；傳輸層錯誤（例：斷網）→ 停止迴圈＋區塊提示「繼續處理」；業務失敗（200＋failed）不停止迴圈
- AI 標記（§5.6）：AI 產出欄位旁 `AiMark`（lucide `sparkles`＋tooltip「由 AI 產生，可編輯」）；歷史建議為文字徽章「依歷史：{名稱}」；禁用漸層／發光／魔法動畫

### D12 i18n 與型別

- 新鍵（zh-TW／en 同步、行數一致；`messages/*.json` 逐鍵插入不整檔重寫）：`ai.mark.tooltip`、`ai.drafts.*`（`title`／`subtitle`／`backToNew`／`upload.*`／`bulk.*`／`status.*`／`card.*`／`errors.*`／`empty.*`／`toast.*`）、`items.new.batchEntry.*`
- API 變更後重生成 `packages/api-types`（`export_openapi.py` ＋ `gen:types`），零 diff 為驗收項

---

## 資料模型（migration 0024）

```
ai_draft_items
  id            UUID  PK
  owner_id      UUID  FK users(id) ON DELETE CASCADE, indexed
  source        VARCHAR(20)  NOT NULL            -- batch_photo | receipt（CHECK）
  image_id      UUID  NULL FK images(id) ON DELETE SET NULL
  status        VARCHAR(20)  NOT NULL default 'pending'  -- CHECK: pending|processing|ready|failed|accepted|discarded
  payload       JSON  NOT NULL                   -- DraftPayload（version=1）
  error_code    VARCHAR(32) NULL                 -- ai_disabled|quota_exhausted|upstream_error|image_missing
  item_id       UUID  NULL FK items(id) ON DELETE SET NULL   -- 與 roadmap 差異：新增，供「已建立 → 檢視物品」與測試驗證
  processed_at  TIMESTAMPTZ NULL                 -- 最後一次 process 完成時間
  created_at    TIMESTAMPTZ NOT NULL default now
  INDEX (owner_id, status)

ai_usage
  id       UUID PK
  user_id  UUID FK users(id) ON DELETE CASCADE
  day      DATE NOT NULL                          -- Asia/Taipei 當地日期
  calls    INTEGER NOT NULL default 0
  UNIQUE (user_id, day)
```

- `payload` 用 `JSONType`（`app/models/favorite_audit_token.py`）與 `reports.payload` 一致；PG 上為 JSON
- 模型：`app/models/ai_draft.py`（`AiDraftItem`）、`app/models/ai_usage.py`（`AiUsage`）；`app/models/__init__.py` 註冊
- 索引／CHECK 命名沿用 `0023` 風格；`down` 需完整可回

---

## API payload 範例

### `POST /api/ai/drafts`

```json
// request
{"image_ids": ["8f2c…", "1a9b…"]}
// 201
{
  "created": [
    {
      "id": "d1c0…", "source": "batch_photo", "status": "pending",
      "image_id": "8f2c…", "item_id": null, "error_code": null,
      "payload": {"version": 1, "ai": null,
                  "history": {"category": null, "location": null, "tags": []}},
      "processed_at": null, "created_at": "2026-10-19T02:11:03Z"
    }
  ],
  "skipped_image_ids": ["1a9b…"]
}
```

### `GET /api/ai/drafts`

```
?status=ready&limit=20&offset=0        # 省略 status → 活動四態（pending|processing|ready|failed）
```
```json
{
  "items": [
    {"id": "d1c0…", "source": "batch_photo", "status": "ready", "image_id": "8f2c…",
     "item_id": null, "error_code": null,
     "payload": {"version": 1,
        "ai": {"name": "咖啡濾杯", "description": "陶瓷手沖濾杯", "category_suggestion": "廚房用品", "tag_suggestions": ["咖啡"]},
        "history": {"category": {"id": 3, "name": "廚房用品", "item_count": 12, "score": 4},
                    "location": {"id": 7, "name": "廚房", "item_count": 9, "score": 3},
                    "tags": [{"name": "咖啡", "item_count": 6, "score": 3}]}},
     "processed_at": "2026-10-19T02:11:09Z", "created_at": "2026-10-19T02:11:03Z"}
  ],
  "total": 1,
  "counts": {"pending": 0, "processing": 0, "ready": 1, "failed": 0, "accepted": 4, "discarded": 1}
}
```

### `POST /api/ai/drafts/{id}/process`

```
200 → DraftRead（status=ready 或 failed＋error_code）
409 → {"detail": "draft already accepted"}（終態）
404 → 不存在或非本人
```

### `POST /api/ai/drafts/{id}/accept`

```json
// request（編輯後欄位；name 必填）
{"name": "咖啡濾杯", "description": "陶瓷手沖濾杯", "category_id": 3, "location_id": 7,
 "tag_names": ["咖啡", "陶瓷"], "quantity": 1, "cost": "450.00"}
// 200
{"draft": {"…": "…", "status": "accepted", "item_id": "77aa…"},
 "item": {"id": "77aa…", "name": "咖啡濾杯", "image_id": "8f2c…", "…": "…"}}
```

### `POST /api/ai/drafts/{id}/discard` → `200 DraftRead`（`status=discarded`）

### `POST /api/ai/drafts/discard`

```json
{"ids": ["d1c0…", "e2d1…"]}
// 200
{"discarded": 1, "skipped": [{"id": "e2d1…", "reason": "already discarded"}]}
```

### `POST /api/ai/suggest-classification`

```json
// request
{"name": "陶瓷咖啡濾杯"}
// 200
{"category": {"id": 3, "name": "廚房用品", "item_count": 12, "score": 4},
 "location": {"id": 7, "name": "廚房", "item_count": 9, "score": 3},
 "tags": [{"name": "咖啡", "item_count": 6, "score": 3}]}
```

---

## 任務（TDD：每項先 RED 再 GREEN）

> 指令：API `cd apps/api && uv run pytest -q`；Web `cd apps/web && pnpm vitest run`／`pnpm typecheck`。每 task 完成即 commit（Conventional Commits，繁中 body）。

### T1.1 DB：`AiDraftItem`／`AiUsage` 模型＋migration 0024

- RED：`tests/test_ai_drafts.py::test_draft_row_defaults`（直接以 session 建列：`status=pending`、`payload` 為 JSON、`error_code=None`）；`test_ai_usage_unique_day`（同 `(user_id, day)` 唯一）
- GREEN：模型＋`alembic/versions/0024_ai_drafts.py`（up：兩表＋索引／CHECK；down：drop）；`app/models/__init__.py` 匯出
- 驗證：Postgres 容器 `upgrade 0023 → 0024 → downgrade → upgrade`

### T1.2 規則引擎 `classification_service`（純函式）

- RED：`tests/test_classification_rules.py`
  - `tokenize`：NFKC／lower；拉丁＋數字 ≥ 2 字；CJK bigram；CJK 單字元；混合字串；空字串／純符號 → `set()`
  - `suggest`：共享 token 計分、`score → item_count → id` 排序；top3 標籤；無交集 → `None`／`[]`；`category_id`／`location_id` 為 null 不入選；軟刪除排除；**僅本人**（他人同名物品不影響）；決定性（同資料兩次呼叫同結果）；`LIMIT 2000` 護欄（造 2001 筆仍決定性）
- GREEN：`app/services/classification_service.py`（`tokenize`／`suggest_for_name(session, owner_id, name)`）

### T1.3 配額 `ai_quota`

- RED：`tests/test_ai_quota.py`：同日累加；跨日重置（以 UTC 16:00 為 Asia/Taipei 換日邊界）；per-user 隔離；`AI_DAILY_QUOTA=1` 第二次 → `False`；`<= 0` → 無限制；`tests/test_ai.py` 追加：既有端點超額 → 429 且 **Gemini 未被呼叫**（mock 斷言）；扣次於嘗試（上游例外仍計）
- GREEN：`app/services/ai_quota.py`（`consume(session, user_id) -> bool`）＋`app/config.py` `ai_daily_quota: int = 50`；`ai_service.suggest_from_image` 接線

### T1.4 草稿建立／清單 API

- RED：`tests/test_ai_drafts_api.py`
  - 建立：1–10 張（0 張／11 張 → 422）；他人圖片／不存在 → 404；重複活動草稿 → `skipped_image_ids`（`failed` 後可重建）；`source=batch_photo`、`status=pending`
  - 清單：預設只回活動四態；`status=` 過濾；`counts` 六態齊全且必填；分頁 `limit/offset/total`；**只回本人**（他人草稿不出現）；`created_at DESC`
  - viewer → 建立 403
- GREEN：`app/schemas/ai_draft.py`（`DraftCreate`／`DraftRead`／`DraftPayload`／`BucketSuggestion`／`TagSuggestion`／`DraftListResponse`）、`app/services/ai_drafts_service.py`（`create_drafts`／`list_drafts`／`counts`／`get_owned`）、`app/routes/ai_drafts.py`（掛 `WriterGuardRoute`）＋`main.py` 註冊

### T1.5 process 狀態機（含錯誤碼與失敗路徑）

- RED：`tests/test_ai_drafts_process.py`（沿用 `test_ai.py` 的 mock `google.genai.Client` 手法）
  - 成功：`pending → processing → ready`；`payload.ai` 填入 mock 結果；`payload.history` 以 AI 名稱計算（先造歷史物品）；`processed_at` 有值
  - AI 未設定（無 key）→ `failed`＋`ai_disabled`（不呼叫 Gemini）
  - 配額耗盡 → `failed`＋`quota_exhausted`（不呼叫 Gemini）
  - 上游例外／非 JSON → `failed`＋`upstream_error`（原始訊息不入 DB）
  - 圖片列已刪（`image_id=NULL`）→ `failed`＋`image_missing`
  - 重入：`failed → ready`（重試）；`ready → ready`（可重跑）；`processing` 可進入；`accepted`／`discarded` → 409；他人草稿 → 404
- GREEN：`ai_drafts_service.process_draft`（兩段 commit）＋路由

### T1.6 accept／discard／批量 discard

- RED：`tests/test_ai_drafts_accept.py`
  - accept：建立物品欄位正確（名稱／描述／分類／位置／標籤／數量／成本）；`image_id` 綁定；`status=accepted`＋`item_id`；回應含 `item`
  - `failed → accept`（手動完成）成功；`pending`／`processing` → 409；重複 accept → 409；他人 → 404
  - 名稱空白 → 422；分類／位置不存在 → 與 items 端點一致之錯誤
  - discard：四態可丟棄、終態 409、他人 404；批量：混合輸入 → `discarded`＋`skipped[{id, reason}]`、上限 50、終態入 skipped
  - webhook `item.created` 觸發（沿用既有服務即得，測試補一筆斷言）
- GREEN：`accept_draft`／`discard_draft`／`discard_many`＋路由

### T1.7 `suggest-classification` 端點

- RED：`tests/test_ai_drafts_api.py`（或 `test_suggest_classification.py`）：回傳 top1 分類／位置／top3 標籤；空歷史 → 全 null／`[]`；空白名稱 422；他人資料不入選；viewer 可呼叫（非 guard 域）
- GREEN：`app/routes/ai.py` 新端點＋`app/schemas/ai.py`（`ClassificationSuggestion` 系）

### T1.8 api-types 重生成

- `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`；`pnpm --filter @ims/api-types gen:types`；`git status packages/api-types` 需為乾淨（零 diff 後即為 web 端 consumer 的型別來源）

### T2.1 Web API client＋hooks

- RED：`lib/api/ai-drafts.test.ts`（或既有 client 測試檔慣例）＋`lib/hooks/use-ai-drafts.test.tsx`：路徑／參數正確；`useDrafts`／`useDraftCounts`／mutations（process／accept／discard／bulk discard）＋invalidate 行為
- GREEN：`lib/api/ai-drafts.ts`（型別自 `@ims/api-types` `paths`）、`lib/hooks/use-ai-drafts.ts`（`useQuery`／`useMutation`，慣例同 `use-reports`）

### T2.2 `AiMark` 共用元件（roadmap §5.6）

- RED：`components/ai/ai-mark.test.tsx`：渲染 `sparkles` 圖示＋tooltip「由 AI 產生，可編輯」（zh-TW／en）；`aria-label` 可及；不改變容器樣式
- GREEN：`components/ai/ai-mark.tsx`（`muted-foreground`、小型圖示；點擊／hover 皆可說明——tap 可及）

### T2.3 草稿卡元件（四態＋編輯＋建議排序）

- RED：`components/ai/draft-card.test.tsx`
  - 四態渲染：pending（排隊）／processing（spinner＋重新辨識）／failed（錯誤碼文案＋重試＋可展開手動填寫）／ready（AI 欄位＋`AiMark`＋歷史徽章）
  - 建議預設：分類／位置／標籤預設取歷史；歷史缺 → AI 精確同名分類匹配；AI 無 → 空
  - 「依歷史建議」按鈕 → 呼叫 `suggest-classification` 並套用 chips（含 loading／無結果文案）
  - 接受 → 以編輯後值呼叫 accept；丟棄 → discard；按鈕 loading 狀態
  - 名稱空白 → 接受 disabled
- GREEN：`components/ai/draft-card.tsx`（使用既有 `Input`／`Textarea`／`Select`／`LocationSelect`／`TagMultiSelect`）；新 `components/categories/category-select.tsx`（抽出 `flattenCategories`＋分類 Select，`item-form.tsx` 改用之，零回歸——`item-form.test.tsx` 與 e2e `items-crud.spec.ts` 為回歸護欄）

### T2.4 佇列頁 `/items/drafts`（上傳區＋逐張處理＋批量條）

- RED：`app/(app)/items/drafts/page.test.tsx`
  - 上傳：多檔選取 → 逐檔上傳 → 建草稿；>10 擋下並提示；單檔失敗列內重試；建立失敗區塊錯誤＋重試
  - 處理迴圈：序列（同時 1 張）、`pending` 自動續行、`processing` 不自動重送、業務失敗不中斷、傳輸錯誤停止並提供「繼續處理」
  - 批量條：全選／取消；「全部接受」只對 `ready`（跳過提示）；「全部丟棄」呼叫 bulk discard；未選取 disabled
  - 四態與狀態契約（skeleton／空狀態引導／清單錯誤重試）
  - `readOnly` → `ViewerNotice`
- GREEN：`app/(app)/items/drafts/page.tsx`（server shell）＋`drafts-client.tsx`（client）＋`components/ai/draft-upload-zone.tsx`、`components/ai/draft-bulk-bar.tsx`

### T2.5 `/items/new` 入口卡＋計數徽章

- RED：`app/(app)/items/new/page.test.tsx` 追加：入口卡可見、CTA 連結 `/items/drafts`、`counts` 合計 > 0 顯示「N 筆待審核」、計數錯誤仍可用、viewer 不顯示
- GREEN：`components/ai/batch-entry-card.tsx` 併入 `/items/new`（`useReadOnly` 判斷）

### T2.6 i18n 補齊與對帳

- RED（對帳）：`tests/i18n.test.ts`（若無既有者，新增最小檢查：`zh-TW.json` 與 `en.json` 鍵集一致、`ai.*`／`items.new.batchEntry.*` 齊全）
- GREEN：`messages/zh-TW.json`、`messages/en.json` 逐鍵插入（行數一致）

### T3.1 E2E `tests/ai-drafts.spec.ts`

- 情境 1（無 key 路徑，＝本機與 CI 預設）：註冊登入 → 以 API 建 1 筆具分類「廚房用品」的物品（建立歷史）→ `/items/new` 入口卡 → `/items/drafts` 上傳 2 張 1×1 PNG（`setInputFiles`，比照 `backup.spec.ts`）→ 兩張卡自動處理 → 皆 `failed`（`ai_disabled` 文案）→ 第 1 張展開手動填寫：名稱「咖啡濾杯」→「依歷史建議」→ 分類 chip 套用「廚房用品」→ 接受 → toast＋清單少 1 張 → `/items` 可見新物品 → 草稿 `accepted`（不再出現在佇列）
- 情境 2：批量丟棄：上傳 1 張 → failed → 勾選 → 全部丟棄 → 佇列空狀態引導
- 情境 3：`/items/new` 入口卡徽章（在有活動草稿時顯示「N 筆待審核」）
- 注意：`toContainText`（Playwright matcher）；`getByRole(name)` 為子字串比對；每次註冊新使用者隔離資料

### T3.2 文件收尾

- `docs/ai.md`（新）：`GEMINI_API_KEY`／`AI_DAILY_QUOTA` 設定、草稿生命週期與狀態機、端點清單與語義、規則引擎說明（分詞／評分／排序／隱私）、疑難排解（未設 key、配額、上游錯誤、e2e 無 key 路徑）
- `CHANGELOG.md`：`alpha.32`（DB／API／Web／i18n／測試數／migration 0024）
- `docs/v2-roadmap.md`：Phase 32 ✅＋測試規模更新；`docs/scheduling.md` 不動（無新 job，於 `docs/ai.md` 交叉註明）
- 本計畫 Final Verification 實測記錄＋收尾環境註記

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → ___ passed
- [ ] Web：`pnpm vitest run` → ___ passed（___ 檔）；`pnpm typecheck` → 0 error
- [ ] api-types 重生成零 diff
- [ ] Migration 0024 up／down／up（Postgres 容器）
- [ ] e2e：重建 image 後 `pnpm exec playwright test` → ___ spec／___ passed
- [ ] 視覺走查：桌機 1440×900＋行動 390×844（`/items/new` 入口卡；`/items/drafts` 上傳區、四態卡（含失敗重試與手動填寫）、批量條、空狀態）——人工檢視無破版
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

### 收尾環境註記（2026-10-19 起填）

- （待填：worktree 名稱、stack 狀態、e2e 前置與資料種子、無 key 路徑說明）

## 測試基線（main，Phase 31 完成）

- API：912 passed
- Web：560 passed（111 檔）＋typecheck
- E2E：22 spec／68 情境
