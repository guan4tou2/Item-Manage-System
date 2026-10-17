# Phase 27 — 成本與庫存估值 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 27（L444–460）＋ §5.1 儀表板資訊階層（估值卡不得插在行動卡之前）、§5.2 設定 IA（幣別置於「個人 ＞ 偏好」）、§5.4 狀態契約、§5.6 金額格式（本 phase 建立）。
> 本 phase 為**純加欄**（`items.cost`）＋讀取端聚合，migration `0021` 可逆、無破壞性；不需 Phase 26 式的強制備份。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**；完成即 commit（Conventional Commits，繁中 body）。

**Goal：** 物品可記單價（`items.cost Numeric(12,2)` nullable）；幣別為**帳號層級單一設定**（`users.preferences.currency`，預設 TWD，不做匯率換算）；`GET /api/stats/value` 提供庫存總值、依分類／位置／倉庫分布與**未填成本比例**（null 成本以 0 計）；Web：物品表單成本欄位＋詳情顯示、統計頁「庫存估值」區塊（摘要卡＋兩張價值圖）、設定頁「個人 ＞ 偏好」幣別、儀表板估值卡（**排在行動卡群組之後**，§5.1）；CSV `cost`／`currency` 欄位；備份 `format_version` 2 → 3；金額顯示統一（§5.6：`Intl.NumberFormat`，TWD 於 zh-TW／en 皆 `NT$` 前綴）。

**Architecture：** 單價存 `items.cost`（Decimal、2 位、≥0、nullable；null＝未填）。估值**讀取時聚合**（`func.sum(cost × quantity)`；不建快取表、不建 view）：`stats_repository.value_totals`（總值＋priced／unpriced 計數）與 `value_by_category`／`value_by_location`／`value_by_warehouse`（`outerjoin`＋`group by`，比照既有 `by_*`）；service 補 location label（樹路徑 `paths_for`）、讀帳號幣別、金額 `quantize(0.01)`。序列化決策：**金額一律 JSON 字串**（Pydantic `Decimal` → `"12.30"`；既有 `lists.price`／`budget` 前例），Web 端存字串、顯示才 `formatCurrency()` 轉 number。備份 JSON 同步（`_serialize` 補 `Decimal → str`——同時修既有 `lists.budget`／`price` 有值時 `JSONResponse` `json.dumps(Decimal)` 崩潰的潛在 bug）。

**Tech Stack：** FastAPI、SQLAlchemy async、Alembic（migration `0021`，add／drop column 可逆）、pytest（SQLite in-memory；Numeric 經 SQLite REAL → 斷言以 2 位字串／Decimal 正規化）、React Query、next-intl、recharts（**沿用既有圖表語彙**：Pie 比照分類圖、橫向 Bar 比照標籤圖）、shadcn/ui、Vitest、Playwright。**不新增依賴**。

**關鍵既有資產（重用，勿重造）：**
- 金額前例：`app/models/list.py`（`budget`／`price` = `Numeric(12,2)`）、`schemas/list.py`（`Decimal`→JSON 字串）、`apps/web/components/lists/list-entry-row.tsx`（字串顯示）——`items.cost` 完全比照
- 偏好機制：`users.preferences`（JSONB）、`preferences_repository.get_raw_preferences`／`preferences_service`（`exclude_none` merge）、`PreferencesForm`
- 統計：`stats_repository.by_location`（outerjoin＋group by＋service 以 `paths_for` 補 label）、`schemas/stats.py`（Bucket 風格）、`routes/stats.py`、`lib/api/stats.ts`、`lib/hooks/use-stats.ts`
- CSV：`csv_service.EXPORT_COLUMNS`／`IMPORT_OPTIONAL`／`RowError`（列級錯誤列舉）、`csv-panel.tsx`（欄位文案）
- 備份：`backup_service._serialize`／`_row_to_dict`／items include 清單；`format_version` 現為 2；`JSONResponse` 直出（**json.dumps——Decimal 必須先轉字串**）
- 圖表：`components/stats/*`（`category-chart` Pie＋`PALETTE`／`tag-chart` 橫向 Bar／`EmptyChart`）
- 儀表板：`app/(app)/dashboard/page.tsx` 行動卡 grid（Expiry／LowStock／ActiveLoans，`md:grid-cols-2`）、`StatCard`／`ExpiryCard` 卡面前例
- 物品：`components/items/item-form.tsx`（zod＋`Input` 欄位）、`app/(app)/items/[id]/page.tsx` `dl` 屬性區（`location.path` 截斷前例）、`ItemRead.location`
- 快照：`items_service.update_item` 的 `pre_snapshot`（`ItemVersion.snapshot` JSON——**Decimal 需先 `str()`**）
- i18n：`messages/zh-TW.json`／`en.json`（逐鍵插入、不重排整檔）

