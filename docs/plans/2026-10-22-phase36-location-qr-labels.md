# Phase 36 — 位置 QR 標籤（貼在櫃子／箱子）

- **日期**：2026-10-22
- **狀態**：計畫中（TDD 任務與驗證見下文；Final Verification 收尾時填實測）
- **依據**：`docs/progress-2026-10-22.md` §六 後續候選 #1（「位置 QR 標籤：掃碼 → 該位置物品清單（貼櫃子／箱子）；平面圖欄位與掃碼流程已在」）
- **依賴**：Phase 13（QR 標籤產生與列印頁）、Phase 25（多格式掃碼引擎與條碼內查）、Phase 26（多層位置樹）
- **規模**：S（API：2 個純新增端點；Web：列印頁＋位置樹入口＋掃碼辨識；e2e：1 spec）

---

## 目標

讓**位置**（櫃子／抽屜／箱子／房間）也能貼一張 QR 標籤：掃碼後直接看到「這個位置裡有什麼」。

Phase 13 已為**物品**提供 QR 標籤（深連結 `/items/{uuid}` → 物品詳情），Phase 25 已提供多格式掃碼與內查，Phase 26 已把位置改為多層樹。本期把這三块拼起來：**位置 → QR 標籤 → 掃碼 → 該位置（含子孫）的物品清單**。

---

## 範圍

### API（純新增）

- `GET /api/locations/{location_id}/qr.png` → QR PNG（編碼位置深連結）
- `GET /api/locations/{location_id}/label` → 標籤資料 JSON（名稱／路徑／物品數／深連結）

### Web

- 列印頁 `/locations/labels`（`?ids=1,2,3`）：QR ＋ 名稱 ＋ 路徑 ＋ 物品數；**無 `ids` 時列出位置供勾選**（一次印多個櫃子）
- 位置管理頁（`/locations`）：節點「⋯」選單新增「列印標籤」→ 開啟該位置的列印頁；頁首另有「列印位置標籤」入口（勾選模式）
- 掃碼頁：辨識位置深連結 → 導向該位置的物品清單（手動輸入亦同）

### 明確不在本期範圍

- 不新增「位置詳情頁」（目的地沿用既有 `/items` 位置篩選，零重複邏輯）
- 不做標籤的批次管理／標籤歷史（QR 由位置推導，位置改名不需重印；位置 id 穩定）
- 不做位置標籤的到期／版本控管
- 不改既有物品標籤流程（`/items/labels`）
- 不改掃碼引擎（僅擴充 payload 分流）

---

## 關鍵設計決策

### D1 深連結格式：`/items?location={id}`

- 位置 id 是 **int**（非 UUID）→ 深連結以 query param 承載：`{PUBLIC_WEB_URL}/items?location={id}`
- 目的地 = **物品列表（已篩選該位置）**；`GET /api/items` 的 `location_scope` 預設為 `subtree` → 天然包含子孫（貼在房間門口也會列出櫃子裡的東西）
- **不新增目的地頁**：位置詳情頁的功能會與「物品列表＋位置篩選」完全重複，且後者已有篩選面板、搜尋、批次勾選等能力
- 沿用既有 `filtersFromSearchParams`（`location` → `locationId`），零改動

### D2 掃碼分流順序：item → location → 條碼 → 名稱

- 既有 `extractItemIdFromPayload` 只認 `/items/{uuid}`；新增 `extractLocationIdFromPayload`：URL 的 `location` 參數為正整數即命中
- 分流順序固定：**item id**（既有）→ **location id**（新）→ 條碼（既有）→ 名稱搜尋（既有）
- 兩者不衝突：item 深連結的 pathname 為 `/items/{uuid}`（無 query），位置深連結的 pathname 為 `/items`（帶 query）
- 手動輸入走**同一分流**（貼上深連結 → 導向清單）
- 掃碼結果提示新增一則「位置標籤」文案

### D3 API 端點與權限

