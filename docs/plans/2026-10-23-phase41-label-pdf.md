# Phase 41 — 伺服器端物品標籤 PDF（A4 貼紙、QR＋Code128）

- **日期**：2026-10-23
- **狀態**：🚧 進行中
- **依據**：`docs/v2-roadmap.md` 下一輪候選 #2（「伺服器端標籤 PDF：以 reportlab 產 A4 貼紙 PDF，供標籤機／一次印大量；瀏覽器列印頁已可用」）
- **規模**：M（API：PDF 服務＋端點＋2 個執行期依賴；Web：批量標籤頁加下載鈕；e2e：1 情境；**無 migration**）
- **契約變更**：無（純新增端點；既有 `/api/items/{id}/qr.png`、`/label` 不變）

---

## 目標

Phase 36／37 已有**瀏覽器列印頁**（單張／批量物品標籤、地點標籤），但「一次印大量」仍得開瀏覽器、等 QR 一張張載入、叫出列印對話框，且不同瀏覽器的邊界與縮放會讓貼紙對位跑掉。本 phase 新增**伺服器端 PDF**：

- `GET /api/items/labels.pdf?ids=…` → 一份 A4 PDF，直接送標籤機或一般印表機
- 每頁 **21 張**（3 欄 × 7 列）、每張 **63.5 × 38.1 mm**，固定版面、不由瀏覽器縮放
- 每張含：**QR**（物品深連結，與現有 QR 相同）、**Code128 條碼圖**、**名稱**、**短 id／數量**、**條碼數字**
- `start` 參數可跳過前 N 格 → **重用印過一半的貼紙 sheet**
- 批量標籤頁多一顆「下載 PDF」按鈕（既有「列印」保留）

---

## 範圍

### API

- 新增 `apps/api/app/services/label_pdf_service.py`
  - `render_item_labels_pdf(labels, *, start=0) -> bytes`
  - 版面常數（A4、3×7、63.5×38.1mm）、CJK 換行／截斷、Code128 可編碼性
- `apps/api/app/services/labels_service.py`
  - `get_item_labels_bulk(session, owner_id, item_ids) -> list[dict]`（單一查詢、保留請求順序、缺任何一筆 → 404）
- `apps/api/app/repositories/items_repository.py`
  - `get_owned_many(session, owner_id, item_ids) -> list[Item]`（`IN` 查詢，過濾軟刪）
- `apps/api/app/routes/labels.py`
  - `GET /api/items/labels.pdf`（`ids` 重複參數、1–100 筆；`start` 0–20）
- 字型資產：`apps/api/app/assets/fonts/NotoSansTC-Regular.ttf`（OFL 1.1）＋ `OFL.txt`／`README.md`
- 依賴：`reportlab==5.1.0`、`python-barcode==0.16.1`（執行期）；`pypdfium2==5.14.0`（測試）

### Web

- `lib/api/labels.ts`：`getItemLabelsPdf(ids, token) -> {blob, filename}`（重複 `ids`、讀 `Content-Disposition` 檔名）
- `/items/labels` 頁：加「下載 PDF」按鈕（下載中 disabled、失敗顯示訊息）
- i18n：`items.labels.downloadPdf`／`items.labels.downloadFailed`（zh-TW／en）
- 單元測試：lib（URL／auth／檔名）＋頁面（按鈕、點擊下載）

### 測試

- `apps/api/tests/test_label_pdf.py`：
  - 權限／404（他人、不存在、已軟刪；全有全無）
  - 參數驗證（空 ids、>100、`start` 越界 → 422）
  - 檔頭 `%PDF`、`application/pdf`、`Content-Disposition` 檔名
  - 頁數（21 張 1 頁、22 張 2 頁、`start` 造成換頁）
  - **真值解碼**：PDF raster 後 QR 解出深連結、Code128 解出 barcode 值
  - 無條碼／中文條碼 → 不畫 Code128，QR 與文字仍在
  - 重複 ids 去重
- `apps/web/tests/label-barcode.spec.ts`：批量標籤頁點「下載 PDF」→ 檔名符合 `item-labels-YYYYMMDD.pdf`、內容以 `%PDF` 開頭

### 明確不在本期範圍