**盤點定案（2026-10-17，實作前一覽）：**
1. **Schema**：`items.cost Numeric(12,2) nullable`＋`CheckConstraint("cost IS NULL OR cost >= 0", name="ck_items_cost_nonneg")`；migration `0021`（`down_revision="0020"`）：add column＋check constraint；downgrade drop（可逆）。
2. **精度與序列化**：Decimal 端到端；API JSON 一律**字串**（`"12.30"`／null——Pydantic v2 Decimal 行為，以既有 `lists.price` 前例＋測試鎖定）；Web 存入 state 為字串，顯示端才轉 number；輸入端表單以正規 `/^\d{1,10}(\.\d{1,2})?$/`（空＝未填）把關，伺服器仍以 `ge=0, max_digits=12, decimal_places=2` 為權威。
3. **幣別**：`users.preferences.currency`，白名單 `TWD|USD|EUR|JPY|CNY|HKD`（預設 `TWD`）；帳號層級單一；**不做匯率換算**；`PreferencesUpdate` 僅新增 optional 欄位（既有 merge 邏輯不動）。
4. **`GET /api/stats/value` 回傳**：`{currency, total_value, priced_items, unpriced_items, total_items, by_category[], by_location[], by_warehouse[]}`；`value`＝`Σ(cost × quantity)`（cost null 以 0 計）；bucket 含 `count`（桶內物品數，未填成本也計入）＋`value`；`location.label`＝樹路徑（`paths_for`，無位置→null）；`is_deleted=true` 排除；金額 `quantize(Decimal("0.01"), ROUND_HALF_UP)`。
5. **未填成本語義**：以 0 計入總值／分布；`unpriced_items` 另計，UI 顯示「未填 N / M（x%）」——明示「未填以 0 計」，不靜默。
6. **CSV**：export 於 `min_quantity` 後插 `cost`、`currency`（currency＝帳號幣別；cost 空＝""）；import 接受 `cost`（空→null；`Decimal` 失敗／負數／>2 位小數→列錯誤 `invalid_cost`）與 `currency`（空或＝帳號幣別→通過；不符→列錯誤 `currency_mismatch`，避免幣別誤植）；舊檔（無此兩欄）相容。
7. **備份**：`format_version` 2 → **3**；items 加 `cost`（字串／null）；`_serialize` 補 `Decimal → str`（同時修既有 lists `budget`／`price` 匯出潛在 500）；備份不含 `users.preferences`（currency 不進備份；Phase 29 再議還原範圍）。
8. **版次快照**：`update_item` 的 `pre_snapshot` 加 `cost`（快照 JSON 內以字串存；無還原邏輯，僅歷史上可見）。
9. **金額格式工具**：新增 `apps/web/lib/format/currency.ts`——`formatCurrency(value, currency, locale)`：`Intl.NumberFormat(locale, {style:"currency", currency, minimumFractionDigits: digits, maximumFractionDigits: digits})`＋`formatToParts` 將 `currency` part 以固定符號表置換（`TWD→NT$`、`USD→US$`、`EUR→€`、`JPY→¥`、`CNY→CN¥`、`HKD→HK$`），確保 **TWD 於 zh-TW／en 均 `NT$` 前綴**（§5.6）；`digits`＝JPY 一律 0、整數金額 0、有小數 2（`NT$1,200`／`NT$99.50`）；null／空／非數 → `"—"`。
10. **物品表單**：成本欄位＝text＋`inputMode="decimal"`（不做千分位輸入）；helper 顯示當前幣別（唯讀註記「以 NT$ 計價，幣別可於設定更改」）；送出：`trim()==="" → null`（create 不設／update **清空**——`exclude_unset` 保留顯式 null）；編輯模式 `defaultValue = item.cost ?? ""`。
11. **物品詳情**：`dl` 屬性區新增「成本」列（`formatCurrency`；null → `—`；`data-testid="item-cost"`）；幣別取自 `usePreferences()`（載入中 skeleton）。
12. **統計頁**：新增「庫存估值」區塊**置頂**（統計頁無行動卡約束；既有 5 張圖表**不動**、不重排）：`h2` 分節標題＋`ValueSummaryCard`（總值＋幣別＋未填比例）＋grid（`ValueCategoryChart` Pie／`ValueLocationChart` 橫向 Bar；只畫 `value > 0` 桶；空資料→`EmptyChart` 引導補成本；長路徑截斷＋Tooltip 全路徑）。
13. **儀表板**：`ValueCard`（金額＋「未填成本 N/M」註記＋deep link「查看統計 →」）作為行動卡 grid 的**最後一張**（DOM 序在到期／低庫存／在借之後，滿足 §5.1；md 兩欄自然落在第 2 列右格）；全無成本→`NT$0`＋「為物品補上成本」連結（`/items`）。
14. **偏好更新連動**：`useUpdatePreferences.onSuccess` 追加 `invalidateQueries(["stats"])`（value 的 `currency` 隨偏好變）。
15. **不做（範圍外）**：物品列表不加成本欄／不加成本篩選；批次成本（per-batch）為 stretch 後議；lists 的 `$` 硬編碼不動（另案）；AI 收據帶入成本屬 Phase 33（依賴本 phase 欄位＋格式工具）；`OverviewStats` 不加欄位（儀表板卡直接共用 `useStatsValue`）。

