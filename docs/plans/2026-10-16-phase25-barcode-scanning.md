# Phase 25 — 條碼掃描（內查＋外查） Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 25（L376–407）＋ §5.4 掃碼列、§5.7 掃描 FAB、§5.4 補充（掃碼手輸 prefill）。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**。
> 完成任一 task 即 commit（Conventional Commits，`feat(api): …`／`feat(web): …`／`test(web): …`）。

**Goal：** 掃 EAN/UPC/ISBN → 系統內快速定位（單筆直接跳轉／多筆候選列表）；查無 → 外部資料庫（Open Food Facts／Open Library）帶入新增表單；`barcode_lookups` 快取 30 天；`items.barcode` 欄位（表單／詳情／CSV）；`/scan` 由純 QR 擴充為 QR＋1D 多格式；行動版掃描 FAB；既有 QR 流程零回歸。

**Architecture：** 掃描（原生 `BarcodeDetector` 快路徑／`@zxing/browser` fallback）→ payload 分流（既有 deep link/UUID｜條碼 canonical）→ `GET /api/barcodes/{code}` → 內查（owner 範圍、canonical 精確比對）→ 非空：跳物品頁／候選列表；空：外查（provider 抽象：978/979/ISBN-10→Open Library、EAN/UPC→Open Food Facts；httpx timeout 3s、fail-soft）→ 正/負結果寫快取（TTL 30 天）→ 外查 ok：來源標註＋`/items/new?barcode=…`（表單以同一 hook hydrate，快取命中即時）／not_found：「查無公開資料，已帶入條碼，請補名稱」／unavailable：「網路不穩，條碼已保留」＋重試。

**Tech Stack：** FastAPI、SQLAlchemy async、Alembic（migration `0019`）、pytest（provider monkeypatch；SQLite in-memory）、React Query、next-intl、shadcn/ui、Vitest、Playwright。**新增依賴：`@zxing/browser`（＋peer `@zxing/library`）；移除 `qr-scanner`**（單一引擎同時支援 QR 與 1D）。

**關鍵既有資產（重用，勿重造）：**
- QR 掃描：`apps/web/components/scan/qr-scanner-view.tsx`（`extractItemIdFromPayload`、deep link／UUID 導頁、手動輸入名稱搜尋、權限/錯誤處理）＋ `qr-scanner-view.test.ts`；`/scan` 頁 `apps/web/app/(app)/scan/page.tsx`（dynamic import, `ssr: false`）
- 掃描入口：`nav-items.ts`（`scan` → `/scan`）；`app-header.tsx` 桌面 nav（`NAV_ITEMS` 渲染）＝桌面 toolbar 入口保留
- shell：`app-shell.tsx`（header＋main；**目前無底部導覽**，FAB 僅需避 safe-area）＋ `mobile-nav.tsx`（drawer）
- 表單：`item-form.tsx`（AI 建議／模板套用「只填不覆蓋＋來源標註」既有模式）＋ `items/new/page.tsx`（`defaultValues={empty}`；未接 searchParams）
- 詳情：`items/[id]/page.tsx` `<dl>` 區（description/notes 列慣例）
- 圖片：`lib/api/images.imageUrl(image_id)`（縮圖）；`ItemRead.image_id` 已存在
- 位置路徑顯示慣例：`[floor, room, zone].filter(Boolean).join(" / ")`（`items-table.tsx:153`）
- CSV：`csv_service.py` `EXPORT_COLUMNS`（16 欄）／`IMPORT_OPTIONAL`；round-trip 既有測試
- 清單搜尋：`items_repository.py:105`（`q` → name/description ilike）
- httpx 慣例：`external_notifications.py`（`httpx.AsyncClient(timeout=…)`）
- `JSONType`（`app/models/favorite_audit_token.py`；PG JSONB／SQLite JSON 兩用）
- 快取並發吸收先例：`expiry_alert` savepoint＋IntegrityError（Phase 24）
- e2e 慣例：zh-TW locale、`request.post("/api/auth/register")`、admin 階梯（`reminders.spec.ts`）