- **不做位置標籤 PDF**：位置數量少、瀏覽器列印已足夠；物品才是「一次印大量」痛點（列為後續候選）
- 不做標籤版型自訂（尺寸／欄數／字型大小）：固定一組實測可對位的版面，避免 UI 與測試膨脹
- 不做 PDF 內的圖片（物品照片）：標籤以 QR＋條碼＋文字為主，照片會讓檔案變大且列印品質不穩
- 不做非同步 job／暫存檔：100 張以內同步產生（實測記憶體與時間可接受）
- 不改 `items` 表、不加欄位 → **無 migration**

---

## 關鍵設計決策

### D1 端點與語意

```
GET /api/items/labels.pdf?ids=<uuid>&ids=<uuid>&start=0
```

- `ids` **重複 query 參數**（與既有 `/items/labels?ids=` 頁面一致），去重後 1–100 筆
- **全有全無**：任一 id 不存在／已軟刪／非本人 → `404 item not found`。理由：默默跳過會讓使用者拿到少幾張的 PDF 卻不知道；批量頁本身已在前端過濾掉載入失敗的項目
- `start`：0–20，跳過第一頁前 N 格（重用部分使用過的貼紙）
- 回應：`application/pdf`、`Content-Disposition: attachment; filename="item-labels-YYYYMMDD.pdf"`、`Cache-Control: private, no-store`（含個人資料，即時產生）

### D2 版面：A4 × 21 格（3×7）

| 參數 | 值 |
|---|---|
| 紙張 | A4 210 × 297 mm |
| 欄 × 列 | 3 × 7（21 張／頁） |
| 標籤 | 63.5 × 38.1 mm |
| 左右邊界 | 9.75 mm（(210 − 190.5) ÷ 2） |
| 上下邊界 | 15.15 mm（(297 − 266.7) ÷ 2） |
| 欄距／列距 | 0（切線對齊；空白貼紙可直接裁切） |
| 順序 | 由左至右、由上至下（列優先） |

- 每格畫 **0.25pt 淺灰裁切線**（含空格），方便對位與裁切
- 單格內容：
  - 左：QR 19 × 19 mm（深連結）
  - 右上：名稱（8.5pt，最多 2 行，超出以 `…` 截斷）
  - 右下：`#abcdef12 · x2`（6.5pt 灰）
  - 底部：Code128 圖（高 8mm，寬度最多 59.9mm，等比縮放）＋條碼數字（6pt）
- 無條碼／不可編碼 → 底部只留空白（名稱與 QR 不動），整批不因一筆壞資料失敗

### D3 內容與既有 QR 完全一致

- QR payload = `labels_service._deep_link_for(item.id)`（`public_web_url` + `/items/{id}`）
- 名稱／數量／條碼值皆取自既有 `ItemLabel` 語意；PDF 與瀏覽器列印頁看到的是同一組資料，不新增第二套口徑
- 不新增 location path 欄位：與現有標籤一致，避免版面擁擠

### D4 技術選型：reportlab＋內嵌 Noto Sans TC＋既有 qrcode＋python-barcode

- **reportlab**（BSD-3）：A4 版面、向量裁切線、文字與圖片定位；成熟、無系統相依（wheel）
- **qrcode**（既有執行期依賴）：沿用 `labels_service.render_qr_png()` 同一個函式，QR 口徑不分叉
- **python-barcode**（MIT）：Code128 → PNG；`ImageWriter` 可關閉人類可讀文字、指定 module 寬度／DPI
- **不使用 reportlab 內建 barcode widget**：reportlab 5.x 的 `QrCodeWidget`／`Code128` API 與 4.x 文件不一致（`QrCodeWidget` 已不是可加入 `Drawing` 的 Shape），改用成熟獨立套件可避免版本綁定
- **字型：內嵌 Noto Sans TC 子集**（OFL 1.1，`app/assets/fonts/NotoSansTC-Regular.ttf`，約 6.6 MB）
  - 以 `fontTools` 固定 `wght=400`、保留全部 cmap 字元（20,745 個，含繁中、簡中、日文假名、拉丁），移除 reportlab 不需要的排版表
  - reportlab 會**只嵌入實際用到的字形子集**（單張標籤 PDF 約 20 KB），不會把 6.6 MB 全部塞進每份 PDF
  - **為何不用 reportlab 內建 CID 字型（STSong-Light／MSung-Light）**：CID 字型不嵌入，交由檢視器替換；實測 PDFium 對「舊、電、風、臺、灣、櫃、無、碼」等繁中字直接缺字，Docker／Linux 或標籤機的結果不可控。內嵌 TTF 才能保證各環境一致
  - 限制：Noto Sans TC 未涵蓋的極少數字元（部分日文新字體漢字、emoji）會顯示缺字框；瀏覽器列印頁仍可作為備援