**執行前置：**
1. worktree：`git worktree add .claude/worktrees/phase27-cost-valuation -b claude/phase27-cost-valuation`；alembic head＝`0020`
2. 起堆疊：`ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx`（api 啟動即 `alembic upgrade head`＝0021）；`docker compose exec api alembic current` 驗證
3. 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `pnpm -F @ims/web test`／`pnpm -F @ims/web typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`；e2e `pnpm exec playwright test`
4. 註：dev／e2e 長期沿用庫既有物品 `cost` 皆為 null（未填）——估值 e2e 以**新註冊用戶**自建資料，不依賴既有資料；無需備份（純加欄）

**Execution Order**
1. API：`items.cost`（model＋migration 0021＋smoke）→ items schemas／service（create／update／`_to_read`／snapshot）
2. API：preferences currency → `GET /api/stats/value`（repo／service／route／schemas）→ CSV（cost／currency）→ backup v3（＋`_serialize` 修正）→ api-types 重生成
3. Web：`formatCurrency` 工具 → 幣別設定 → 物品表單／詳情 → stats value api／hooks → 統計頁估值區塊 → 儀表板估值卡 → i18n＋CSV 面板文案
4. e2e → 文件收尾（CHANGELOG／roadmap／勾選＋Final Verification）

---

## Phase 1: API — 成本欄位、幣別偏好與估值端點

### Task 1.1: `items.cost` model＋migration `0021`＋smoke

**Files:**
- Modify: `apps/api/app/models/item.py`
- Create: `apps/api/alembic/versions/0021_item_cost.py`
- Test: `apps/api/tests/test_item_cost_smoke.py`

**TODO:**
- [x] `Item.cost`：`Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)`；`__table_args__` 加 `CheckConstraint("cost IS NULL OR cost >= 0", name="ck_items_cost_nonneg")`（比照 `ck_items_quantity_nonneg`）；import `Decimal`／`Numeric`
- [x] migration `0021`（`down_revision="0020"`）：`op.add_column("items", sa.Column("cost", sa.Numeric(12, 2), nullable=True))`＋check constraint（SQLite 走 `batch_alter_table`，比照 0020 檔案風格）；downgrade：drop constraint＋drop column（可逆）
- [x] smoke：`cost=None` 可建；`Decimal("12.34")` 建→讀回；負值 → CheckConstraint 違反（SQLite／PG 皆擋，PG 於收尾 API 實測）；nullable 不影響既有欄位
- 精度把關在 schema 層（SQLite 的 `Numeric` 不做 scale 強制，勿在 model 層測截斷）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_item_cost_smoke.py`

### Task 1.2: items schemas／service 帶 cost

**Files:**
- Modify: `apps/api/app/schemas/item.py`
- Modify: `apps/api/app/services/items_service.py`
- Test: `apps/api/tests/test_items_service.py`、`apps/api/tests/test_items_routes.py`、`apps/api/tests/test_item_history.py`

**TODO:**
- [x] `ItemCreate.cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)`；`ItemUpdate.cost` 同（顯式 `null`＝清空，`model_dump(exclude_unset=True)` 已保留）；`ItemRead.cost: Optional[Decimal]`
- [x] `create_item`：`cost=body.cost`；`update_item`：隨 `fields` 迴圈 `setattr`（無需特例）；`_to_read`：`"cost": item.cost`
- [x] `pre_snapshot` 加 `"cost": str(item.cost) if item.cost is not None else None`（`ItemVersion.snapshot` 為 JSON——Decimal 不可直入）
- [x] 測試：create `"12.30"` → response JSON 字串 `"12.30"`；未帶／null → `null`；`-1` → 422；`"1.234"` → 422；11 位整數 → 422（max_digits 12 含 2 位小數＝整數上限 10 位）；update 設值；update `cost: null` 清空；PATCH 未帶 cost → 不變更；snapshot 含 cost 字串；`extra="forbid"` 不受影響（回歸）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_items_service.py tests/test_items_routes.py tests/test_item_history.py`