**盤點定案（2026-10-16，實作前一覽）：**
1. **canonicalize（正規化）**：trim → 去除空白／連字號／底線；結果符合 `^\d{8,14}$` 或 `^\d{9}[\dXx]$`（ISBN-10）→ 收斂為數字（X 大寫）；否則保留 trim 原樣（Code128 等英數 SKU 不破壞）。**寫入時正規化**（表單／CSV／API 同一函式；API 端為權威）。
2. **分類（server 權威）**：ISBN-10（mod-11 checksum）／ISBN-13（`978`/`979` 前綴＋EAN checksum）→ `openlibrary`；EAN-13（非 978/979）／EAN-8／UPC-A（12 位）checksum 有效 → `openfoodfacts`；其餘（含 checksum 無效）→ 無 provider（外查 `unsupported`，仍做內查）。
3. **內查優先**：`local_matches` 非空 → **不呼叫外部**（`external_status: "skipped"`、`external: null`）——省外部呼叫，UI 先呈現既有物品（roadmap：查無 → 外查）。
4. **端點**：`GET /api/barcodes/{code}`——任何登入者（匿名 401）；空／>64 字 → 422。回應（`cached` 供透明標記，UI 可不顯示）：
   ```json
   {
     "code": "4710085200014",
     "local_matches": [
       {"id": "…", "name": "…", "quantity": 2, "image_id": "…|null", "location_path": "1F / 廚房 / 上櫃"}
     ],
     "external": {"source": "openfoodfacts", "name": "…", "description": "…", "image_url": "…|null", "suggested_category_id": 3},
     "external_status": "ok | not_found | unavailable | unsupported | skipped",
     "cached": false
   }
   ```
5. **外部↔使用者分類建議**（roadmap「分類建議」）：server 以 **外部分類字串**與使用者**葉分類名稱字面比對**（不分大小寫，類名長度 ≥2；唯一命中才填 `suggested_category_id`，多重命中＝不建議）；無法可靠映射時不建議（分類樹為使用者自訂）。外部分類原文仍併入 description 文字。
6. **快取 `barcode_lookups`**：`code` UNIQUE＋`source`＋`payload`（`JSONType` nullable＝**查無負快取**）＋`fetched_at`；TTL `30` 天（讀取時判定，過期重抓覆寫）；**`unavailable`（逾時/網路/非 JSON/5xx）不寫快取**；並發以 savepoint 吸收 `IntegrityError` → 改 UPDATE。
7. **Provider**：`BarcodeProvider` protocol（`name`、`async fetch(code) -> ExternalResult | None`，None＝查無）；registry `{openfoodfacts, openlibrary}`。
   - Open Food Facts：`https://world.openfoodfacts.org/api/v2/product/{code}.json?fields=product_name,brands,categories,quantity,image_front_small_url`——`status==1` 命中；`status==0`／404 → not_found；name＝`product_name`；description＝`[brands, categories, quantity]` 非空以「，」串接；image＝`image_front_small_url`。
   - Open Library：`https://openlibrary.org/api/books?bibkeys=ISBN:{code}&format=json&jscmd=data`——空物件 → not_found；name＝`title`；description＝`作者：A、B；出版：YYYY；出版社：X`（缺項省略）；image＝`cover.medium|small`。
   - 逾時 3 秒；任何 `httpx.HTTPError`／`ValueError`（JSON 解析失敗）／格式意外 → `unavailable`（fail-soft，**不得 500**）。
