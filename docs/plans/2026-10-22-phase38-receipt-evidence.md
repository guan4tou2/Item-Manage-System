# Phase 38 — 收據證據鏈（算術驗證＋缺價待補＋幣別待確認＋不確定欄位）

- **日期**：2026-10-22
- **狀態**：已完成（T1.1–T3.2 全部落地；TDD 紅綠、全套驗證與視覺走查見文末 Final Verification）
- **依據**：`docs/progress-2026-10-22.md` §六 後續候選 #1（「收據證據鏈（借鑑 itemly）：收據三態（平衡／差額／缺價待補）＋行項算術檢查（折扣／稅／押金／運費）＋抽取不確定性標記＋『未平衡收據只能存草稿』；強化 Phase 33 的對帳語意」）
- **移植來源**：[itemly](https://github.com/Kamitoad/itemly)（MIT；`shared/receipt.ts`、`shared/receipt-validation.ts`、`shared/currency.ts`）——本 phase 移植其**驗證語意**，程式碼改寫為 Python／TypeScript 原生
- **規模**：M（API：抽取欄位擴充＋算術驗證＋快照擴充；Web：群組標頭升級；e2e：收據對帳情境；**有 API 契約變更** → api-types 重生成）

---

## 目標

Phase 33 的收據對帳目前只比「品項小計合計 vs 收據總額」，**看不到折扣、稅、運費**，也無法區分「真的差額」與「AI 沒讀到價格」。本 phase 借 itemly 的驗證語意，把收據證據鏈補成四態可判讀：

| 狀態 | 意義 | 對應 itemly |
|------|------|-------------|
| `balanced` | 算術驗證通過（品項合計 − 折扣 + 稅 + 運費 == 收據總額） | `balanced` |
| `discrepancy` | 有差額（並拆解差額來源） | `discrepancy` |
| `incomplete` | 缺價品項／缺總額／幣別未知 → **無法判斷** | `incomplete` |
| `unknown` | 舊資料（無新欄位）→ 不顯示對帳判讀 | （向後相容） |

並新增三個「AI 誠實標示」旗標：**待補價品項數**、**幣別待確認**、**不確定欄位**。

---

## 範圍

### API

- 抽取回應擴充：`subtotal`（價稅前小計）、`discount`（收據層級折扣）、`tax`（稅額）、`shipping`（運費）、`items[].discount`、`items[].tax`、`uncertain_fields[]`
- `ReceiptSnapshot` 擴充：`subtotal`／`discount`／`tax`／`shipping`／`calculated_total`／`balance_status`／`missing_price_count`／`uncertain_fields`／`currency`（未知為 `XXX`）
- 服務端算術驗證與快照組裝

### Web

- 收據群組標頭升級：四態判讀＋**差額拆解**（品項合計 − 折扣 + 稅 + 運費 = 應付；對照收據總額）
- 待補價品項數、幣別待確認、不確定欄位數

### 明確不在本期範圍

- **不做**「未平衡收據不得確認」的強制阻擋：我們是**逐品項接受**（無整張收據的確認流程），且 Phase 33 已明確決策「差額不阻擋接受」→ 維持不阻擋，但於文件記錄此取捨
- 不做 provenance 逐欄位來源追蹤（itemly 的 `fieldSources`）——成本高、當前無 UI 消費；僅移植「不確定欄位清單」
- 不做 itemly 的押金（deposit）、發票號碼、付款方式、附件雜湊等欄位
- 不做收據垃圾桶／復原（itemly 的 trash）：我們的草稿狀態機已有 `discarded` 終態
- 不做使用者手動編輯收據草稿（我們是品項草稿卡，非整張收據編輯）

---

## 關鍵設計決策

### D1 抽取欄位擴充（prompt ＋ schema ＋ 解析）

- `_RECEIPT_PROMPT` 要求模型額外輸出：`subtotal`／`discount`／`tax`／`shipping`（收據層級）與 `items[].discount`／`items[].tax`（行項層級）
- **金額語意**：`subtotal`＝價稅前品項合計；`total`＝實收總額。兩者差額由折扣／稅／運費解釋
- 缺值一律 `null`（不猜測）；金額字串沿用既有規則（純小數、2 位）
- `uncertain_fields`：模型列出「讀不確定」的欄位路徑（如 `total`、`currency`、`items[3].quantity`）；解析時**白名單過濾**（只留已知路徑形態），長度上限 20

### D2 算術驗證（服務端，Decimal 全程）

```
calculated_total = Σ item.subtotal − receipt_discount + tax_total + shipping
balance_status:
  - total 缺 或 calculated_total 無法算（品項皆缺價）→ unknown / incomplete
  - |calculated_total − total| < 0.01 → balanced
  - 否則 discrepancy（差額＝total − calculated_total，保留正負號）
```

- 一律 `Decimal`（`quantize(Decimal("0.01"))`），**不用浮點**
- 缺價品項（缺 `unit_price` 且缺 `subtotal`）→ 不參與合計，計入 `missing_price_count`；只要 `missing_price_count > 0` → `incomplete`（不可判斷），並在 UI 顯示「N 項待補價」
- 幣別未知（模型未讀到）→ `currency = "XXX"`（ISO 4217 no-currency，itemly 同款）→ `incomplete` ＋ UI「幣別待確認」

### D3 四態與旗標分離

- `balance_status`（單一欄位）＋ 旗標（`missing_price_count`／`uncertain_fields`／`currency == "XXX"`）
- 理由：UI 需要同時顯示「差額」與「待補價」；若合成一個狀態會遺失資訊
- 舊快照缺 `balance_status` → 視為 `unknown`（UI 不顯示判讀，既有行為不變）

### D4 幣別 `XXX` 與帳號幣別

- 未知幣別用 `"XXX"`（itemly 的 `UNKNOWN_CURRENCY`）→ 不再假設 TWD
- 我們額外提供：使用者的帳號預設幣別（`preferences.currency`）可作為「建議值」提示，但**不自動改寫**快照（避免假資料被當真）

### D5 不確定欄位（輕量版 provenance）

- 只移植 itemly 的 `uncertaintyFields`（欄位路徑清單），不做逐欄位 `fieldSources`
- UI 顯示「N 個欄位待確認」（不逐欄位列出——避免標籤/群組標頭過度資訊）

### D6 不阻擋接受（維持 Phase 33 決策）

- itemly 的規則是「未平衡收據只能存草稿」；我們的流程是**逐品項接受成物品**，且 Phase 33 明確決策「差額不阻擋接受」
- → 維持不阻擋，但群組標頭的資訊更完整，使用者可自行判斷
- 於 `docs/ai.md` 記錄此取捨與理由

### D7 契約變更與向後相容

- `ReceiptSnapshot` 擴充（**純新增欄位**）→ api-types 重生成；既有 payload 讀取端需容忍缺欄位（`extra="allow"` 已容許，但 snapshot 是明確 model → 缺欄位需有預設值）
- 舊草稿（無 `balance_status`）→ `unknown`，UI 不顯示判讀 → **不破壞既有資料**

### D8 stub 供應器同步（Phase 35）

- `ai_stub.STUB_RECEIPT` 擴充為含折扣／稅／運費的範例（讓算術驗證在 stub e2e 可被驗證）
- stub e2e（`ai-stub` 專案）的收據情境需更新斷言

---

## API payload 範例

### `GET /api/ai/drafts`（收據草稿的 `payload.receipt`）

```json
{
  "merchant": "測試商店",
  "purchased_at": "2026-01-01",
  "currency": "TWD",
  "total": "150.00",
  "item_total": "140.00",
  "subtotal": "140.00",
  "discount": "10.00",
  "tax": "0.00",
  "shipping": "0.00",
  "calculated_total": "130.00",
  "discrepancy": "20.00",
  "balance_status": "discrepancy",
  "missing_price_count": 0,
  "uncertain_fields": [],
  "page_count": 1,
  "truncated": false
}
```

（`balance_status` ∈ `balanced`／`discrepancy`／`incomplete`／`unknown`）

### 抽取回應（stub 與 live 同構）

```json
{
  "merchant": "測試商店",
  "purchased_at": "2026-01-01",
  "currency": "TWD",
  "subtotal": "140.00",
  "discount": "10.00",
  "tax": "5.00",
  "shipping": "0.00",
  "total": "135.00",
  "items": [
    {"name": "測試品項甲", "quantity": 2, "unit_price": "50.00", "subtotal": "100.00",
     "discount": "0.00", "tax": "0.00"},
    {"name": "測試品項乙", "quantity": 1, "unit_price": "40.00", "subtotal": "40.00",
     "discount": "0.00", "tax": "0.00"}
  ],
  "uncertain_fields": []
}
```

---

## 資料模型

**無 migration**：`payload.receipt` 為既有 JSON 欄位（擴充欄位，不改表結構）。

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：抽取擴充與解析

- RED：`tests/test_ai_receipts.py` 追加
  - `parse_receipt_response` 解析新欄位（subtotal／discount／tax／shipping／items[].discount／items[].tax）
  - 缺值 → `None`；金額字串容錯（沿用既有 `_decimal_or_none`）
  - `uncertain_fields` 白名單過濾（只留已知路徑形態、≤20）
  - 舊格式（無新欄位）仍可解析（向後相容）
- GREEN：`_RECEIPT_PROMPT` 擴充＋`ReceiptExtraction` 擴充＋`parse_receipt_response` 擴充

### T1.2 API：算術驗證與快照

- RED：`tests/test_ai_receipt_balance.py`（純函式）
  - `balanced`／`discrepancy`（含正負號）／`incomplete`（缺價品項、缺總額、幣別 XXX）／`unknown`
  - 缺價品項不參與合計且計入 `missing_price_count`
  - Decimal 精度（0.1 + 0.2 類情境不誤判）
- GREEN：`app/services/receipt_balance.py`（純函式）＋`ai_drafts_service` 組裝快照

### T1.3 API：端點整合

- RED：`tests/test_ai_receipts.py` 追加（`POST /api/ai/receipts` 回應含新快照欄位與 `balance_status`）
- GREEN：服務層串接

### T1.4 api-types 重生成

- 確認純新增欄位、零破壞性變更

### T2.1 Web：群組標頭四態

- RED：`components/ai/receipt-group-header.test.tsx` 追加
  - `balanced` → 「與收據總額相符」
  - `discrepancy` → 顯示**算術拆解**（品項合計 − 折扣 + 稅 + 運費 = 應付；收據總額；差額）
  - `incomplete` → 「待補價 N 項」／「幣別待確認」／「N 個欄位待確認」
  - `unknown`（舊快照）→ 不顯示判讀（維持既有畫面）
- GREEN：`components/ai/receipt-group-header.tsx` 升級

### T2.2 Web：i18n 對帳

- RED：`lib/i18n/messages.test.ts` 追加 Phase 38 鍵清單＋未使用鍵檢查
- GREEN：zh-TW／en 逐鍵插入

### T3.1 stub 供應器與 e2e 同步

- `ai_stub.STUB_RECEIPT` 擴充（含折扣／稅 → 可驗算術）
- `ai-stub` 專案的收據情境：新增「顯示算術拆解與相符判讀」斷言

### T3.2 文件收尾

- `docs/ai.md`：收據章節補「對帳四態＋算術驗證＋旗標」與「不阻擋接受」的取捨理由
- `CHANGELOG.md`：`alpha.38`
- `docs/v2-roadmap.md`／`docs/progress-2026-10-22.md`：更新
- 本計畫 Final Verification 填實測

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| 模型讀不到折扣／稅 → 大量 `incomplete`，對帳失去意義 | 缺值一律 `null`（不猜）；`incomplete` 明確區分「無法判斷」與「有差額」，不誤導使用者 |
| 金額浮點誤差造成假差額 | 全程 `Decimal`＋`quantize(0.01)`；差額門檻 0.01（沿用既有） |
| 既有草稿 payload 缺新欄位 → 500／破版 | `balance_status` 缺值視為 `unknown`；UI 不顯示判讀；API 讀取端容忍缺欄位 |
| 抽取代價太高（每次多抽 4 欄位） | 同一請求同一模型，僅多輸出欄位；`uncertain_fields` 讓模型主動標示不確定而非我們瞎猜 |
| 幣別誤判（TWD/人民幣） | 未知用 `XXX` 不猜測；帳號幣別僅作提示不自動改寫 |
| itemly 的「未平衡不得確認」未移植 | 明確記錄取捨（逐品項接受模型不同、Phase 33 決策不阻擋） |

---

## Final Verification（收尾時填實測；2026-10-22）

- [x] API：`cd apps/api && uv run pytest -q` → **1161 passed**（基線 1141；＋20）；golden eval **28 passed／1 skipped**
- [x] Web：`pnpm vitest run` → **752 passed（132 檔）**；`pnpm typecheck` → **0 error**
- [x] api-types：重生成 → **零破壞性**（107 行新增、0 刪除；`ReceiptSnapshot` 新欄位皆為選填 → 舊快照相容）
- [x] e2e（live，`--project=chromium`）：**85 passed**（無回歸）
- [x] e2e（stub，`--project=ai-stub`）：**4 passed**（收據情境新增「算術拆解」斷言）
- [x] 視覺走查（1440×900＋390×844）：收據群組標頭顯示「與收據總額相符」＋算術拆解（品項合計 140 − 折扣 10 + 稅 5 + 運費 0 = 應付 135）→ 無破版
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

### 收尾環境註記（2026-10-22）

- Worktree：`.claude/worktrees/phase38-receipt-evidence`；分支 `feature/phase38-receipt-evidence`
- Stack：compose 專案 `ims-v2`；`AI_MODE=stub` 只重建 api 容器
- 移植來源：itemly（MIT）`shared/receipt.ts`／`receipt-validation.ts`／`currency.ts`——移植**語意**（四態、算術驗證、`XXX` 幣別、不確定欄位），程式碼為 Python／TypeScript 原生改寫
- 取捨紀錄：**不移植**「未平衡收據不得確認」的強制阻擋（逐品項接受模型＋Phase 33 決策）；**不移植**逐欄位 provenance（成本高、無 UI 消費）
- 走查以臨時 Playwright 腳本執行（走查後已刪除）

---

## 測試基線（main，Phase 37 完成）

- API：1141 passed
- Web：742 passed（132 檔）
- E2E：28 spec／89 情境（chromium 85＋ai-stub 4）