### Task 1.3: preferences `currency`

**Files:**
- Modify: `apps/api/app/schemas/preferences.py`
- Test: `apps/api/tests/test_preferences_schemas.py`、`apps/api/tests/test_preferences_routes.py`、`apps/api/tests/test_preferences_service.py`

**TODO:**
- [x] `Currency = Literal["TWD", "USD", "EUR", "JPY", "CNY", "HKD"]`；`PreferencesRead.currency: Currency = "TWD"`；`PreferencesUpdate.currency: Currency | None = None`（service 既有 `exclude_none=True` merge 不動）
- [x] 測試：未設定過 → 讀回 `"TWD"`（含舊帳號 preferences 無此鍵）；PUT `{"currency":"JPY"}` → 200＋持久；非法 `"BTC"` → 422；與 `theme` 並存 merge 不互蓋（回歸）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_preferences_schemas.py tests/test_preferences_routes.py tests/test_preferences_service.py`

### Task 1.4: `GET /api/stats/value`

**Files:**
- Modify: `apps/api/app/schemas/stats.py`
- Modify: `apps/api/app/repositories/stats_repository.py`
- Modify: `apps/api/app/services/stats_service.py`
- Modify: `apps/api/app/routes/stats.py`
- Test: `apps/api/tests/test_stats_value.py`（新；repository→service→route 一檔貫穿，比照 `test_stats_v2.py` 風格）

**TODO:**
- [x] schemas：`ValueStats{currency, total_value: Decimal, priced_items: int, unpriced_items: int, total_items: int, by_category: list[CategoryValueBucket], by_location: list[LocationValueBucket], by_warehouse: list[WarehouseValueBucket]}`；bucket＝`{category_id|location_id|warehouse_id, name|label, value: Decimal, count: int}`
- [x] repository：`value_totals`（`func.sum(Item.cost * Item.quantity)`＋`func.sum(case((Item.cost.is_(None), 1), else_=0))`＋`func.count(Item.id)`；`is_deleted=False`）；`value_by_category`／`value_by_location`／`value_by_warehouse`（`outerjoin`＋`group_by`＋`order_by(func.sum(...).desc())`；`func.coalesce(..., 0)`；含 None 桶＝「未分類／未分配／無倉庫」）
- [x] service：`get_value`——currency 以 `preferences_repository.get_raw_preferences` 取（未知值／缺鍵 → `"TWD"`，`currency_from_raw` 正規化）；location labels 以 `locations_repository.fetch_all`＋`paths_for`（比照 `get_by_location`）；所有金額 `Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP)`（SQLite REAL→Decimal 正規化）
- [x] route：`GET /api/stats/value`（response_model=ValueStats）
- [x] 測試：空庫（`"0.00"`、比例 0/0）；混合（cost 10 × qty 3＋null × qty 1 → total `30.00`、priced 1／unpriced 1／total 2）；分組含 None 桶；quantity 加權；JPY 偏好 → `currency:"JPY"`；軟刪物品排除；跨 owner 隔離；anonymous 401（10 例）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_stats_value.py`

### Task 1.5: CSV `cost`／`currency`

**Files:**
- Modify: `apps/api/app/services/csv_service.py`
- Test: `apps/api/tests/test_csv_cost.py`（新）