8. **外部→表單 prefill**：`/items/new?barcode=…`；表單以同一 lookup hook 查（server 快取命中即時）；**只填空白欄位**（name／description；不覆蓋已輸入）＋來源標註（Open Food Facts／Open Library）；`suggested_category_id` 於分類欄未選時帶入；`local_matches>0` → 顯示「已有 N 件同條碼物品」提示＋連結（指 `/items?q=<barcode>`），不做外部 prefill。
9. **表單 barcode 欄位**：手輸（正規化上限 32 字）；旁「查詢」小按鈕＝對欄位值執行同一 lookup（回填自身欄位正規化值＋只填空欄）；儲存隨 payload 送出。**不做表單內建相機**——「掃描輸入」＝由 `/scan` 流程帶入（`?barcode=`）；表單不自動查詢（除 `?barcode=` 帶入時）。
10. **掃描引擎**：`createBarcodeEngine(video, onDecode)` 統一介面——原生 `BarcodeDetector`（含 `getSupportedFormats` 過濾）可用→快路徑；否則 `@zxing/browser` `BrowserMultiFormatReader` hints〔QR_CODE, EAN_13, EAN_8, UPC_A, UPC_E, CODE_128, CODE_39, ITF〕＋TRY_HARDER（「先 QR 再 1D」＝同reader 內多格式自動，使用者無模式選擇）。**移除 `qr-scanner`**；QR 行為零回歸（deep link/UUID 導頁、非條碼→手動輸入名稱搜尋）。
11. **掃描頁分流**：decode → ①deep link／UUID → 導頁（既有）②canonical 條碼候選 → lookup query（載入中「查詢外部資料庫…」）③`local_matches` 1 筆 → push 物品頁；多筆 → 候選列表（縮圖／名稱／位置路徑／數量＋總數標題）；0 筆 → 外查三態卡 ④其餘 payload → 手動輸入保底（既有名稱搜尋）。手動輸入欄位：值為條碼候選 → 走 ②；否則名稱搜尋（既有）。
12. **權限被拒**：全頁空態（相機區塊）＋「開啟權限」按鈕（重新嘗試啟動相機）＋手動輸入保底（輸入框照常可用）。
13. **清單搜尋**：`q` 併入 `barcode` ilike（contains；canonical 儲存、輸入正規化由掃描/表單路徑處理，不另設端點）。
14. **詳情頁**：`barcode` 列（monospace）＋複製按鈕（toast「已複製」），僅有值時顯示。
15. **CSV**：匯出 `barcode` 欄（置於 `description` 後；值＝canonical 或空）＋匯入可選欄（套 canonicalize）；round-trip 測試。
16. **FAB**：`scan-fab.tsx`——僅 `md` 以下顯示（`md:hidden`）、`fixed` 右緣底部＋`env(safe-area-inset-bottom)`、≥44px、`aria-label`、連結 `/scan`；掛載於 `app-shell`（僅登入區）；桌面入口不動（§5.7）。
17. **標籤 stretch**：`items/[id]/label` 於 QR 下方加印**條碼數字文字**（有 barcode 時；不渲染條碼圖形）。
18. e2e 不依賴外部網路：外部三態以 API 測試（provider mock）＋元件測試（hook mock）覆蓋；e2e 專注內查（單/多筆）／表單 prefill（local 命中）／CRUD＋搜尋／FAB。

**執行前置：**
- worktree：`phase25-barcode-scan`（branch `claude/phase25-barcode-scan`）
- alembic head＝`0018`；T1.1 後以 `docker compose cp`＋`alembic upgrade head` 對真實 PG 驗證
- Phase 3（e2e）前 `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web`（worktree `.env` 需含 `ENABLE_DEV_ROUTES=1`，比照 Phase 24）
- 依賴：`pnpm -F @ims/web add @zxing/browser`（T2.1）；`pnpm -F @ims/web remove qr-scanner`（T2.1 綠後）
- 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `pnpm -F @ims/web test`／`pnpm -F @ims/web typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`

**Execution Order**
1. API：models＋migration 0019 → `barcode_service`（canonicalize／classify／providers／cache）→ routes＋schemas → items 整合（schema／service／搜尋／CSV）＋api-types
2. Web：掃描引擎置換（QR 回歸）→ lookup client／hook → `/scan` 流程＋候選＋外查卡＋i18n → 表單／詳情 → FAB
3. e2e `scan.spec.ts` → 標籤 stretch → 文件收尾（CHANGELOG／roadmap／勾選）

---

## Phase 1: API — barcode 欄位、provider 與快取

### Task 1.1: `items.barcode`＋`barcode_lookups` model＋migration `0019`

**Files:**
- Modify: `apps/api/app/models/item.py`（`barcode` 欄位）
- Create: `apps/api/app/models/barcode_lookup.py`
- Modify: `apps/api/app/models/__init__.py`（註冊）
- Create: `apps/api/alembic/versions/0019_item_barcode.py`
- Test: `apps/api/tests/test_barcode_models_smoke.py`