- 兩個端點皆掛 `get_current_user`；位置以 `locations_repository.get_owned` 檢查 → 他人／不存在一律 `404`（不洩漏存在性，與既有位置端點一致）
- `qr.png` 沿用 `labels_service.render_qr_png`（同一 QR 渲染器與參數）
- `label` 回傳：`location_id`／`name`／`path`（完整路徑，如 `1F / 廚房 / 藥箱`）／`item_count`／`deep_link`

### D4 `item_count` 為**含子孫**的物品數

- 標籤貼在房間門口時，「N 件」應是整棵子樹的數量（與篩選結果一致）
- 以既有 `locations_repository.descendant_ids`（recursive CTE）取子孫集合 → 統計未刪除物品數
- 位置樹面板仍顯示**直接**物品數（既有語意不變）

### D5 列印頁版面沿用物品標籤頁

- 6cm 格、QR 2.65cm、`print:` CSS（列印時去圓角、保留邊框）、`window.print()` 觸發
- 標籤內容：QR ＋ **名稱** ＋ **完整路徑** ＋ **N 件**（位置特有資訊；物品標籤則是名稱／數量／條碼）
- 無 `ids` 時：列出全部位置（樹序）供勾選 → 勾選後即時產生標籤（不需另按「產生」）

### D6 入口

- 位置樹每個節點的「⋯」選單 →「列印標籤」→ `/locations/labels?ids={id}`（單一位置最常用）
- 位置管理頁頁首 →「列印位置標籤」→ `/locations/labels`（勾選模式，一次印多個）
- 位置標籤列印**不需寫權限**（唯讀；viewer 也可列印自己的位置標籤——但 viewer 無位置編輯權限，仍可列印已存在位置的標籤）

### D7 i18n

- 新增 `locations.labels.*`（標題／說明／列印／返回位置／勾選提示／空狀態／張數摘要／N 件）
- 新增 `scan.result.location`（掃到位置標籤的提示）
- zh-TW／en 鍵集與行數一致（既有 i18n 對帳測試守門）

### D8 測試

- **API**：`label`／`qr.png` 的 200／401／404（他人）＋ `item_count` 含子孫＋ QR 內容解碼為預期深連結
- **Web**：`extractLocationIdFromPayload` 單元測試（URL／query／非數字／無 query／item 深連結不誤判）；列印頁渲染（勾選模式與 ids 模式）
- **e2e**：位置標籤列印頁顯示 QR 與名稱；掃碼頁手動輸入位置深連結 → 導向 `/items?location=`

---

## API payload 範例

### `GET /api/locations/{id}/label`

```json
200
{
  "location_id": 8,
  "name": "藥箱",
  "path": "1F / 廚房 / 藥箱",
  "item_count": 12,
  "deep_link": "http://localhost/items?location=8"
}
```

```json
404 { "detail": "location not found" }
```

### `GET /api/locations/{id}/qr.png`

```json
200 image/png
```

（QR 內容 = `deep_link`；`Cache-Control: private, max-age=60`，與物品標籤一致）

---

## 資料模型

**無 migration**：位置標籤完全由位置推導（id／名稱／路徑／物品數），不新增資料表或欄位。

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：位置標籤端點

- RED：`apps/api/tests/test_location_labels.py`
  - `GET /api/locations/{id}/label` → 200（name／path／item_count／deep_link）
  - `item_count` **含子孫**（父節點計入子節點物品）
  - 他人位置 → 404；不存在 → 404；未登入 → 401
  - `GET /api/locations/{id}/qr.png` → 200 ＋ `image/png` ＋ PNG magic bytes
  - QR **內容**解碼為預期深連結（用 `qrcode` 內部解碼或 PIL 驗證）
- GREEN：`app/services/labels_service.py`（位置分支）＋ `app/routes/labels.py`（第二個 router）＋ `app/schemas/label.py`（`LocationLabel`）

### T1.2 api-types 重生成

- 確認純新增（2 端點＋`LocationLabel`），零破壞性變更

### T2.1 Web：位置深連結辨識

- RED：`apps/web/lib/scan/location-link.test.ts`
  - `extractLocationIdFromPayload`：`/items?location=8` → `8`；非數字／缺參數／item 深連結 → `null`
- GREEN：`apps/web/lib/scan/location-link.ts`（或併入 `barcode.ts`）