**TODO:**
- [x] `EXPORT_COLUMNS`：`min_quantity` 後插 `cost`、`currency`；export：cost＝`str(item.cost)`（DB scale 2 → `"12.30"`）或 `""`；currency＝帳號幣別（讀偏好，fallback TWD）
- [x] `IMPORT_OPTIONAL` 加 `cost`、`currency`；import：cost（strip；空→None；`Decimal` 失敗／<0／>2 位小數／>10 位整數 → `RowError(row, "invalid_cost")`——實作以單一訊息 `cost must be a number >= 0 with at most 2 decimals`）；currency（strip＋upper；空→通過；≠帳號幣別 → `RowError(row, "currency_mismatch")`）；錯誤以既有列舉機制回報
- [x] `csv_service` 新增對 `preferences_repository`／`currency_from_raw` 的依賴（export／import 兩處）
- [x] 測試：export header 順序；有／無 cost 值；import 建帶成本物品；`"1.234"`／`"-1"`／`"abc"` → 錯誤；`"USD"`（帳號 TWD）→ mismatch；`"TWD"`／空 → 通過；無此兩欄舊檔相容；round-trip（export→import 新 owner，成本一致）（7 例）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_csv_cost.py`

### Task 1.6: backup v3＋`_serialize` Decimal 修正

**Files:**
- Modify: `apps/api/app/services/backup_service.py`
- Test: `apps/api/tests/test_backup.py`

**TODO:**
- [x] `_serialize`：`if isinstance(value, Decimal): return str(value)`——**RED 先行**：先加「清單含 `price`／`budget` 的 export」測試（現況 `JSONResponse` `json.dumps(Decimal)` → 500（實測 TypeError），修後 200＋字串值）
- [x] items include 加 `"cost"`；`format_version` 2 → 3
- [x] 測試：`format_version == 3`；items `cost`=`\"12.30\"`／null；帶價清單 export 200＋值為字串；既有 backup 測試回歸（7 例）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_backup.py`

### Task 1.7: api-types 重生成

**Files:**
- Regenerate: `packages/api-types/openapi.json`、`packages/api-types/src/*`

**TODO:**
- [x] `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`＋ `pnpm --filter @ims/api-types gen:types`
- [x] diff 確認：`ItemRead.cost: string | null`（請求端 `number | string | null`）、`PreferencesRead.currency`／`PreferencesUpdate.currency`、`ValueStats`／三個 Bucket
- 註：Web 需要 cost 型別（T2.3）；若 Phase 1 未完成的 Task 阻塞 Web，可提前重生成（以最終一次零 diff 為準）

**Commands:**
- `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`

---

## Phase 2: Web — 金額格式、幣別設定、表單／詳情、統計與儀表板

### Task 2.1: `formatCurrency` 金額格式工具

**Files:**
- Create: `apps/web/lib/format/currency.ts`
- Test: `apps/web/lib/format/currency.test.ts`

**TODO:**
- [x] `CURRENCIES = ["TWD","USD","EUR","JPY","CNY","HKD"] as const`；`type Currency`；`CURRENCY_SYMBOLS`（NT$／US$／€／¥／CN¥／HK$）
- [x] `formatCurrency(value: string | number | null | undefined, currency: string, locale: string): string`：null／""／undefined／`Number()` 非有限 → `"—"`；`digits`＝JPY 0、整數 0、有小數 2；`Intl.NumberFormat(locale, {style:"currency", currency, minimumFractionDigits: digits, maximumFractionDigits: digits})`＋`formatToParts` 置換 `currency` part（未知幣別 → Intl 原樣；實測 `XYZ` 不拋錯、以 `\u00a0` 分隔）
- [x] 測試（9 例）：`"1200"`／TWD／zh-TW＝`NT$1,200`；en 同；`"99.50"` → `NT$99.50`；整數去小數（`"10.00"`→`NT$10`）；JPY `"1200"`→`¥1,200`、`"1200.4"`→`¥1,200`；USD／EUR／CNY／HKD；null／undefined／""／`"abc"`／NaN → `—`；未知幣別相容；白名單與符號表

**Commands:**
- `pnpm -F @ims/web test -- lib/format`

### Task 2.2: 幣別設定（個人 ＞ 偏好）＋偏好連動 stats

**Files:**
- Modify: `apps/web/components/settings/preferences-form.tsx`
- Modify: `apps/web/lib/preferences/use-preferences.ts`
- Test: `apps/web/components/settings/preferences-form.test.tsx`

**TODO:**
- [x] 幣別 `Select`（label `settings.preferences.currency`；選項 `currency.TWD`…；值＝API `currency`；變更→`mutateAsync({currency})`＋既有 toast）；下方 muted 即時預覽 `formatCurrency(1200, currency, locale)`（`useLocale()`；`data-testid="currency-preview"`）＋`currencyHint`
- [x] `useUpdatePreferences.onSuccess`：保留 `setQueryData`，追加 `qc.invalidateQueries({ queryKey: ["stats"] })`
- [x] 測試：渲染目前值（預設 TWD）；變更 → mutation body 帶 `currency`；預覽 `NT$1,200`；hook 測試（invalidate stats＋cache 更新）；settings 全套回歸（13 檔／49 例）

**Commands:**
- `pnpm -F @ims/web test -- components/settings`