**TODO:**
- [x] `Item.barcode`：`String(32)` nullable、`Index("ix_items_owner_barcode", "owner_id", "barcode")`（**不設唯一**——同條碼多件）
- [x] `BarcodeLookup`：`id`(UUID pk)、`code`(String(64), nullable=False, **unique**)、`source`(String(32), nullable=False)、`payload`(`JSONType`, nullable=True＝負快取)、`fetched_at`(DateTime, nullable=False)
- [x] migration 0019：`revision="0019"`、`down_revision="0018"`；upgrade＝`items` 加欄＋index、建 `barcode_lookups`＋unique；downgrade 對稱
- [x] smoke：建含 barcode 的 item（同 owner 同 barcode 兩件允許）；`BarcodeLookup` code unique 違反；payload 存 dict 取回一致
- [x] 真實 PG 驗證：`docker compose cp`＋`alembic upgrade head`→`alembic current`＝0019

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_barcode_models_smoke.py`
- `cd apps/api && uv run alembic upgrade head`

### Task 1.2: `barcode_service`（canonicalize／classify／providers／cache）

**Files:**
- Create: `apps/api/app/services/barcode_service.py`
- Test: `apps/api/tests/test_barcode_service.py`

**TODO:**
- [x] 常數：`CACHE_TTL_DAYS = 30`、`EXTERNAL_TIMEOUT_SECONDS = 3.0`、`API_BASE` 兩 provider URL
- [x] `canonicalize(raw) -> str`（定案 1）；checksum：`_ean_checksum_ok`（EAN-8/13、UPC-A 12 位）、`_isbn10_checksum_ok`（mod 11，X=10）
- [x] `classify(code) -> "isbn" | "ean" | "other"`（定案 2）
- [x] `ExternalResult` dataclass（`source`／`name`／`description`／`image_url`）；`BarcodeProvider` protocol；`OpenFoodFactsProvider`／`OpenLibraryProvider`（定案 7）；`PROVIDERS` registry＋`provider_for(code)`
- [x] `async lookup_external(session, code) -> ExternalLookup`（dataclass：`external`／`status`／`cached`）：classify → 無 provider → `unsupported`；快取列存在且 `fetched_at >= now - 30d` → 回 `payload`（None → `not_found`）；否則 fetch → 命中/查無寫快取（savepoint 吸收 IntegrityError 改 UPDATE）→ `unavailable` 不寫
- [x] `async suggest_category_id(session, owner_id, categories_text) -> int | None`（定案 5：葉分類字面比對、唯一命中）
- [x] 測試：
  - canonicalize：去空白連字號底線；`978-0-306-40615-7`→13 位；ISBN-10 `X` 大寫；英數 SKU 原樣；空字串
  - classify：ISBN-10 有效/無效、978/979→isbn、EAN-13/8、UPC-A、checksum 壞→other
  - provider（monkeypatch httpx `AsyncClient` 或 transport mock）：OFF 命中映射（name/description/image）；`status:0`/404→None；非 JSON→`unavailable`；timeout→`unavailable`；OL 命中（作者串接）／空物件→None；OL ISBN-10
  - 快取：二度查詢 provider 呼叫數＝0（計數器）；`fetched_at` 31 天前→重抓覆寫；負快取（查無）二度查不打 provider；`unavailable` 不留列
  - `suggest_category_id`：唯一命中／多重命中 null／無命中 null／葉限定

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_barcode_service.py`

### Task 1.3: routes＋schemas — `GET /api/barcodes/{code}`

**Files:**
- Create: `apps/api/app/routes/barcodes.py`
- Create: `apps/api/app/schemas/barcode.py`
- Modify: `apps/api/app/main.py`（註冊 router）
- Modify: `apps/api/app/repositories/items_repository.py`（`list_by_barcode`）
- Test: `apps/api/tests/test_barcodes_routes.py`