### D5 Code128 可編碼性與長度

- 與 Phase 37 前端同一條規則：**可列印 ASCII（0x20–0x7E）且去空白後非空**才畫條碼
- `items.barcode` schema 上限 32 字元；PDF 依實際像素寬度**等比縮到可用寬度**，數字仍以文字呈現（掃不到時可手動輸入）
- 不可編碼（含中文／控制字元）→ 不畫條碼圖，不拋錯

### D6 `start`：重用部分貼紙

- `start=0..20`；第 `i` 張標籤放在 `slot = start + i`，`slot // 21` 為頁碼（0-based）、`slot % 21` 為格位
- 例：`start=20` + 2 張 → 第 1 頁最後一格 1 張、第 2 頁第 1 格 1 張
- UI 不暴露 `start`（預設 0）；需要時可直接打 API 或未來再加欄位

### D7 錯誤與效能

- 100 筆以內：一次 `SELECT ... WHERE id IN (...)`（不 N+1）、同步產生 PDF；單檔實測 < 1 MB
- 缺 id → 404；參數錯誤 → FastAPI 422（`ids` 空／超過 100、`start` 越界）
- PDF 產生失敗 → 500（不寫半套檔案；記憶體 buffer 一次回傳）

### D8 測試策略：對 PDF 做真值解碼

沿用 Phase 37 的原則「不是看圖有出來，而是真的解得出來」：

1. `pypdfium2` 把 PDF 頁面 raster 成 PIL Image（scale 3–4）
2. `zxing-cpp` 解 QR 與 Code128，斷言**內容等於**深連結／barcode 值
3. 文字以 `pypdfium2` 的文字頁擷取（必要時輔以 `pypdf`）斷言名稱、短 id、數量

這能抓到「圖畫了但內容錯、密度太高掃不到、QR 被裁掉」等瀏覽器截圖測試抓不到的問題。

### D9 Web 下載流程

- `getItemLabelsPdf()` 用 `fetch` 帶 Bearer（與其他 API 相同），**不能用** `<a href>` 直接連（無 Authorization）
- 從 `Content-Disposition` 解析檔名；失敗則退回 `item-labels.pdf`
- 下載用暫存 object URL，點擊後 revoke；下載中按鈕 disabled，失敗顯示 `items.labels.downloadFailed`
- 「下載 PDF」按鈕只加在 header；既有「列印」按鈕與 `print:` 樣式不動
- **附帶修正（實作時發現）**：批量預覽卡片原本固定 `h-[4cm]`，內容（QR 2.65cm＋名稱＋短 id＋條碼＋數字）遠超過 4cm，flex 把名稱與 id 壓成 0 高度 → 畫面上看不到文字。改為 `min-h-[4cm]`（卡片隨內容長高），名稱與短 id 恢復可見；列印仍維持 6cm 寬卡片

### D10 依賴與供應鏈

- `reportlab==5.1.0`、`python-barcode==0.16.1`（執行期，wheel、純 Python／Pillow）
- `pypdfium2==5.14.0`（**測試 only**，wheel、無系統 poppler 需求）
- 內附 `NotoSansTC-Regular.ttf`（OFL 1.1；來源與子集化步驟見 `apps/api/app/assets/fonts/README.md`）
- 授權皆為寬鬆授權（BSD／MIT／Apache-2.0／OFL），符合專案 MIT

---

## API 範例

```
GET /api/items/labels.pdf?ids=6f1c…&ids=9a2b…&start=0
Authorization: Bearer <access token>

200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="item-labels-20261023.pdf"
Cache-Control: private, no-store

%PDF-1.7 …
```

錯誤：

| 情境 | 回應 |
|---|---|
| 未登入 | 401 |
| 任一 id 非本人／不存在／已刪 | 404 `item not found` |
| `ids` 空或 >100 | 422 |
| `start` <0 或 >20 | 422 |

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：依賴與 PDF 產生器