### Task 2.3: 物品表單成本欄位＋詳情顯示

**Files:**
- Modify: `apps/web/components/items/item-form.tsx`
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`
- Test: `apps/web/components/items/item-form.test.tsx`（補案）

**TODO:**
- [ ] zod 加 `cost: z.string().trim().regex(/^(?:\d{1,10}(?:\.\d{1,2})?)?$/, "costInvalid").optional()`（空字串＝未填，通過）
- [ ] 欄位：`<Input id="cost" inputMode="decimal" placeholder="0.00" {...register("cost")} />`＋Label `items.form.cost`＋helper `items.form.costHint`（含當前幣別符號，例：「以 NT$ 計價；幣別可於設定更改」）；編輯模式 `defaultValue = item?.cost ?? ""`
- [ ] payload：送出時 `cost: raw.trim() === "" ? null : raw.trim()`（create／update 一致；update 空＝清空）
- [ ] 詳情：`dl` 屬性區加「成本」列（Label 沿用 `items.form.cost`）＝`formatCurrency(item.cost, currency, locale)`；null → `—`；`data-testid="item-cost"`；`usePreferences()` 載入中 → `<Skeleton>`（不閃爍）
- [ ] 測試：輸入 `1200.50` → 送出 `cost:"1200.50"`；空 → `null`；`1.234`／`-1`／`abc` → 行內錯誤且不送出（RED→GREEN）；編輯模式預填；helper 文案含 `NT$`（預設偏好）

**Commands:**
- `pnpm -F @ims/web test -- components/items`

### Task 2.4: stats value api／hooks

**Files:**
- Modify: `apps/web/lib/api/stats.ts`、`apps/web/lib/hooks/use-stats.ts`
- Test: `apps/web/lib/hooks/use-stats.test.tsx`（若無既有檔則隨 T2.5 元件測試覆蓋）

**TODO:**
- [ ] `export type ValueStats = paths["/api/stats/value"]["get"]["responses"]["200"]["content"]["application/json"]`；bucket 元素型別另 export
- [ ] `getValue(accessToken)`；`useStatsValue()`（queryKey `["stats","value"]`，staleTime 同 `STALE_TIME`）

**Commands:**
- `pnpm -F @ims/web test -- lib/api lib/hooks`

### Task 2.5: 統計頁「庫存估值」區塊

**Files:**
- Create: `apps/web/components/stats/value-summary-card.tsx`（＋test）
- Create: `apps/web/components/stats/value-category-chart.tsx`（＋test）
- Create: `apps/web/components/stats/value-location-chart.tsx`（＋test）
- Modify: `apps/web/app/(app)/statistics/page.tsx`
- Modify: i18n 兩檔（見 T2.7）

**TODO:**
- [ ] `ValueSummaryCard`：標題 `stats.value.title`；大字 `formatCurrency(total_value, currency, locale)`（`data-testid="value-summary"`）；副行「已填成本 {priced}/{total}・未填 {unpriced}（{pct}%）」＋說明「未填成本以 0 計」（i18n）；loading skeleton；error → 卡內 compact 錯誤＋重試
- [ ] `ValueCategoryChart`：比照 `category-chart`（Pie＋`PALETTE`）；資料＝`by_category` 過濾 `value > 0` 轉 Number；`count` 入 Tooltip；不足 1 桶 → `EmptyChart`；CardTitle `stats.value.byCategory`
- [ ] `ValueLocationChart`：橫向 Bar（比照 `tag-chart`）；label＝`label ?? stats.value.noLocation`；>24 字元截斷 `…`＋Tooltip 全路徑；`value > 0` 過濾；CardTitle `stats.value.byLocation`
- [ ] 統計頁：置頂新增 `h2`（`stats.value.sectionTitle`）＋`ValueSummaryCard`＋`md:grid-cols-2` 兩圖；**既有 5 圖表順序與內容不動**；各卡片自帶 loading／error
- [ ] 測試：summary 金額（`NT$1,200`）與比例文案；總值 0 → 引導文案；Pie 0 值桶排除；location 截斷＋`title`；EmptyChart 空態；loading skeleton

**Commands:**
- `pnpm -F @ims/web test -- components/stats`

### Task 2.6: 儀表板估值卡（行動卡之後）

**Files:**
- Create: `apps/web/components/dashboard/value-card.tsx`（＋test）
- Modify: `apps/web/app/(app)/dashboard/page.tsx`
- Modify: i18n 兩檔（見 T2.7）

**TODO:**
- [ ] `ValueCard`（比照 ExpiryCard 卡面）：CardTitle `dashboard.value.title`；金額大字（`formatCurrency`）；註記「未填成本 {unpriced}/{total}」；footer link「查看統計 →」（`/statistics`，`data-testid="value-card-link"`）；loading skeleton；錯誤態 compact；全無成本（`priced_items === 0`）→ `NT$0`＋註記改引導文案＋連結 `/items`
- [ ] 版面：掛在行動卡 grid（Expiry／LowStock／ActiveLoans）**最後一張**（DOM 序第 4；md 兩欄＝第 2 列右格）——§5.1「估值卡不得插在行動卡之前」
- [ ] 測試：渲染金額與註記；連結 href；loading skeleton；無成本文案；**DOM 序**（ValueCard 在 ActiveLoansCard 之後）

**Commands:**
- `pnpm -F @ims/web test -- components/dashboard`

### Task 2.7: i18n＋CSV 面板文案

**Files:**
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`
- Modify: `apps/web/components/settings/csv-panel.tsx`（欄位清單加 `cost`／`currency`＋說明）

