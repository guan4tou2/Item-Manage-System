# Phase 37 — 標籤列印加印條碼（Code128）＋QR 內容真值驗證

- **日期**：2026-10-22
- **狀態**：計畫中（TDD 任務與驗證見下文；Final Verification 收尾時填實測）
- **依據**：`docs/progress-2026-10-22.md` §六 後續候選 #3（「標籤列印加印條碼：Phase 25 stretch；列印頁已有（物品／位置標籤皆適用）」）
- **參考實作**（MIT，可移植／可借用）：[storagetron](https://github.com/Brain4Fish/storagetron)（Next.js 標籤工作流）、[itemly](https://github.com/Kamitoad/itemly)（收據證據鏈，候選後續 phase）
- **規模**：S–M（Web：條碼 SVG 元件＋兩處列印頁＋物品詳情；API 測試：QR 真值解碼；無 migration）

---

## 目標

1. **物品標籤加印真條碼**（Code128 條碼圖 ＋ 條碼數字）——現有標籤只有 QR 與條碼**數字**，沒有可被掃描器讀取的條碼圖。
2. **QR 內容真值驗證**——Phase 36 的 QR 內容斷言只能用「不同位置的 PNG 內容不同」近似；改用 `zxing-cpp` **實際解碼**並斷言深連結字串。

**用既有工具、不自造輪子**：

| 工具 | 用途 | 為何選它 |
|------|------|----------|
| **jsbarcode**（npm，MIT） | 前端產生 Code128 **SVG** | 成熟、支援 `displayValue`（條碼數字自動排版）；純前端 → **不需後端 PDF 產製**，既有列印頁版面幾乎不變 |
| **zxing-cpp**（PyPI，wheel，無系統相依） | 測試端解碼 QR | 純 wheel 安裝（無 zbar／OpenCV 系統相依）；讓 API 測試能斷言 QR **內容**而非近似 |
| segno / reportlab | 高容錯 QR／伺服器端 A4 PDF | **本期不採用**（列印需求已由瀏覽器列印滿足；PDF 留待後續） |

---

## 範圍

### Web

- 共用元件 `components/items/label-barcode.tsx`：以 jsbarcode 產生 Code128 SVG（條碼數字由函式庫排版）
- 套用於：單張物品標籤（`/items/{id}/label`）、批量物品標籤（`/items/labels`）、物品詳情頁（條碼區塊）
- **位置標籤不加商品條碼**（位置沒有商品碼；維持 QR ＋ 名稱 ＋ 路徑 ＋ 件數）

### API（僅測試強化）

- `tests/test_location_labels.py`／`tests/test_labels.py`：QR 內容改為**真值解碼**斷言（`zxing-cpp`）

### 明確不在本期範圍

- 不做伺服器端 PDF（reportlab）——瀏覽器列印已可用；PDF 屬「一次印大量／標籤機」需求，另開 phase
- 不做位置標籤顏色分類／標籤繼承（storagetron 的做法）——需新增位置欄位（migration），另議
- 不改任何 API 契約（`ItemLabel`／`LocationLabel` 欄位不變）
- 不支援非 Code128 的商品條碼格式（EAN/UPC 需另購 GS1 授權與測試向量）——既有資料多為使用者自訂字串

---

## 關鍵設計決策

### D1 條碼圖在前端以 SVG 產生（jsbarcode），不新增後端端點

- 條碼是**呈現層**需求：列印頁已有 QR（後端 PNG）＋文字；加一條條碼圖不該再拉一個後端端點
- SVG 而非 PNG：可列印、體積小、可 `currentColor` 跟隨列印色
- `jsbarcode` 需 DOM → **動態 import**（`import("jsbarcode")`）於 `useEffect` 內，避免 SSR／首次繪製 bundle 膨脹（比照 Phase 25 掃碼引擎的動態載入作法）

### D2 只在「可編碼」時加印條碼；不可編碼 → 退回純文字（不讓整張標籤失敗）

- 既有 `items.barcode` 為**使用者自訂字串**（`barcode_service.canonicalize` 只收斂數字／ISBN，其餘保留原樣）→ 可能含 Code128 無法編碼的字元（中文、emoji、控制字元、空白）
- 失敗策略：**捕捉並略過條碼圖**（保留既有條碼數字文字）→ 標籤仍可列印，不因一筆髒資料壞掉整批
- Code128 可編碼集合為 ASCII 0–127（含空白）；中文等 → 不可編碼 → 走 fallback

### D3 條碼數字由函式庫排版（`displayValue`），但仍保留既有純文字區塊

- jsbarcode 的 `displayValue` 會在條碼下方自動排印數字（與實務標籤一致）
- 既有頁面已有一行純文字條碼 → **保留**（避免無 JS／列印邊界時完全看不到條碼值）

### D4 QR 內容真值驗證（zxing-cpp）

- `zxing-cpp` 提供 `zxingcpp.read_barcode(image)` → 直接解碼 PIL 影像
- API 測試斷言：位置 QR 內容 == `location_deep_link(id)`；物品 QR 內容 == `…/items/{uuid}`
- 取代 Phase 36 的「兩個 PNG 不相同」近似 → 契約更明確（連結格式一改就會紅）

### D5 條碼圖的版面

- 單張／批量物品標籤：條碼圖置於**條碼數字文字之上**、QR 之下（QR 仍為主識別碼；條碼為備援掃描路徑）
- 高度約 1.1cm（寬度自适应）——避免 4cm 高的標籤卡被擠爆（Phase 36 曾因固定高度裁切文字 → 已改 `min-h-[4cm]`）
- 條碼區塊加 `data-testid="label-barcode"` 供測試與視覺走查定位

### D6 授權與相容

- jsbarcode（MIT）、zxing-cpp（Apache-2.0）皆為寬鬆授權，可安全引入
- 本專案 README 宣稱 MIT 但倉庫**缺 LICENSE 檔** → 本期一併補上（否則引用他人 MIT 程式碼時授權聲明不完整）

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：QR 內容真值解碼（測試強化）

- RED→GREEN：`tests/test_location_labels.py`＋`tests/test_labels.py`
  - 新增 `zxing-cpp` 為測試依賴（`apps/api/pyproject.toml` 的 `test` extra）
  - 位置 QR 解碼 == `location_deep_link(id)`；物品 QR 解碼 == `…/items/{uuid}`
  - 移除 Phase 36 的「PNG 內容不同」近似斷言
- 無 API 行為變更（僅測試）

### T2.1 Web：條碼 SVG 元件

- RED：`components/items/label-barcode.test.tsx`
  - 有可編碼條碼 → 產生 `<svg>`（含條碼數字）
  - 不可編碼字串（中文／emoji）→ **不產生** svg，且不拋錯（退回純文字）
  - 空值 → 不渲染
- GREEN：`components/items/label-barcode.tsx`（動態 import jsbarcode；`data-testid="label-barcode"`）

### T2.2 套用至三處

- RED：既有測試追加（單張標籤／批量標籤／物品詳情頁各一項）
- GREEN：改 `app/(app)/items/[id]/label/page.tsx`、`app/(app)/items/labels/page.tsx`、`app/(app)/items/[id]/page.tsx`

### T2.3 i18n

- 僅在需要時新增（例如無障礙說明）；否則沿用既有鍵

### T3.1 e2e

- 物品標籤列印頁（`/items/{id}/label`）顯示條碼 SVG ＋ 數字；批量標籤頁顯示條碼
- 不可編碼條碼 → 頁面仍正常（不拋錯）

### T3.2 文件收尾

- `User_Manual_zh-TW.md`：條碼章節補「標籤含 Code128 條碼圖」
- `CHANGELOG.md`：`alpha.37`
- `docs/v2-roadmap.md`：Phase 37 ✅＋測試規模
- `docs/progress-2026-10-22.md`：基線與候選更新
- 補 `LICENSE` 檔（MIT，README 已宣稱）
- 本計畫 Final Verification 填實測

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| 使用者自訂條碼含 Code128 無法編碼的字元 | D2：捕捉錯誤並退回純文字，標籤仍可列印（有單元測試覆蓋） |
| jsbarcode 需 DOM → SSR／hydration 問題 | 動態 import 於 `useEffect`；SSR 不渲染條碼（列印時由使用者互動觸發的列印視窗已含 SVG） |
| 條碼圖把標籤卡擠出 4cm | D5：條碼高 1.1cm ＋ 標籤卡 `min-h-[4cm]`（Phase 36 已改內容驅動高度） |
| jsbarcode 進入首次繪製 bundle | 動態 import（`next/dynamic` 不適用於純函式 → 以 `import()` 於 effect 內） |
| 引入新依賴的風險 | jsbarcode（MIT，3.12.3，前端）、zxing-cpp（Apache-2.0，wheel）皆無系統相依；版本固定於 lockfile |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → 實測（含 QR 真值解碼）
- [ ] Web：`pnpm vitest run` ＋ `pnpm typecheck` → 實測
- [ ] e2e：`pnpm exec playwright test --project=chromium --workers=1` → 實測
- [ ] 視覺走查（1440×900＋390×844）：單張／批量物品標籤的條碼圖與版面
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

---

## 測試基線（main，Phase 36 完成）

- API：1139 passed
- Web：734 passed（131 檔）
- E2E：27 spec／86 情境（chromium 82＋ai-stub 4）