**TODO:**
- [x] `items_repository.list_by_barcode(session, owner_id, code)`：owner 範圍、`is_deleted = false`、`barcode == code`（canonical）、依 name 排序；回傳附 `location_path` 建構所需欄位（join locations；`[floor, room, zone].filter(join " / ")`）
- [x] schemas：`BarcodeLocalMatch`（`id`/`name`/`quantity`/`image_id`/`location_path`）、`BarcodeExternal`（`source`/`name`/`description`/`image_url`/`suggested_category_id`）、`BarcodeLookupResponse`（定案 4 形狀）
- [x] route：canonicalize → 空／>64 字 422；`local_matches` 非空 → `skipped`；否則 `lookup_external`＋`suggest_category_id`（僅 `ok`）
- [x] 測試：匿名 401；單筆/多筆/零筆；`skipped` 語義（有 local 不呼叫 provider——以 monkeypatch 計數）；`unsupported`（checksum 壞的 13 位）；422（空／超長）；owner 隔離（他用戶條碼不現）；`location_path` 格式；`image_id` 透傳

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_barcodes_routes.py`

### Task 1.4: items 整合（create/update/read、q 搜尋、CSV）＋api-types

**Files:**
- Modify: `apps/api/app/schemas/item.py`（`ItemCreate`/`ItemUpdate`/`ItemRead`）
- Modify: `apps/api/app/services/items_service.py`（create／update 正規化）
- Modify: `apps/api/app/repositories/items_repository.py`（`q` 併 barcode）
- Modify: `apps/api/app/services/csv_service.py`（export／import）
- Test: `apps/api/tests/test_items_barcode.py`、既有 `tests/test_items_routes.py`／CSV 測試補案
- Regenerate: `packages/api-types/openapi.json`＋`gen:types`

**TODO:**
- [x] `ItemCreate.barcode`／`ItemUpdate.barcode`：`Optional[str] = Field(None, max_length=32)`；`ItemRead.barcode: Optional[str]`
- [x] `create_item`：`barcode=canonicalize(body.barcode) or None`；`update_item`：`"barcode" in model_fields_set` 才動，`None`＝清除，否則 canonicalize
- [x] repository `q`：`or_(name, description, Item.barcode.ilike(like))`
- [x] CSV：`EXPORT_COLUMNS` 於 `description` 後插 `barcode`（列建構取值或空）；`IMPORT_OPTIONAL += "barcode"`（匯入前 canonicalize）
- [x] 測試：建立帶 barcode（含連字號輸入→canonical 儲存）；更新改值／`null` 清除；未送欄位不變；q 以完整條碼命中；CSV 匯出欄位順序＋值、匯入回填、round-trip；api-types 重生成零 diff

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_items_barcode.py`
- `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`
- `pnpm --filter @ims/api-types gen:types`

---

## Phase 2: Web — 掃描引擎、`/scan` 流程、表單／詳情、FAB

### Task 2.1: 掃描引擎（native→ZXing fallback）＋ `qr-scanner-view` 換引擎零回歸

**Files:**
- Create: `apps/web/lib/scan/barcode-engine.ts`、`apps/web/lib/scan/barcode-engine.test.ts`
- Create: `apps/web/lib/scan/barcode.ts`、`apps/web/lib/scan/barcode.test.ts`（client canonicalize／`isBarcodeLike`）
- Modify: `apps/web/components/scan/qr-scanner-view.tsx`（引擎介面化）
- Modify: `apps/web/components/scan/qr-scanner-view.test.ts`
- Modify: `apps/web/package.json`（＋`@zxing/browser`；完成後 －`qr-scanner`）