**TODO:**
- [ ] keys（逐鍵插入、不重排整檔）：`items.form.cost`／`costHint`／`validation.costInvalid`；`settings.preferences.currency`；`currency.TWD|USD|EUR|JPY|CNY|HKD`；`stats.value.*`（title／sectionTitle／byCategory／byLocation／noLocation／pricedLine／unpricedLine／zeroTotal／error／retry）；`dashboard.value.*`（title／unpricedNote／emptyNote／viewStats／goFill）；`csv-fields`（依 csv-panel 現行 key 結構加 cost／currency 說明）
- [ ] csv-panel：欄位說明與後端 `EXPORT_COLUMNS` 一致（cost 2 位小數字串；currency＝帳號幣別）
- [ ] 測試：既有 `csv-panel.test.tsx` 補文案斷言；`pnpm -F @ims/web test` 全套（79+ 檔）

**Commands:**
- `pnpm -F @ims/web test`；`pnpm -F @ims/web typecheck`

---

## Phase 3: e2e、文件收尾

### Task 3.1: e2e `valuation.spec.ts`＋統計空態更新

**Files:**
- Create: `apps/web/tests/valuation.spec.ts`
- Modify: `apps/web/tests/statistics.spec.ts`（空態「尚無資料」5 → 7）

**TODO:**
- [ ] ① 估值主流程：新用戶 register → API 建 2 件（`cost=1200.50` qty 2；另一件無成本 qty 1）→ `/statistics`：`value-summary` 顯示 `NT$2,401`（整數無小數）＋「未填 1/2」；兩張價值圖可見；`value-summary` 為頁面最前區塊
- [ ] ② 幣別連動：`/settings/preferences` 切 `JPY` → `/statistics` 前綴變 `¥`（載入後）＋重整後持久
- [ ] ③ 物品流程：UI 表單填 `99.50` 建立 → 詳情 `item-cost` 顯示 `NT$99.50`；表單 `1.234` → 行內錯誤不送出
- [ ] ④ 儀表板：`ValueCard` 金額可見＋連結至 `/statistics`；DOM 序在 `ActiveLoansCard` 之後（locator 順序斷言）
- [ ] ⑤ 統計空態：新用戶 `/statistics` →「尚無資料」恰 **7** 張（原 5＋價值 2）；`statistics.spec.ts` 更新
- [ ] 全套 e2e 回歸（53+4；新增 spec 4 情境）

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx && pnpm exec playwright test`

### Task 3.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.27]`）、`docs/v2-roadmap.md`（Phase 27 ✅＋測試規模；§5.6 註記實作位置）、本計畫（勾選＋Final Verification）

**TODO:**
- [ ] CHANGELOG alpha.27：`items.cost`／migration 0021／`currency` 偏好／`GET /api/stats/value`（總值＋分布＋未填比例）／統計頁估值區塊／儀表板估值卡（行動卡後）／CSV `cost`／`currency`／backup `format_version 3`＋`_serialize` Decimal 修正（修 lists 匯出潛在 500）／`formatCurrency`（TWD→NT$ 雙語）
- [ ] v2-roadmap：Phase 27 ✅＋測試規模更新；§5.6「金額與日期格式（Phase 27 建立）」補實作位置 `apps/web/lib/format/currency.ts`
- [ ] 本計畫：全任務勾選＋Final Verification（實測數字、環境註記）
- [ ] 收尾視覺走查：估值摘要（淺／深色）／價值兩圖／未填比例／表單成本（含錯誤態）／詳情顯示／設定幣別預覽／儀表板卡位置／行動 390 版

