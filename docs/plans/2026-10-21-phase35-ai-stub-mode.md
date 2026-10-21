# Phase 35 — AI stub 模式（可測的 AI 成功路徑）

- **日期**：2026-10-21
- **狀態**：計畫中（TDD 任務與驗證見下文；Final Verification 收尾時填實測）
- **依據**：`docs/progress-2026-10-19.md` §六 後續候選 #1（「AI stub 模式（技術債）：`AI_MODE=stub` 環境開關，讓 e2e 能驗證 AI 成功路徑（收據品項／搜尋 chip／問答引用），補上最大測試缺口」）＋ `docs/v2-roadmap.md` 下一輪候選 #1
- **依賴**：Phase 32（草稿狀態機）、Phase 33（收據抽取）、Phase 34（NL 搜尋／問答）
- **規模**：S–M（API：設定開關＋stub 供應器＋規則轉譯器＋1 個唯讀端點；Web：**無**功能變更；e2e：1 個新 spec＋Playwright 專案分流）

---

## 目標

把 Phase 32–34 三個 AI 功能「成功路徑無法 e2e 覆蓋」的最大測試缺口補上。

做法：新增 `AI_MODE=stub` 環境開關。啟用後，**所有 LLM 呼叫改由確定性的 stub 供應器回應**（不連外網、不需 `GEMINI_API_KEY`、不消耗配額），但**下游的解析、白名單驗證、名稱解析、對帳、引用映射、錯誤碼路徑完全不變**。因此 e2e 可以在沒有真實 key 的情況下驗證：

- 收據辨識成功 → 品項草稿 `ready` → 對帳相符 → 接受入庫
- 自然語言搜尋成功 → 「理解為」chip（位置／到期／關鍵字）＋結果
- 物品問答成功 → 回答＋引用連結（`/items/{id}`）
- 批次照片辨識成功 → 草稿 `ready` → 接受入庫

---

## 範圍

### API

- `Settings.ai_mode: Literal["live", "stub"]`（env `AI_MODE`，預設 `live`）
- `app/services/ai_stub.py`：stub 供應器（決定性回應）
- `app/services/ai_mode.py`：統一啟用判定 `ai_enabled()`
- `GET /api/ai/status`：回報目前模式（`live`／`stub`）與是否啟用

### Web

- **無功能變更**（成功路徑 UI 於 Phase 32–34 已完成，本期只是第一次被 e2e 實際走過）

### e2e

- 新增 `apps/web/tests/ai-stub.spec.ts`（收據成功、搜尋 chip、問答引用、批次入庫四情境）
- Playwright 專案分流：`chromium`（預設，live）與 `ai-stub`（stub 專用）

### 明確不在本期範圍

- 不改任何既有端點的請求／回應契約（`GET /api/ai/status` 為**純新增**）
- 不做 stub 資料的隨機化／模糊化（stub 必須**完全決定性**，才能寫死 e2e 斷言）
- 不改 stub 模式的資料隔離規則（仍只讀本人可見資料）
- 不移除 `GEMINI_API_KEY` 的 live 行為（`AI_MODE=live` 且無 key → 現行 fallback／503 行為**完全不變**）

---

## 關鍵設計決策

### D1 單一環境開關 `AI_MODE`，啟動時 fail fast

- `AI_MODE` ∈ {`live`（預設）, `stub`}；其他值 → pydantic `ValidationError`（啟動即失敗，不靜默降級）
- 與既有 `JWT_SECRET` 守則一致：**非 `dev` 環境不得啟用 stub**（`environment != "dev"` 且 `ai_mode == "stub"` → 啟動失敗），避免正式環境誤開而對使用者回假資料
- `AI_MODE=stub` 時啟動 log 一則 warning（一眼可辨識部署狀態）

### D2 攔截點在 LLM 唯一出口（`ai_service`），下游一律不動

`ai_service` 的四個 `call_gemini_*` 是全系統**唯一**呼叫 Gemini 的位置（已確認 `grep google.genai` 僅此四處）。stub 只在這四個函式開頭分支：

| 函式 | live | stub |
|------|------|------|
| `call_gemini_suggest` | Gemini → 解析 | stub JSON → **同一個**解析函式 |
| `call_gemini_receipt` | Gemini → `parse_receipt_response` | stub JSON → **同一個** `parse_receipt_response` |
| `call_gemini_search_filters` | Gemini → `parse_search_filters_response` | stub JSON → **同一個** `parse_search_filters_response` |
| `call_gemini_ask` | Gemini → `parse_ask_response` | stub JSON → **同一個** `parse_ask_response` |