**TODO:**
- [x] `barcode-engine.ts`：`createBarcodeEngine(video, onDecode, opts?) -> Promise<{ stop(): void }>`——`"BarcodeDetector" in globalThis` → `getSupportedFormats()` 過濾〔qr_code, ean_13, ean_8, upc_a, upc_e, code_128, code_39, itf〕＋輪詢 detect；否則 ZXing `BrowserMultiFormatReader`（hints 定案 10）`decodeFromVideoElement`；停止＝cancel＋`stop()` 釋放 tracks
- [x] `barcode.ts`：`canonicalizeBarcode`（同 API 規則）＋`isBarcodeLike`（`^\d{8,14}$`／ISBN-10）
- [x] `qr-scanner-view.tsx`：`QrScanner` 模組換 `createBarcodeEngine`；`extractItemIdFromPayload` 保留；decode 分流掛點先維持既有行為（②③ 於 T2.3 接上）
- [x] 測試：engine 選擇（mock `BarcodeDetector` 存在/不存在→native/zxing 分支）、`stop` 呼叫、`getSupportedFormats` 過濾；canonicalize 邊界；QR 回歸——deep link/UUID 導頁、無效 payload 顯示、手動輸入名稱搜尋、權限錯誤狀態（改 mock 引擎）
- [x] `pnpm -F @ims/web remove qr-scanner`（測試綠後）；typecheck

**Commands:**
- `pnpm -F @ims/web test -- src/lib/scan apps/web/components/scan`
- `pnpm -F @ims/web typecheck`

### Task 2.2: lookup client／hook

**Files:**
- Create: `apps/web/lib/api/barcodes.ts`、`apps/web/lib/api/barcodes.test.ts`
- Create: `apps/web/lib/hooks/use-barcode-lookup.ts`
- 依賴：`packages/api-types`（T1.4 產物：`BarcodeLookupResponse` 等型別）

**TODO:**
- [ ] `lookupBarcode(code, token)`：`GET /api/barcodes/{encodeURIComponent(code)}`；型別自 `@ims/api-types`
- [ ] `useBarcodeLookup(code: string | null)`：react-query、`enabled: !!code`、`retry: false`、`staleTime: 5min`（server 快取 30 天為權威）
- [ ] 測試：成功／401／網路錯誤；`enabled` 關閉不發請求

**Commands:**
- `pnpm -F @ims/web test -- src/lib/api/barcodes`

### Task 2.3: `/scan` 流程（分流、候選列表、外查三態）＋i18n

**Files:**
- Modify: `apps/web/components/scan/qr-scanner-view.tsx`（分流②③＋狀態 UI）
- Create: `apps/web/components/scan/barcode-candidates.tsx`（＋test）
- Create: `apps/web/components/scan/barcode-external-card.tsx`（＋test）
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`（`scan.*` 擴充）
- Test: `qr-scanner-view.test.ts` 擴充

**TODO:**
- [ ] 分流：decode／手輸 → `canonicalizeBarcode` 後 `isBarcodeLike` → `useBarcodeLookup`；1 筆 → `router.push(/items/{id})`；多筆／零筆 → 面板呈現
- [ ] `barcode-candidates.tsx`：標題「找到 {count} 件」；列＝縮圖（`imageUrl(image_id)`，無圖→佔位 icon）／名稱／`location_path`／數量；點擊 → 物品頁（鍵盤可達、`aria`）
- [ ] `barcode-external-card.tsx`：`ok` → 來源徽章（Open Food Facts／Open Library）＋name／description＋封面縮圖＋「帶入新增」→ `/items/new?barcode=…`；`not_found` → 「查無公開資料，已帶入條碼，請補名稱」＋「以條碼新增」；`unavailable` → 「網路不穩，條碼已保留」＋「重試」（重打 query）＋「仍要新增」；`unsupported` → 直接「以條碼新增」；查詢中 → 「查詢外部資料庫…」＋spinner
- [ ] 權限被拒：全頁空態區塊＋「開啟權限」（重新 `start()`）＋手動輸入保底（不遮擋）
- [ ] i18n zh-TW／en 同步；既有 QR 文案不動
- [ ] 測試：單筆 push；多筆候選渲染（縮圖/路徑/數量/退化無圖）；三態卡文案與按鈕；重試觸發 refetch；非條碼 → 名稱搜尋回歸

**Commands:**
- `pnpm -F @ims/web test -- src/components/scan`

### Task 2.4: 表單 barcode 欄位＋`?barcode=` prefill；詳情列＋複製

**Files:**
- Modify: `apps/web/components/items/item-form.tsx`（欄位＋查詢按鈕＋hydrate；＋test）
- Modify: `apps/web/app/(app)/items/new/page.tsx`（`searchParams.barcode` 透傳；＋test）
- Modify: `apps/web/app/(app)/items/[id]/edit/page.tsx`（欄位自動生效，必要時微調 defaultValues）
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`（barcode `dl` 列＋複製）
- Modify: i18n 兩檔（`items.form.barcode*`、`items.detail.barcode*`）
- Test: `page.test.tsx`／詳情測試擴充