- `pyproject.toml` 加 `reportlab`／`python-barcode`；test extra 加 `pypdfium2`
- `label_pdf_service.py`：版面常數、`_wrap_cjk`、`render_item_labels_pdf`
- RED：固定 3 筆資料 → 1 頁、A4 尺寸、`%PDF` 開頭；QR／Code128 可被 zxing 解出

### T1.2 API：批量取資料與端點

- `items_repository.get_owned_many`、`labels_service.get_item_labels_bulk`
- `routes/labels.py`：`GET /labels.pdf`（Query 驗證、headers）
- RED：404 全有全無、422 邊界、去重、100 筆 5 頁

### T1.3 API：版面邊界

- RED：22 張 → 2 頁、`start=20` + 2 張 → 2 頁、無條碼／中文條碼 → 只解到 QR、`start=0/20` 不越界
- RED：長名稱截斷（以文字擷取確認 `…`，且不拋錯）

### T2.1 Web：下載 lib

- `getItemLabelsPdf`＋單元測試（重複 ids、Authorization、檔名解析、無 header fallback）

### T2.2 Web：按鈕與 i18n

- `/items/labels` 加按鈕、下載狀態、錯誤訊息
- 頁面測試（按鈕存在、點擊呼叫、object URL revoke）
- i18n 兩鍵（zh-TW／en）

### T3.1 e2e

- `label-barcode.spec.ts` 增「下載 PDF」情境：檔名 pattern、`%PDF` 檔頭

### T3.2 文件

- `CHANGELOG.md` alpha.41、`FEATURES.md` 標籤章節、`docs/v2-roadmap.md`（完成表＋候選重編號）、`docs/progress-2026-10-23.md`（更新為 Phase 40–41）、本計畫 Final Verification

---

## 測試清單（RED 先寫）

| # | 測試 | 期望 |
|---|---|---|
| 1 | 1 張物品 | 1 頁、A4、`%PDF`、`application/pdf`、檔名 `item-labels-YYYYMMDD.pdf` |
| 2 | QR 真值 | raster 後解出 `public_web_url + /items/{id}` |
| 3 | Code128 真值 | raster 後解出 barcode 值 |
| 4 | 名稱／短 id／數量 | 文字頁含名稱、`#` + 前 8 碼、`x2` |
| 5 | 21 張 | 1 頁 |
| 6 | 22 張 | 2 頁 |
| 7 | `start=20` + 2 張 | 2 頁 |
| 8 | `start=21` | 422 |
| 9 | 無 ids | 422 |
| 10 | 101 個 ids | 422 |
| 11 | 他人／不存在／已刪 | 404，且不回傳 PDF |
| 12 | 重複 ids | 只出現 1 張（解到 1 個 QR） |
| 13 | 無 barcode | 只解到 QR，無 Code128 |
| 14 | 中文 barcode | 不畫 Code128、不拋錯 |
| 15 | 長名稱 | 2 行內截斷（含 `…`）、不溢出 |
| 16 | Web lib | URL 重複 `ids`、帶 Bearer、解析檔名 |
| 17 | Web 頁面 | 按鈕存在、點擊下載、失敗顯示訊息 |
| 18 | e2e | 下載檔名符合 pattern、內容 `%PDF` |

---

## 風險與對策

| 風險 | 影響 | 對策 |
|---|---|---|
| 標籤中文缺字 | 名稱空白或豆腐框 | 內嵌 Noto Sans TC（OFL）子集，不依賴系統字型；PDF 只嵌用到的字形（約 20 KB／張） |
| 字型檔體積 | repo 增加約 6.6 MB | 只保留一個字重與 reportlab 需要的表；PDF 端仍為子集嵌入 |
| 條碼太長／太密掃不到 | 標籤機讀不到 | schema 上限 32 字、等比縮放、數字另以文字呈現；測試以真值解碼驗證 |
| 貼紙對位不準（printer margin） | 內容偏出標籤 | 固定 21 格＋淺灰裁切線；`start` 支援重用；文件說明以 100% 比例列印 |
| 100 筆同步產生太慢 | 請求 timeout | 單一查詢＋圖片小；實測建立上限；必要時未來改非同步 job |
| reportlab 5.x API 與舊範例不符 | 開發卡住 | 不使用內建 barcode widget；只用穩定的 canvas／ImageReader |
| 檔名標頭被瀏覽器忽略 | 下載檔名不符 | Web 解析 `Content-Disposition`；e2e 驗證 |
| 既有批量標籤頁測試因新增按鈕失敗 | 假紅 | 只新增元素、不改既有文字與結構；必要時更新 snapshot（目前無 snapshot） |