→ **stub 必須回傳「原始 JSON 文字」**（不是已解析的物件），才能保證解析層、白名單層、引用映射層都被真實執行。

### D3 stub 回應形狀＝真實 LLM 的形狀

stub 產出的 JSON **與真實 LLM 回應同構**（欄位名、型別、型態皆相同），因此下游驗證不會被繞過：

- 收據：`merchant`／`purchased_at`／`currency`／`total`／`items[]`（`name`／`quantity`／`unit_price`／`subtotal`）
- 搜尋：**名稱**（非 id）→ 既有 `filters_from_llm` 名稱解析路徑生效（`category`／`location`／`tags`）
- 問答：`{"answer": string, "grounded": bool}`，答案含 `[#n]` → 既有引用映射路徑生效
- 建議：`{"name", "description", "category_suggestion", "tag_suggestions"}`

### D4 搜尋 stub：確定性規則轉譯器（非固定 JSON）

真實 LLM 會依句子輸出條件；stub 必須能對「不同句子」給出「有意義且可重現」的條件，否則 e2e 只能驗一條句子。規則（順序固定、無隨機）：

1. **目錄比對**：查詢字串包含本人目錄中的分類／位置／標籤名稱（或位置完整路徑）→ 輸出該名稱（取**最長匹配**；歧義交由既有 `_resolve` 處理 → `unresolved`）
2. **關鍵詞規則**：`快過期/即將過期/7天內` → `expiry=expiring_soon`；`已過期` → `expired`；`逾期` → `loan=overdue`；`借出/借著` → `borrowed`；`最愛/收藏` → `favorite=true`；`至少 N` → `min_quantity`；`最多 N` → `max_quantity`；`最快到期` → `sort=expiry_asc`；`最新` → `created_desc`；`名稱` → `name_asc`
3. **殘留關鍵字**：扣除已命中的名稱與關鍵詞、去除虛詞（的/裡/中/有/找/幫我/請…）後的殘字 → `q`（上限 100 字；空則省略）
4. **只輸出白名單欄位**（與 D3 同構）

→ 範例：`"廚房裡快過期的感冒藥"`（目錄有位置「廚房」）→ `{location:"廚房", expiry:"expiring_soon", q:"感冒藥"}`

### D5 問答 stub：以上下文為唯一依據，產生可映射的引用