**TODO:**
- [ ] `itemFormSchema += barcode: z.string().max(32).optional()`；欄位（Input＋「查詢」小按鈕 aria-label）置於 description 附近；送出不變（payload 帶 barcode）
- [ ] `?barcode=` 帶入：new 頁讀 `searchParams`；form 以 `useBarcodeLookup` hydrate——只填空欄（name／description／category 依定案 8）＋來源標註（徽章，hover/文字「來源：…」）；`local_matches>0` → 「已有 {count} 件同條碼物品」＋連結（不做外部 prefill）；查詢中狀態文案
- [ ] 手動「查詢」按鈕：canonicalize 欄位值 → lookup → 同 hydrate 語義（只填空欄；自身欄位寫回 canonical）
- [ ] 詳情：`item.barcode` 存在時 `<dt>`「條碼」／`<dd>` monospace＋複製按鈕（`navigator.clipboard`＋toast「已複製」）；e2e 友善（按鈕 `aria-label`）
- [ ] 測試：prefill 只填空欄（name 已填→不覆蓋）；local 命中→提示不 prefill；來源標註渲染；分類建議唯一命中才帶入；查詢按鈕路徑；詳情列顯隱＋複製 mock

**Commands:**
- `pnpm -F @ims/web test -- src/components/items src/app/.../items`
- `pnpm -F @ims/web typecheck`

### Task 2.5: 行動掃描 FAB

**Files:**
- Create: `apps/web/components/shell/scan-fab.tsx`（＋test）
- Modify: `apps/web/components/shell/app-shell.tsx`

**TODO:**
- [ ] `Link href="/scan"`：`md:hidden`、`fixed right-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-40` 圓形 ≥44px、`aria-label={t("scan.fabAria")}`、icon（ScanLine）
- [ ] i18n `scan.fabAria`（zh-TW「掃描」／en "Scan"）；掛載 `app-shell`（`main` 之外、登入區內）
- [ ] 測試：渲染含 aria-label 與 `md:hidden`；href `/scan`

**Commands:**
- `pnpm -F @ims/web test -- src/components/shell`

---

## Phase 3: e2e、標籤 stretch、收尾

### Task 3.1: e2e `scan.spec.ts`（內查＋表單＋FAB；不依賴外部網路）

**Files:**
- Create: `apps/web/tests/scan.spec.ts`

**TODO:**
- [ ] 前置：register（既有 helper 模式）；API 建 2 件同 barcode（"4710085200014"）＋1 件另一 barcode（"4710085200021"）＋1 件無 barcode
- [ ] ① 內查單筆：`/scan` 手輸 → 送出 → URL `/items/{id}`
- [ ] ② 內查多筆：手輸共用 barcode → 候選列表（兩名稱＋總數）→ 點列 → 物品頁
- [ ] ③ 非條碼輸入回歸：手輸名稱 → `/items?q=…`
- [ ] ④ 表單 prefill（local 命中）：`/items/new?barcode=…` → barcode 欄已帶入＋「已有 1 件同條碼物品」提示
- [ ] ⑤ 建立→詳情：表單手輸 barcode 建檔 → 詳情顯示條碼；列表 `q=barcode` 命中
- [ ] ⑥ FAB：`test.use({ viewport: { width: 390, height: 844 } })` → 可見、點擊到 `/scan`；桌面 viewport → 隱藏
- [ ] 註記：外部三態不在 e2e（網路非決定性）——provider mock 於 T1.2／hook mock 於 T2.3 覆蓋

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && pnpm exec playwright test tests/scan.spec.ts`

### Task 3.2: 標籤 stretch（QR 下方加印條碼數字）＋文件收尾

**Files:**
- Modify: `apps/web/app/(app)/items/[id]/label/page.tsx`（＋test 擴充）
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.25]`）、`docs/v2-roadmap.md`（Phase 列＋測試規模）、本計畫（勾選＋Final Verification）