---

## 實作結果（與計畫差異）

- **端點與語意照計畫落地**：`GET /api/items/labels.pdf`（`ids` 重複參數、去重後 1–100；`start` 0–20）；任一筆不可見 → 404（全有全無）；`get_owned_many()` 以單一 `IN` 查詢避免 N+1；`Cache-Control: private, no-store`。
- **字型方案在實作中改為「內嵌 Noto Sans TC 子集」**：原計畫用 reportlab CID `MSung-Light`，但實測 PDFium 對「舊、電、風、臺、灣、櫃、無、碼」等繁中字直接缺字（CID 不嵌入，交由檢視器替換）。改內附 `NotoSansTC-Regular.ttf`（OFL 1.1，約 6.6 MB；`wght=400`、保留 20,745 個 cmap 字元），reportlab 只嵌實際用到的字形（字型子集約 20 KB／份）。來源、授權與重製步驟見 `apps/api/app/assets/fonts/README.md`。
- **reportlab 5.x barcode widget 不採用**：`QrCodeWidget` 已不是可加入 `Drawing` 的 Shape、`Code128` 變成 Flowable，與 4.x 文件不相容。QR 沿用既有 `qrcode`，Code128 用 `python-barcode` 產 PNG，再以 `ImageReader` 畫入 PDF。
- **路由順序**：`/api/items/labels.pdf` 會被 items router 的 `GET /api/items/{item_id}` 先匹配（UUID 驗證 → 422）。已把 `labels.router` 移到 `items.router` 之前（`app/main.py`，附註解）。
- **OpenAPI**：`response_class=Response` 讓 200 只宣告 `application/pdf`（不再多一個空的 `application/json`）；api-types 新增 1 個 path，另有 router 順序造成的 path 排序變動（非語意變更）。
- **Web 附帶修正**：批量標籤預覽卡片原本固定 `h-[4cm]`，但 QR 2.65cm＋名稱＋短 id＋條碼＋數字遠超 4cm，flex 將名稱／短 id 壓成 0 高度（畫面看不到文字）。改 `min-h-[4cm]` 後恢復可見；下載 PDF 按鈕與錯誤訊息一併加入。
- **測試**：API 新增 13 個案例（原 1206 → 1219）；Web 新增 4 個（原 765 → 769）；e2e 新增 1 個（原 87 → 88）。PDF 測試會在 raster 後以 zxing 真值解碼 QR／Code128，並斷言 `/FontFile2` 確認字型內嵌。

---

## Final Verification

| 項目 | 結果 |
|---|---|
| API 測試 | **1219 passed**（`uv run pytest -q`，3 分 27 秒） |
| API golden eval | **28 passed／1 skipped**（`uv run pytest evals/ -q`） |
| Web 測試 | **769 passed（132 檔）**（`pnpm vitest run`） |
| Web 型別 | **0 error**（`pnpm typecheck`） |
| E2E（live） | **28 spec／88 情境 passed**（chromium、`--workers=1`；docker compose live stack） |
| api-types | 新增 `/api/items/labels.pdf`；path 排序變動為 router 順序所致 |
| Migration | `0025 (head)`；本 phase 無 migration |
| PostgreSQL | live stack 實測：登入 → 建物品 → 批量標籤頁 → 下載 PDF（nginx → API → PG），檔名與 `%PDF` 正確 |
| 字型 | `test_label_pdf.py` 斷言 `/FontFile2`；PDF 於 PDFium raster 後繁中文字可讀（視覺檢查 A4 樣張） |
| 條碼真值 | QR 解出 `public_web_url + /items/{id}`；Code128 解出 barcode 值 |

---

## 測試基線（main，Phase 41 完成）

- API：**1219 passed**；Web：**769 passed（132 檔）**；typecheck 0 error
- e2e：chromium **88 passed**（`--workers=1`）；ai-stub 4
- Migration：`0025 (head)`；本 phase **無 migration**
- Phase 40 稽核 action：12 種
- 新增端點：`GET /api/items/labels.pdf`（`ids` 1–100、`start` 0–20）