stub 只看 `context`（既有服務已保證是本人可見物品摘要），輸出「依系統資料，共找到 N 筆相關物品：名稱1 [#1]、名稱2 [#2]…」。→ 既有 `_citations_from_answer` 映射成 `citations`（`item_id`／`name`／`path`），e2e 可直接斷言引用連結。答案長度仍受 1000 字上限約束。

### D6 stub 模式不需要 key、也不消耗配額

- `ai_enabled()` 統一判定：`ai_mode == "stub" or bool(gemini_api_key)`；取代目前**五處** `if not settings.gemini_api_key`（`suggest_from_image`／`search`／`ask`／`create_receipt_drafts`／`process_draft`）
- `ai_quota.consume` 在 stub 模式直接回 True（不寫 `ai_usage`）：stub 沒有上游成本，不該消耗真實額度（否則 e2e 連跑會被 50 次／日限制攔截）
- 配額耗盡路徑不受影響：`AI_MODE=live` 行為完全照舊

### D7 opt-in 與配額語意不變

- `ai_data_sharing_enabled` 仍為 `search`／`ask` 的前置條件（stub 模式**不豁免**）：資料分享同意是產品語意，不是上游可用性語意；e2e 需顯式開啟（順帶保留 opt-in 的 e2e 覆蓋）
- 收據／草稿辨識不需 opt-in（沿用現況）

### D8 e2e 分流：Playwright 兩個 project + 模式偵測

- `playwright.config.ts` 增兩個 project：
  - `chromium`（預設）：`testIgnore: ai-stub.spec.ts` → 驗 live／無 key 的 fallback 路徑（既有 25 spec 不變）
  - `ai-stub`：`testMatch: ai-stub.spec.ts` → 驗 AI 成功路徑
- `ai-stub.spec.ts` 開頭以 `GET /api/ai/status` 偵測模式；若不是 `stub` → `test.skip()`（避免誤在 live stack 上假失敗）
- 執行方式：
  ```bash
  # live（AI 未設定 → fallback 路徑）
  pnpm exec playwright test --project=chromium --workers=2
  # stub（AI 成功路徑）
  AI_MODE=stub docker compose up -d api && pnpm exec playwright test --project=ai-stub --workers=2
  ```
- compose `api` 服務加 `AI_MODE: ${AI_MODE:-live}` → 可用 shell 環境變數覆寫，只重建 api 容器（不動 web／nginx／資料庫）

### D9 `GET /api/ai/status`（純新增唯讀端點）

- 回 `{mode: "live"|"stub", enabled: bool}`；需登入（避免公開部署設定）
- 用途：e2e 模式偵測（D8）、部署者自我檢查（`curl` 一行即知是否誤開 stub）
- 需重生成 api-types（純新增端點）

### D10 收尾環境與非 dev 環境

- `AI_MODE=stub` 僅允許 `environment == "dev"`（D1）→ compose 本機（`ENVIRONMENT=dev`）可用；正式部署設 `ENVIRONMENT=prod` 即拒絕啟動
- `.env.example` 補 `AI_MODE=live` 與說明

---

## API payload 範例

### `GET /api/ai/status`

```json
200
{ "mode": "stub", "enabled": true }
```

```json
200
{ "mode": "live", "enabled": false }
```

### stub 內部產物（非對外契約，供設計參考）

```json
// 搜尋（query="廚房裡快過期的感冒藥"，目錄有位置「廚房」）
{ "location": "廚房", "expiry": "expiring_soon", "q": "感冒藥" }

// 收據
{ "merchant": "測試商店", "purchased_at": "2026-01-01", "currency": "TWD", "total": "150.00",
  "items": [ {"name": "測試品項甲", "quantity": 2, "unit_price": "50.00", "subtotal": "100.00"},
             {"name": "測試品項乙", "quantity": 1, "unit_price": "50.00", "subtotal": "50.00"} ] }

// 問答（context 有 2 筆）
{ "answer": "依系統資料，共找到 2 筆相關物品：感冒藥 [#1]、鮮乳 [#2]。", "grounded": true }
```

---

## 資料模型

**無 migration**：不新增資料表／欄位。偏好沿用既有 JSON 欄位（`ai_data_sharing_enabled`）。

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 設定與啟用判定

- RED：`tests/test_ai_mode.py`
  - `AI_MODE` 預設 `live`；`stub` 可解析；非法值 → `ValidationError`
  - `environment != "dev"` 且 `ai_mode == "stub"` → `ValidationError`
  - `ai_enabled()`：`live`＋無 key → False；`live`＋有 key → True；`stub` → True
- GREEN：`app/config.py`（`ai_mode` 欄位＋validator）＋ `app/services/ai_mode.py`

### T1.2 stub 供應器與規則轉譯器

- RED：`tests/test_ai_stub.py`
  - 搜尋轉譯：目錄名稱比對（最長匹配）、關鍵詞規則、殘留關鍵字、虛詞去除、長度上限、只輸出白名單欄位
  - 收據 JSON 合法（可被 `parse_receipt_response` 解析；`total` == 品項小計合計）
  - 問答 JSON 含 `[#n]`、長度 ≤ 1000
  - 建議 JSON 合法
  - **決定性**：同輸入兩次輸出完全相同
- GREEN：`app/services/ai_stub.py`

### T1.3 `ai_service` 攔截（LLM 唯一出口）

- RED：`tests/test_ai_stub_api.py`
  - `AI_MODE=stub`（無 key）：`POST /api/ai/suggest-from-image` → 200 ＋ stub 建議
  - `AI_MODE=stub`：`POST /api/ai/receipts` → 201、2 列 `ready` 草稿、快照 total == item_total
  - `AI_MODE=stub`：`POST /api/ai/search`（需 opt-in）→ 200、`fallback_reason=null`、`applied` 含位置／到期
  - `AI_MODE=stub`：`POST /api/ai/ask`（需 opt-in）→ 200、`grounded=true`、`citations` 映射到本人物品
  - `AI_MODE=live`（無 key）：既有行為**完全不變**（503／fallback `ai_disabled`）
  - stub 回應仍走白名單／引用邊界（越界 `[#9]` 不產生引用）
- GREEN：`app/services/ai_service.py`（抽出 `parse_suggest_text`；四個 `call_gemini_*` 加 stub 分支）＋ `ai_search_service`／`ai_drafts_service` 改用 `ai_enabled()`

### T1.4 配額在 stub 模式不消耗

- RED：`tests/test_ai_stub_quota.py`（stub 模式下連續呼叫 N 次仍不 429，且 `ai_usage` 無新增列）
- GREEN：`app/services/ai_quota.py`

### T1.5 `GET /api/ai/status`＋api-types

- RED：`tests/test_ai_status.py`（需登入／viewer 可用／回 `mode` 與 `enabled`）
- GREEN：`app/routes/ai.py`＋`app/schemas/ai.py`
- 重生成：`uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`＋`node generate.mjs`（**零破壞性變更**）

### T2.1 e2e `tests/ai-stub.spec.ts`

- 情境 1（收據成功）：上傳 1 頁 → 草稿卡 `辨識完成` → 群組標頭顯示「測試商店」與 2 品項、對帳相符 → 展開 → 名稱預填「測試品項甲」、成本預填 `50.00` → 接受 → `/items` 見新物品
- 情境 2（搜尋 chip）：種子（位置「廚房」＋物品「感冒藥」＋3 天內到期批次＋開啟 opt-in）→ AI 搜尋「廚房裡快過期的感冒藥」→ chip 含「位置：」「到期：7 天內」「關鍵字：感冒藥」→ 結果含「感冒藥」→ **無** fallback 提示
- 情境 3（問答引用）：承情境 2 → 問答面板 → 提問 → 顯示回答＋引用連結（`href="/items/{id}"`）
- 情境 4（批次入庫）：上傳照片 → 草稿 `辨識完成`（AI 名稱）→ 接受 → `/items` 見新物品

### T2.2 Playwright 專案分流＋compose 覆寫

- `playwright.config.ts`：`chromium`（`testIgnore` stub spec）＋ `ai-stub`（`testMatch` stub spec）
- `docker-compose.yml`：`api.environment` 加 `AI_MODE: ${AI_MODE:-live}`
- `.env.example`：補 `AI_MODE=live`＋說明

### T3.1 文件收尾

- `docs/ai.md`：新增「AI stub 模式」章節（開關、行為差異、stub 回應範例、e2e 執行方式、非 dev 環境限制）
- `CHANGELOG.md`：`alpha.35`
- `docs/v2-roadmap.md`：Phase 35 ✅＋測試規模更新
- `docs/progress-2026-10-19.md`（或新進度檔）：更新驗證基線與已知限制（AI 成功路徑已可 e2e）
- 本計畫 Final Verification 填實測＋收尾環境註記

---

## 狀態契約

| 介面 | 影響 |
|------|------|
| 既有 AI 端點 | **零變更**（live 行為不動；stub 僅換掉 LLM 回應來源） |
| `GET /api/ai/status` | 新增（唯讀、需登入） |
| Web | **零變更** |
| e2e | 新增 `ai-stub` project＋4 情境；既有 25 spec 不變 |

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| 正式環境誤開 stub（回假資料給使用者） | D1：非 `dev` 環境啟動即失敗；啟動 warning；`GET /api/ai/status` 可自我檢查 |
| stub 繞過驗證層（測了假的成功路徑） | D2／D3：stub 回**原始 JSON**，一律走真實解析／白名單／引用映射 |
| stub 資料不具代表性（e2e 只驗到特例） | D4：規則轉譯器＋多句 e2e 斷言；stub 僅供測試，live 行為完全不動 |
| e2e 兩種模式互相干擾 | D8：Playwright project 分流＋`/api/ai/status` 模式偵測與 skip |
| stub 消耗真實配額導致 e2e 連跑失敗 | D6：stub 不寫 `ai_usage` |
| e2e 依賴固定資料庫殘留 | 每情境自建使用者（既有慣例），資料隔離 |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → 實測
- [ ] Web：`pnpm vitest run` → 實測；`pnpm typecheck` → 0 error
- [ ] api-types 重生成 → 零破壞性差異
- [ ] e2e（live）：`pnpm exec playwright test --project=chromium --workers=2` → 實測
- [ ] e2e（stub）：`AI_MODE=stub docker compose up -d api && pnpm exec playwright test --project=ai-stub --workers=2` → 實測
- [ ] 視覺走查（1440×900＋390×844）：stub 模式下的收據群組標頭、搜尋 chip、問答引用
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

---

## 測試基線（main，Phase 34 完成）

- API：1086 passed
- Web：717 passed（129 檔）
- E2E：25 spec／79 情境