**TODO:**
- [ ] 標籤頁：`item.barcode` 存在時 QR 下方 monospace 數字文字（列印樣式）；無 barcode 不變（零回歸）
- [ ] CHANGELOG alpha.25（比照 alpha.24 格式）：barcode 欄位／lookup API／快取／`/scan` 擴充／FAB／CSV
- [ ] v2-roadmap：Phase 25 狀態＋測試規模更新
- [ ] 本計畫：全任務勾選＋Final Verification 段（實測數字＋環境註記：`ENABLE_DEV_ROUTES=1`、e2e 不依賴外部網路、admin 階梯沿用）

**Commands:**
- `pnpm -F @ims/web test -- label`
- `pnpm exec playwright test`

---

## API 契約（實作權威）

**`GET /api/barcodes/{code}`**（Bearer；任何登入者）
- 200：定案 4 形狀；`external_status ∈ {ok, not_found, unavailable, unsupported, skipped}`
- 422：canonical 後空／>64 字；401 匿名

**`POST/PATCH /api/items`**：`barcode` 可選（≤32 字、canonicalize 儲存、`null` 清除）
**`GET /api/items?q=`**：`name`/`description`/`barcode`（ilike contains）
**CSV**：`barcode` 匯出（description 後）／匯入可選欄

### §5.4 狀態表（本 phase 介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| 掃碼（25，擴充） | 相機啟動中；外查中「查詢外部資料庫…」（≤3 秒） | 權限被拒 → 全頁空態＋「開啟權限」＋手動輸入保底；外查查無 → 「查無公開資料，已帶入條碼，請補名稱」 | 逾時/網路錯誤 → 「網路不穩，條碼已保留」＋重試（與查無區分；另提供「仍要新增」） | 內查命中：單筆 → 直接跳轉；多筆 → 候選列表（縮圖＋名稱＋位置路徑＋數量＋總數） | 外查 `unsupported`（checksum 無效等）→ 僅「以條碼新增」 |
| 物品表單條碼欄（25） | `?barcode=` 帶入查詢中（「查詢中…」） | 手輸空白＋「查詢」按鈕 | 外查失敗 → 不阻塞儲存（無標註即可） | 外查 ok → 名稱/描述/分類建議回填（只填空欄）＋來源標註 | 「已有 N 件同條碼物品」提示（local 命中，不 prefill） |

### 驗收對照（roadmap §六 Phase 25）

| 驗收項 | Task |
|---|---|
| provider mock（命中／逾時／非 JSON／404） | T1.2 |
| 快取命中與 TTL 過期 | T1.2 |
| 掃描頁 QR 與 1D 並存回歸 | T2.1（單元）＋T3.1 |
| 內查單筆跳轉／多筆候選 | T1.3＋T2.3＋T3.1 |
| 外查三態＋表單 prefill（含掃碼手輸 prefill 補充規格） | T1.3＋T2.3＋T2.4 |
| barcode 欄位（表單／詳情＋複製） | T1.4＋T2.4 |
| CSV import/export | T1.4 |
| FAB（§5.7；桌面入口保留） | T2.5＋T3.1 |
| 標籤加印條碼（stretch） | T3.2 |

---

## Final Verification（收尾時填實測）

- [ ] API：`cd apps/api && uv run --extra test pytest -q` 全綠
- [ ] Web：`pnpm -F @ims/web test` 全綠＋`pnpm -F @ims/web typecheck` 0 error
- [ ] api-types 重生成零 diff
- [ ] e2e：`pnpm exec playwright test` 全綠（環境註記：`ENABLE_DEV_ROUTES=1`；外部三態不在 e2e）
- [ ] 視覺走查：/scan 三態＋候選、表單 prefill 標註、FAB（390 寬＋深色）
- [ ] 環境註記回填（比照 Phase 24）

> 環境註記（實作時補）：e2e 用 `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web`；`items-crud`／`collaboration` 平行偶發 flaky 屬既有現象；外部 provider 依賴真實網路（僅 API 測試以 mock 覆蓋決定性）。