**Commands:**
- `pnpm exec playwright test`（全套）

---

## API 契約（實作權威）

**`ItemCreate`／`ItemUpdate`**：`cost?: string|null`（十進位字串；伺服器以 `ge=0, max_digits=12, decimal_places=2` 驗證；`null`＝清空）
**`ItemRead`**：`cost: string|null`（例 `"12.30"`）
**`PreferencesRead`**：`currency: "TWD"|"USD"|"EUR"|"JPY"|"CNY"|"HKD"`（預設 `"TWD"`）；`PreferencesUpdate.currency?`
**`GET /api/stats/value`** → `{currency, total_value: string, priced_items: int, unpriced_items: int, total_items: int, by_category: [{category_id, name, value: string, count}], by_location: [{location_id, label, value, count}], by_warehouse: [{warehouse_id, name, value, count}]}`（cost null 以 0 計；`is_deleted` 排除；金額 2 位小數字串）
**CSV**：export 欄位序 `…, min_quantity, cost, currency, category_name, …`；import `cost`（空→null；非法→`invalid_cost`）、`currency`（空或＝帳號幣別→通過；不符→`currency_mismatch`）
**Backup**：`format_version: 3`；`items[].cost: string|null`；`_serialize` 對所有 Decimal 一律轉字串
**Web 格式**：`formatCurrency(value, currency, locale)`——整數 0 位、有小數 2 位、JPY 0 位；TWD＝`NT$`（zh-TW／en 一致）

### §5.4 狀態表（本 phase 介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| 統計頁估值區塊（27） | 卡內 skeleton | 無任何成本 → 總值 `NT$0`＋「為物品補上成本」引導；兩圖 `EmptyChart` | 卡內 compact 錯誤＋重試（不整頁壞） | 金額＋未填比例＋兩圖分布 | 部分未填 → 比例註記並明示「未填以 0 計」 |
| 儀表板估值卡（27） | 小卡 skeleton | 無成本 → `NT$0`＋「前往填寫成本」連結 | 隨卡片 compact 錯誤態 | 金額＋未填註記＋deep link `/statistics` | 同左（比例註記） |
| 物品表單成本欄（27） | 沿用表單載入 | 未填＝空欄（可選欄位，無強制） | 行內驗證（`1.234`／`-1`／非數字）；伺服器 422 → 欄位錯誤顯示 | 送出後詳情格式化顯示（`item-cost`） | 幣別註記隨偏好（唯讀） |
| 幣別設定（27） | 偏好載入 skeleton（沿用） | — | 儲存失敗 toast＋回滾（既有模式） | 成功 toast＋預覽即時更新 | 偏好更新後統計自動重抓（invalidate `["stats"]`） |

### 驗收對照（roadmap §六 Phase 27）

| 驗收項 | Task |
|---|---|
| Decimal 精度 | T1.1＋T1.2＋T1.4＋T2.1 |
| null 成本處理（以 0 計、顯示未填比例） | T1.4＋T2.5＋T2.6 |
| i18n（金額格式；TWD→NT$ 雙語） | T2.1＋T2.7 |
| `items.cost`＋CRUD 帶欄位 | T1.1＋T1.2 |
| 幣別設定（個人 ＞ 偏好） | T1.3＋T2.2 |
| `GET /api/stats/value`（總值、by category/location/warehouse、未填比例） | T1.4 |
| 統計頁估值卡片＋圖表（沿用既有圖表語彙） | T2.4＋T2.5 |
| 儀表板卡片（行動卡群組之後，§5.1） | T2.6 |
| CSV `cost`／`currency` | T1.5＋T2.7 |
| 備份相容（format_version 3） | T1.6 |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run --extra test pytest -q` → __ passed
- [ ] Web：`pnpm -F @ims/web test` → __ passed（__ 檔）＋`typecheck` 0 error
- [ ] api-types 重生成零 diff
- [ ] 真實 PG：`alembic current`＝`0021 (head)`；以 dev 庫實測 `GET /api/stats/value`（金額、比例、幣別）＋設定頁切幣別→統計頁前綴即時變
- [ ] e2e：__ passed（含 `valuation.spec.ts` 4 情境；統計空態 7）
- [ ] 視覺走查：`phase27-visual/`（估值摘要淺／深色、價值兩圖、未填比例、表單成本＋錯誤態、詳情顯示、設定幣別預覽、儀表板卡位置、行動 390）

### 收尾環境註記（2026-10-17 起填）

- （待補）