### T2.2 Web：掃碼頁分流

- RED：`apps/web/components/scan/qr-scanner-view.test.tsx` 追加
  - 掃到位置深連結 → 導向 `/items?location=8`
  - 手動輸入位置深連結 → 同上
  - 既有 item／條碼／名稱分流**不變**
- GREEN：`qr-scanner-view.tsx`（分流順序 item → location → 條碼 → 名稱）

### T2.3 Web：位置標籤列印頁

- RED：`apps/web/app/(app)/locations/labels/page.test.tsx`
  - `?ids=8` → 顯示標籤卡（QR、名稱、路徑、N 件）
  - 無 `ids` → 顯示位置清單（可勾選）→ 勾選後出現標籤
  - 空狀態文案
- GREEN：`apps/web/app/(app)/locations/labels/page.tsx` ＋ `lib/api/location-labels.ts`

### T2.4 位置管理頁入口

- RED：`apps/web/components/taxonomy/locations-panel.test.tsx` 追加（節點選單有「列印標籤」）
- GREEN：`location-tree-node.tsx`（選單項目）＋ `locations-panel.tsx`（頁首入口）

### T2.5 i18n 對帳

- RED：`apps/web/lib/i18n/messages.test.ts` 追加 Phase 36 鍵清單
- GREEN：zh-TW／en 逐鍵插入（行數一致）

### T3.1 e2e `tests/location-labels.spec.ts`

- 情境 1（列印頁）：建立位置 → 位置管理頁節點選單「列印標籤」→ 列印頁顯示 QR 與名稱
- 情境 2（掃碼導向）：手動輸入位置深連結 → 導向 `/items?location={id}` 且清單顯示該位置物品

### T3.2 文件收尾

- `docs/ai.md` 不涉及；改為 `docs/` 對應文件（位置標籤說明併入 `GUIDE_ZH-TW.md` 或 `docs/labels.md`？→ 併入 `docs/labels.md` 新章節）
- `CHANGELOG.md`：`alpha.36`
- `docs/v2-roadmap.md`：Phase 36 ✅＋測試規模
- `docs/progress-2026-10-22.md`：更新基線與候選
- 本計畫 Final Verification 填實測

---

## 狀態契約

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 位置標籤列印頁（ids 模式） | skeleton | 無此位置 → 空狀態＋返回 | 標籤載入失敗 → 重試 | 標籤卡（QR＋名稱＋路徑＋N 件） | 部分位置取不到 → 略過並提示 |
| 位置標籤列印頁（勾選模式） | 清單 skeleton | 無位置 → 空狀態 | 清單載入失敗 → 重試 | 勾選位置清單（勾選後即時產生標籤） | — |
| 掃碼頁 | 掃描中 | — | payload 非位置／條碼／UUID → 名稱搜尋 | 位置深連結 → 該位置物品清單 | — |

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| 位置深連結被誤判成物品深連結 | 兩者 pathname 不同（`/items/{uuid}` vs `/items`＋query）；分流順序固定且皆有單元測試 |
| 位置 id 可被猜測（他人位置） | 端點以 `get_owned` 檢查 → 他人位置一律 404 |
| 標籤貼紙數量多時列印錯位 | 沿用物品標籤頁的 6cm 格與 `break-inside-avoid`；`print:` CSS 去裝飾 |
| QR 內容過長 | 深連結僅含 base URL 與一個 query param（短） |
| 掃碼誤導（掃到非本系統 QR） | 非 item／location／條碼 → 名稱搜尋（既有行為） |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → 實測
- [ ] Web：`pnpm vitest run` ＋ `pnpm typecheck` → 實測
- [ ] api-types 重生成 → 零破壞性差異
- [ ] e2e：`pnpm exec playwright test --workers=1` → 實測
- [ ] 視覺走查（1440×900＋390×844）：位置標籤列印頁、位置樹選單、掃碼導向
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

---

## 測試基線（main，Phase 35 完成）

- API：1130 passed
- Web：717 passed（129 檔）
- E2E：26 spec／83 情境（chromium 79＋ai-stub 4）
