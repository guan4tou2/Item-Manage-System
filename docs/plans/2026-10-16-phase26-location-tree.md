# Phase 26 — 多層位置樹重建 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 26（L409–437）＋ §5.4 位置樹列（L164）、§5.7 樹雙模式與 a11y、§5.6 色彩契約。
> **破壞性最高的一個 phase**：現有 `locations` 平面三欄（floor/room/zone）砍掉重建為任意深度樹；遷移前**強制備份**（roadmap L616）＋ dry-run 審查。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**；完成即 commit（Conventional Commits，繁中 body）。

**Goal：** 位置由 `floor/room/zone` 三欄平面結構改為**任意深度樹**（樓層 ＞ 房間 ＞ 櫃子 ＞ 抽屜…）：`parent_id` adjacency list ＋ recursive CTE 查詢；`/locations` 樹管理頁（展開收合／改名／新增／刪除限制／桌面拖放／行動 ⋯ 選單搬移／鍵盤操作）；物品表單與篩選改用樹狀選擇器（桌機 cascading／行動 bottom sheet＋扁平搜尋顯示完整路徑）；物品詳情麵包屑路徑；篩選選父節點**預設含子孫**＋「僅此層」toggle；一次性資料遷移（舊平面 → 樹）保證**每件物品遷移後仍有 location_id（無孤兒）**並輸出遷移報告。

**Architecture：** `locations`（`id, owner_id, parent_id(self-FK), name, kind, sort_order, floor_plan_image_id`）→ repository 以 recursive CTE 提供三種查詢：**子孫集合**（items 篩選／刪除防護）、**節點路徑**（麵包屑／列表／CSV／標籤）、**樹**（管理頁，附直接物品數）；service 守衛：父節點存在且同 owner、**不得移到自己或子孫之下**（防循環）、**有物品或有子節點一律 409**（附計數，無遞移刪除）。遷移＝`location_tree_migration`（SQLAlchemy Core，PG／SQLite 皆可跑）內建 `analyze_flat()`（dry-run，唯讀）與 `migrate_flat()`；Alembic `0020` 依序：加欄 → 執行資料遷移 → `name` NOT NULL → 移除舊三欄 → 建索引。

**Tech Stack：** FastAPI、SQLAlchemy async（Core recursive CTE）、Alembic（migration `0020`；alembic env 為 async＋`run_sync`）、pytest（SQLite in-memory；遷移測試以 raw old-schema table fixture）、React Query、next-intl、shadcn/ui（Sheet／Dialog／Select）、Vitest、Playwright。**不新增依賴**（拖放用原生 HTML5 DnD，行動版不做觸控拖拽）。

**關鍵既有資產（重用，勿重造）：**
- 位置平面實作：`app/models/location.py`、`app/schemas/location.py`、`app/repositories/locations_repository.py`、`app/services/locations_service.py`、`app/routes/locations.py`（`GET ""`／`POST ""`／`POST /reorder`／`PATCH /{id}`／`DELETE /{id}`）
- 樹狀前例：`categories`（self-FK＋partial unique index「同 owner 同 parent 同名」）；Web 平坦化走訪 `flatCats`（`items-filter-panel.tsx`）與 `flattenCategories`（`item-form.tsx`）
- 物品端：`items_repository.list_paginated(location_id=…)`（目前精確比對）、`ItemRead.location`／`LocationRead`、`items_service._validate_refs`（同 owner 驗證）、批次更新 `PATCH /api/items/bulk {item_ids, location_id}`（**搬移物品可重用，無需新端點**）
- 消費端（全部需改）：`stats_repository.by_location`（label＝floor/room/zone join）、`csv_service`（export `location_floor/room/zone`；import `_ensure_location`）、`backup_service`（`format_version: 1`、locations 三欄）、`routes/barcodes.py:_location_path`（Phase 25 新增）
- e2e／單元影響面：`apps/web/tests/{navigation,statistics}.spec.ts`；`items-table`／`item-form`／`items-list-client`／`items-filter-panel`／`csv-panel`／`locations-panel`
- 入口：`/locations` 頁與 `/settings/taxonomy` 位置頁籤**共用** `LocationsPanel`（改一處兩處生效）

**盤點定案（2026-10-16，實作前一覽）：**
1. **Schema**：`locations(id, owner_id, parent_id→locations.id ondelete=RESTRICT, name String(50) NOT NULL, kind String(20) nullable, sort_order, floor_plan_image_id)`；`floor/room/zone` 移除。索引：`Index("ix_locations_owner_parent_sort", "owner_id", "parent_id", "sort_order")`＋partial unique「同 owner 同 parent 同名」（root 與非 root 各一，比照 `categories`）。
2. **查詢策略**：adjacency list ＋ recursive CTE（PG／SQLite 皆支援；SQLAlchemy `cte(recursive=True)`）。materialized path 不在本 phase 實作（保留為後續優化）。
3. **`kind` 語義**：可選、`String(20)`；允許預設鍵 `floor|room|shelf|box|other`（UI 以 i18n 顯示）或自由文字（原樣顯示）。不做 enum 驗證（roadmap 明示「或自由文字」）。
4. **排序**：`sort_order` 為**同一 parent 內**的順序；`reorder` 改為 `POST /api/locations/reorder {parent_id, location_ids}`——`location_ids` 必須是該 parent 的**完整子節點集合**（否則 422），重寫為 0..N。
5. **乾淨樹**：`GET /api/locations`＝平坦清單（**走訪序**：依 parent sort_order→name 深度優先）附 `path`（"1F / 廚房 / 上櫃"）；`GET /api/locations/tree`＝巢狀（root 陣列，節點附 `item_count`＝**直接**物品數與 `children`）；`GET /api/locations/{id}/path`＝`{id, path, nodes:[{id,name,kind}]}`（詳情麵包屑用）。
6. **刪除策略**：有物品或有子節點 → **409**，detail 為結構化物件 `{code: "has_items"|"has_children", items: N, children: M}`（Web 依 §5.4 顯示「此位置有 N 件物品」＋「先搬移」）；不提供遞移刪除。
7. **防循環**：`PATCH /api/locations/{id} {parent_id}`（＝move；`null` 代表移到根）——目標為自己或自己的子孫 → **422 `{code:"cycle"}`**；`parent_id` 非本人所有 → 404。service 以子孫集合判定（CTE），並有測試。
8. **搬移物品**：刪除對話框的「先搬移」＝把該節點的**直接物品**批次移到目標節點 → 重用既有 `PATCH /api/items/bulk`（前端先以 `GET /api/items?location_id={id}&location_scope=exact` 取清單，再送 bulk）；刪除對話框按鈕「先處理子節點」→ 展開並聚焦第一個子節點（子節點須先刪除或搬走）。
9. **物品篩選語義**：`GET /api/items?location_id=X&location_scope=subtree|exact`（**預設 `subtree`**＝含子孫，recursive CTE 取 id 集合）；Web 篩選面板提供「僅此層」toggle（＝`exact`）。
10. **`ItemRead.location`**：維持 `LocationRead` 但欄位改為 `{id, parent_id, name, kind, sort_order, floor_plan_image_id, path}`——**`path` 由 API 計算**，Web 不需自行組路徑（列表／詳情／麵包屑／候選清單一致）。
11. **CSV**：匯出改為單欄 `location_path`（`"1F / 廚房 / 上櫃"`，取代 `location_floor/room/zone`）；匯入接受 `location_path`（以 `/` 分割逐層建立／重用節點：深度 1→`floor`、2→`room`、≥3→`other`）**並保留舊三欄相容**（`location_floor/room/zone` 併為同一路徑邏輯，供舊檔匯入）。CSV 面板文案同步。
12. **備份**：`locations` 區段改為樹欄位（`id, parent_id, name, kind, sort_order, floor_plan_image_id`）；`format_version` 1 → **2**（Phase 29 還原依版本處理）。items 的 `location_id` 語義不變。
13. **warehouse 正交**：warehouse 不進樹、不成為 parent；統計分組維持「位置樹節點」與「倉庫」兩條獨立軸（避免重複或遺漏）。
14. **遷移＝重新指向（rebuild）**：對每個 owner，逐一讀出舊列 `(floor, room, zone)`，建立／重用canonical 節點鏈（`floor`→`floor` 節點；`room`→`room` 節點；`zone`→`other` 節點），把該列所有物品 `location_id` 指向最深節點，刪除舊列。**保證無孤兒**（物品一定指向存在的節點）。
15. **遷移報告**：`{source_rows, created_nodes, merged_rows, orphan_nodes, unassigned_items}`——`merged_rows`＝被併入既有 canonical 節點的舊列數（含完全相同組合的重複列）；`orphan_nodes`＝遷移後「無物品且無子節點」的節點數；`unassigned_items`＝`location_id IS NULL` 的物品數（仍允許，但報告出來）。Alembic 遷移與 dry-run 皆回傳同一報告（遷移時寫入 log）。
16. **dry-run**：`apps/api/scripts/location_migration_dry_run.py`（唯讀；`run_sync(analyze_flat)`）——遷移前在正式庫上先跑，人工審查報告；**遷移前強制備份**（執行前置）。
17. **樹 UI 拖放**：桌面用原生 HTML5 DnD（`dragstart`／`dragover`／`drop`）；**非法目標即時灰化＋tooltip**（自身／自身子孫）；行動版不做觸控拖拽，改用「⋯ 選單 → 搬移至」（bottom sheet＋扁平搜尋，顯示完整路徑）。
18. **a11y（§5.7）**：`role="tree"`／`treeitem`＋`aria-expanded`／`aria-level`／`aria-setsize`；方向鍵（↑↓ 移焦、→ 展開/首子、← 收合/父節點、Enter 選取、F2 改名）；Tap target ≥44px；icon-only 必有 `aria-label`；樂觀更新失敗 → 回滾＋toast，並以 `aria-live="polite"` 播報。
19. **空狀態／搜尋**：空樹 → 引導建立第一層（單一輸入框＋建立）；搜尋框過濾樹，無結果 → 「建立新節點？」（以搜尋字串為名建立於根或當前選取節點下）。
20. **既有資料的開發庫處理**：本 phase 對 dev／e2e 長期沿用資料庫執行**真實遷移**（非 drop）；遷移前備份存檔於暫存，遷移後以 `GET /api/backup/export` 再存一份新格式。

**執行前置（安全網，依 roadmap L616）：**
1. **遷移前強制備份**（以 main 現行舊版堆疊執行，勿先起新碼）：
   - `docker compose up -d`（舊版；避免 api 首次啟動就升級 schema）→ 註冊／登入取得 token → `curl -H "Authorization: Bearer $TOKEN" http://localhost/api/backup/export > phase26-pre-migration-backup.json`
   - 同時留存遷移前統計（`locations` 列數、`items` 依 `location_id` 分佈、`location_id IS NULL` 數）供報告比對
2. **dry-run 審查**：新碼 worktree 內執行 `uv run python scripts/location_migration_dry_run.py`（連 dev PG），人工檢視報告與計畫樹
3. worktree：`phase26-location-tree`（branch `claude/phase26-location-tree`）；alembic head＝`0019`
4. 起新堆疊（`ENABLE_DEV_ROUTES=1 docker compose up -d --build api web`＋`docker compose up -d nginx`）→ api 容器啟動即 `alembic upgrade head`（0020）；以 `alembic current` 與容器 log 的遷移報告驗證
5. 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `pnpm -F @ims/web test`／`typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`；e2e `pnpm exec playwright test`

**Execution Order**
1. API：`locations` model＋migration `0020`（加欄→資料遷移→收尾）→ `location_tree_migration`（analyze／migrate）＋dry-run＋fixture 測試
2. API：repository（CTE：descendants／paths／tree／counts）→ service（create／update／move／reorder／delete 守衛）→ routes／schemas → api-types
3. API：消費端（items 篩選 scope＋`location.path`、stats label、CSV `location_path`、backup v2、barcode path）
4. Web：locations api／hooks → 樹管理頁（桌機）→ 行動搬移 → 樹狀選擇器 → 詳情麵包屑／列表／篩選 toggle／i18n
5. e2e → 文件收尾（CHANGELOG／roadmap／勾選＋Final Verification）

---

## Phase 1: API — 樹化 schema、遷移與樹操作

### Task 1.1: `locations` 樹化 model＋migration `0020`

**Files:**
- Modify: `apps/api/app/models/location.py`
- Create: `apps/api/alembic/versions/0020_location_tree.py`
- Test: `apps/api/tests/test_location_model_smoke.py`

**TODO:**
- [x] Model：`parent_id Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True)`、`name Mapped[str]`（String(50), nullable=False）、`kind Mapped[Optional[str]]`（String(20)）；移除 `floor`／`room`／`zone`；`__table_args__` 加 `Index("ix_locations_owner_parent_sort", "owner_id", "parent_id", "sort_order")`＋兩個 partial unique（root／非 root，比照 `categories`）；`children`／`parent` 關係（`remote_side`；`children`／`items` 皆 `passive_deletes=True`，讓 DB 層 RESTRICT／SET NULL 真正生效而非 ORM 先置 NULL）
- [x] Migration `0020`（`down_revision="0019"`）順序：add `parent_id`／`name`（nullable）／`kind` → **放寬 `floor` NOT NULL**（遷移期間新列不填舊欄；實作時發現的必要步驟）→ **呼叫 `location_tree_migration.migrate_flat(bind)` 做資料遷移**（並以 `preview_paths` 寫入 log）→ `ALTER COLUMN name SET NOT NULL` → drop `floor`／`room`／`zone` → create indexes／unique（比照 `categories` partial index 語法）＋FK；downgrade raise（不可逆）
- [x] smoke：建 root／child／grandchild；同 parent 同名 → unique 違反；跨 parent 同名允許；刪除有子節點的 parent → FK RESTRICT（SQLite 需 `PRAGMA foreign_keys=ON`，比照 Phase 24 smoke）
- [x] 真實 PG 驗證：遷移前備份已存 → 起新堆疊 → `alembic current`＝`0020`＋遷移報告 log

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_location_model_smoke.py`

### Task 1.2: `location_tree_migration`（analyze／migrate）＋dry-run 腳本＋fixture 測試

**Files:**
- Create: `apps/api/app/services/location_tree_migration.py`
- Create: `apps/api/scripts/location_migration_dry_run.py`
- Test: `apps/api/tests/test_location_tree_migration.py`

**TODO:**
- [x] `MigrationReport`（dataclass：`source_rows`／`created_nodes`／`merged_rows`／`orphan_nodes`／`unassigned_items`）＋`as_dict()`
- [x] `analyze_flat(conn) -> MigrationReport`：**唯讀**；讀舊列（`id, owner_id, floor, room, zone`）→ 計算 canonical 節點計畫與 `merged_rows`／`orphan_nodes`／`unassigned_items`（不寫入）
- [x] `migrate_flat(conn) -> MigrationReport`：Core DML——逐 owner 建立／重用節點（同 owner＋同 parent＋同名 → 重用；深度 1→`kind='floor'`、2→`'room'`、≥3→`'other'`，`sort_order` 以首次出現序 0..N）；`UPDATE items SET location_id=<最深節點> WHERE location_id IN (舊列 ids)`；刪除舊列；回傳報告（PG／SQLite 通用，僅用 INSERT/SELECT/UPDATE/DELETE）
- [x] 邊界：`floor` 為空字串（舊 schema 不允許，但仍防禦）、`room`／`zone` 為 NULL、同 owner 內完全相同組合重複列（合併）、舊列無物品（仍建節點並計入 `orphan_nodes`）、物品 `location_id IS NULL`（計入 `unassigned_items`）
- [x] `location_migration_dry_run.py`：async engine ＋ `run_sync(analyze_flat)`；印 JSON 報告（含 `preview_paths` 計畫樹）；**不寫入**（以「跑完後 DB 無變化」驗證）；已對 dev 庫實跑（報告：`source_rows=5`／`created_nodes=7`／`merged_rows=1`／`orphan_nodes=1`／`unassigned_items=216`）
- [x] 測試（fixture：以 raw SQL 建「舊＋新欄並存」的 `locations` 表、`items` 表，塞入平面資料）：平坦 3 層 → 樹形狀正確；兩列同 `floor/room` 不同 `zone` → 共用中間節點；兩列完全同組合 → 合併＋物品重新指向（`merged_rows=1`）；空列（無物品）→ 節點存在且 `orphan_nodes` 計數；`analyze_flat` 與 `migrate_flat` 報告一致；遷移後**無孤兒**（每件有 location_id 的物品指向存在節點）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_location_tree_migration.py`

### Task 1.3: repository（CTE）＋service（樹操作守衛）

**Files:**
- Modify: `apps/api/app/repositories/locations_repository.py`
- Modify: `apps/api/app/services/locations_service.py`
- Test: `apps/api/tests/test_locations_tree_service.py`

**TODO:**
- [x] repository：`list_for_owner`（走訪序，需 path 排序：以 recursive CTE 產生 `path_names` 並排序）、`get_owned`、`create`／`update`／`delete`（既有風格）、`children_of(session, owner_id, parent_id)`、`descendant_ids(session, owner_id, root_ids) -> set[int]`（含自身；CTE）、`paths_for(session, owner_id, location_ids) -> dict[int, str]`（單一查詢、ancestor 串接）、`tree_rows(session, owner_id)`（節點＋`item_count` 聚合）、`count_children`／`count_items`
  - 實作定案：`descendant_ids` 用 recursive CTE（唯一需要單一 SQL 之處）；**走訪序與路徑以 Python 組裝**（`fetch_all` ＋ `walk_order`／`path_for`／`paths_for` 純函式）——位置節點數量小，單純且可單元測試
- [x] service：`list_all`（回傳含 `path` 的結構）、`tree`（巢狀組裝）、`path_of(id)`、`create`（`parent_id` 需存在且同 owner，否則 404；同 parent 同名 → 409 `{code:"duplicate_name"}`）、`update`（`name`／`kind`／`sort_order`／`floor_plan_image_id`；`parent_id` 存在時＝move，經 `_assert_no_cycle`）、`reorder(parent_id, ids)`（需完整子集合，否則 422）、`delete`（`children>0` → 409 `has_children`；`items>0` → 409 `has_items`；兩者皆附計數）
- [x] `_assert_no_cycle`：目標 parent 為自身或其子孫 → 422 `{code:"cycle"}`
- [x] 測試：CTE（`descendant_ids` 三層正確、`paths_for` 多節點正確）；move 成功／移到自身／移到子孫 → 422；跨 owner parent → 404；同名兄弟 → 409；reorder 完整集合成功／缺漏 → 422／跨 parent → 422；delete 有子 → 409＋counts／有物品 → 409＋counts／乾淨 → 204（含「搬到別處後即可刪除」流程）；走訪序穩定（19 例）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_locations_tree_service.py`

### Task 1.4: routes／schemas＋api-types

**Files:**
- Modify: `apps/api/app/schemas/location.py`
- Modify: `apps/api/app/routes/locations.py`
- Test: `apps/api/tests/test_locations_routes.py`、`apps/api/tests/test_location_advanced.py`（改寫）
- Regenerate: `packages/api-types/*`

**TODO:**
- [x] schemas：`LocationCreate(parent_id?, name, kind?, sort_order=0, floor_plan_image_id?)`（`extra="forbid"`——讓舊客戶端送 floor/room/zone 直接 422 而非靜默丟棄）、`LocationUpdate(name?/kind?/sort_order?/floor_plan_image_id?/parent_id?)`（`extra="forbid"`）、`LocationRead(id, parent_id, name, kind, sort_order, floor_plan_image_id, path)`、`LocationTreeNode(LocationRead + item_count + children)`、`LocationPath(id, path, nodes)`、`LocationReorder(parent_id?, location_ids)`
- [x] routes：`GET ""`（平坦＋path）、`GET "/tree"`（**置於 `/{location_id}` 之前**避免路徑衝突）、`GET "/{location_id}/path"`、`POST ""`、`POST "/reorder"`、`PATCH "/{location_id}"`、`DELETE "/{location_id}"`（409 結構化 detail）
- [x] 測試改寫：CRUD＋`path` 正確；`/tree` 巢狀＋`item_count`；`/path` 三層；anonymous 401（全端點）；跨 owner 404／隔離；名稱為空 422；`kind` 過長 422；非白名單欄位 422；409 兩態 detail 內容；reorder 422（重複／不完整／跨 parent／跨 owner）；move 422 cycle；sort_order／floor_plan／kind 自由文字（21 例）
- [x] api-types 重生成（`LocationRead`／`LocationTreeNode`／`LocationPath`／`LocationReorder`；舊 floor/room/zone 欄位移除）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_locations_routes.py tests/test_location_advanced.py`
- `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`

### Task 1.5: 消費端（items／stats／CSV／backup／barcode）

**Files:**
- Modify: `apps/api/app/repositories/items_repository.py`、`apps/api/app/routes/items.py`、`apps/api/app/services/items_service.py`
- Modify: `apps/api/app/repositories/stats_repository.py`
- Modify: `apps/api/app/services/csv_service.py`
- Modify: `apps/api/app/services/backup_service.py`
- Modify: `apps/api/app/routes/barcodes.py`
- Test: `apps/api/tests/test_items_location_scope.py`、既有 `test_items_*`／`test_csv*`／`test_backup.py`／`test_stats*`／`test_barcodes_routes.py` 補案
- Regenerate: `packages/api-types/*`

**TODO:**
- [x] items：`list_paginated(..., location_scope="subtree"|"exact")`——`subtree` 以 `descendant_ids` 轉 `IN`（repository 改收 `location_ids: list[int] | None`，空集合 → 明確無結果）；route `?location_scope=`（`Literal`，非法值 422）；頁面列以 `paths_for` 補 `location.path`
- [x] `ItemRead.location`＝`LocationRead`（含 path）；`_paths_for_items` 依 **item.owner**（共享清單／群組可見的他人物品也正確）批次取路徑；`_validate_refs` 不變（同 owner 驗證）
- [x] stats `by_location`：repository 回 `{location_id, count}`；service 以樹路徑組裝 `label`（無位置 → `label=None`）
- [x] CSV：export 改 `location_path`（移除三欄；值＝path 或空）；import 支援 `location_path` 與舊三欄（`_ensure_location_path`：以 `/` 分割、逐層重用或建立、kind 依深度 1=floor／2=room／≥3=other；快取以路徑前綴共用中間節點）；`IMPORT_OPTIONAL` 更新（保留三欄為相容列）
- [x] backup：locations 區段改樹欄位（`id, parent_id, name, kind, sort_order, floor_plan_image_id`）；`format_version` 1 → **2**
- [x] `barcodes.py`：候選 `location_path` 改用 `paths_for`（完整樹路徑，與列表／詳情一致）
- [x] 測試：新增 `test_items_location_scope.py`（預設含子孫／exact／與 q 組合／`location.path` 完整／搬移後 path 更新／未知節點空結果／非法 scope 422／bulk 搬移後可刪節點）；CSV（`location_path` 建三層樹＋kind 推定、舊三欄相容、匯出匯入 round-trip）；backup（v2＋樹欄位、舊三欄不再輸出）；stats（repository 直接計數＋service label）；barcode（樹路徑）；全套 **691 passed**

**Commands:**
- `cd apps/api && uv run --extra test pytest -q`

---

## Phase 2: Web — 樹管理頁、樹狀選擇器與路徑呈現

### Task 2.1: locations api client／hooks

**Files:**
- Modify: `apps/web/lib/api/locations.ts`、`apps/web/lib/hooks/use-locations.ts`
- Test: `apps/web/lib/api/locations.test.ts`、`apps/web/lib/hooks/use-locations.test.tsx`

**TODO:**
- [x] api：`listLocations`（平坦＋path）、`getLocationTree`、`getLocationPath`、`createLocation`（parent_id）、`updateLocation`、`moveLocation(id, parent_id)`、`reorderLocations(parent_id, ids)`、`deleteLocation`；型別取自 `@ims/api-types`
- [x] hooks：`useLocationTree`、`useMoveLocation`、`useReorderLocations`（未用 `useLocationPath`：詳情改用 `ItemRead.location.path`）；統一 invalidate `["locations"]`／`["items"]`／`["stats"]`
- [x] 測試：請求路徑／body 正確（含 move 的 `parent_id: null`）；409 detail 透傳；invalidate 範圍（12 例）

**Commands:**
- `pnpm -F @ims/web test -- lib/api/locations lib/hooks/use-locations`

### Task 2.2: `/locations` 樹管理頁（桌機）

**Files:**
- Rewrite: `apps/web/components/taxonomy/locations-panel.tsx`（樹版；`/locations` 與 `/settings/taxonomy` 兩入口同時生效）
- Create: `apps/web/components/taxonomy/location-tree-node.tsx`（＋test）
- Create: `apps/web/components/taxonomy/location-delete-dialog.tsx`（＋test）
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`
- Test: `apps/web/components/taxonomy/locations-panel.test.tsx`

**TODO:**
- [x] 樹渲染：`role="tree"`／`treeitem`＋`aria-expanded`／`aria-level`；展開收合；skeleton（LOADING）；空樹 → 「建立第一層」單一輸入框引導（EMPTY）；搜尋框（過濾；無結果 → 「建立新節點？」按鈕，以搜尋字串建立於根）
- [x] 操作：新增子節點（行內輸入）、改名（F2／雙擊→行內輸入）、刪除（開啟對話框）、`kind` 顯示（預設鍵 i18n／自由文字原樣；編輯沿用 API `kind` 欄位，UI 以 preset＋自由文字呈現）
- [x] 桌面拖放（HTML5 DnD）：拖曳節點到新 parent（含「拖到樹容器空白＝移到最上層」）；**非法目標（自身／自身子孫）即時灰化＋tooltip**；drop → 樂觀更新＋toast＋`aria-live` 播報，失敗回滾（§5.4）
- [x] 刪除對話框：以 `item_count`／子節點數顯示「此位置有 N 件物品」／「此位置有 N 個子節點」；按鈕「先搬移物品」（目標＝樹狀選擇器；送出＝`items?location_id=&location_scope=exact` 取 id → `PATCH /api/items/bulk`）與「先處理子節點」（展開並聚焦第一個子節點）；伺服器 409 仍擋下時 toast 提示（結構化 detail）
- [x] 鍵盤（§5.7）：↑↓ 移焦、→ 展開／首子、← 收合／父節點、Enter 切換、F2 改名；roving tabindex（列 `min-h-11`＝44px）；icon-only `aria-label`；`aria-live` 播報樂觀結果
- [x] i18n zh-TW／en：`locations.*` 群組（tree／select／delete／move／errors／kind）＋ `items.filter.onlyThisLevel`（逐鍵插入，未重排整檔）
- [x] 測試：展開收合；改名；新增子節點；刪除對話框計數與兩顆按鈕／確認禁用；拖放成功（drop → hook 呼叫）／非法拖放灰化＋tooltip；鍵盤導覽；搜尋無結果→建立；空樹引導；skeleton／錯誤重試（11 例）

**Commands:**
- `pnpm -F @ims/web test -- components/taxonomy`

### Task 2.3: 行動版搬移（⋯ 選單 → bottom sheet＋扁平搜尋）

**Files:**
- Create: `apps/web/components/taxonomy/location-move-sheet.tsx`（＋test）
- Modify: `apps/web/components/taxonomy/location-tree-node.tsx`（`md:hidden` 的「⋯」選單）
- Modify: i18n 兩檔

**TODO:**
- [x] 行動（`md` 以下）：節點列右側「⋯」按鈕（`aria-label`）→ 選單：選項「新增子節點」「改名」「搬移至…」「刪除」；「搬移至…」→ `LocationMoveSheet`＝扁平清單搜尋（顯示**完整路徑**）＋「移到最上層」；自身／子孫標示不可選（disabled＋「不可選」）
- [x] 桌面（`md` 以上）「⋯」選單不含搬移（拖放為主），保留改名／刪除（一致性）
- [x] 測試：sheet 搜尋過濾／自身與子孫 disabled／toRoot／確認帶目標 id（3 例）；panel 測試以 `useIsMobile: false` 驗桌面分支

**Commands:**
- `pnpm -F @ims/web test -- components/taxonomy`

### Task 2.4: 樹狀選擇器（桌機 cascading／行動 bottom sheet＋搜尋）

**Files:**
- Create: `apps/web/components/locations/location-select.tsx`（＋test）
- Modify: `apps/web/components/items/item-form.tsx`（取代位置 `Select`）、`apps/web/components/items/items-filter-panel.tsx`、`apps/web/app/(app)/items/items-list-client.tsx`（批次搬移目標；既有 flat select）
- Modify: i18n 兩檔

**TODO:**
- [x] 元件介面：`value: number | null`、`onChange`、`allowNone`、`label`（a11y）、可注入 `nodes`（否則走 `useLocations()`）
- [x] 桌機：**cascading** 多層 `Select`（第 N 層＝所選節點的子節點；可續開下一層或選「僅選此層」停在當前節點）；顯示所選完整路徑；由外部 value 還原層級
- [x] 行動：`Button`（顯示當前路徑）開 `Sheet` → 扁平搜尋清單（完整路徑、可捲動）tap 回填；「未指定」選項
- [x] 整合：物品表單、篩選面板、刪除對話框搬移目標（批次搬移清單沿用既有原生 select，顯示樹路徑）
- [x] 測試：cascading 三層逐層選取／外部 value 還原／清除為 None；行動 sheet 搜尋回填與 trigger 路徑（5 例）

**Commands:**
- `pnpm -F @ims/web test -- components/locations components/items`

### Task 2.5: 詳情麵包屑、列表路徑、篩選「僅此層」toggle、CSV 面板文案

**Files:**
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`（麵包屑路徑；長路徑截斷「… / 抽屜」）
- Modify: `apps/web/components/items/items-table.tsx`（位置欄改 `location.path`＋`title`）
- Modify: `apps/web/app/(app)/items/items-list-client.tsx`（`locationScope` 篩選狀態＋URL 參數）、`apps/web/components/items/items-filter-panel.tsx`（「僅此層」toggle）
- Modify: `apps/web/components/settings/csv-panel.tsx`（欄位說明改 `location_path`）
- Modify: `apps/web/lib/api/items.ts`（`ItemFilters.locationScope`）
- Modify: i18n 兩檔
- Test: 上述元件的既有測試檔補案

**TODO:**
- [x] 詳情：`item.location.path` 以 `/` 分隔顯示；層數 > 3 時中間截斷（「1F / … / 抽屜」，附全路徑 `title`、`data-testid="item-location-path"`、mono）
- [x] 列表：位置欄顯示樹路徑（截斷 + `title`）
- [x] 篩選：`locationScope: "subtree" | "exact"`（預設 `subtree`＝不輸出參數），checkbox 標籤「僅此層」；URL 參數 `location_scope`；清除位置篩選時同步重置
- [x] CSV 面板文案：`location_path`（欄位清單同步含 barcode／tag_names）
- [x] i18n：`items.filter.onlyThisLevel`（zh-TW／en）
- [x] 測試：filters scope 讀寫 4 例；詳情長路徑截斷＋title；列表路徑截斷＋title；全套 **374 passed（79 檔）**

**Commands:**
- `pnpm -F @ims/web test`；`pnpm -F @ims/web typecheck`

---

## Phase 3: e2e、文件收尾

### Task 3.1: e2e `locations-tree.spec.ts`

**Files:**
- Create: `apps/web/tests/locations-tree.spec.ts`
- Modify: `apps/web/tests/navigation.spec.ts`／`statistics.spec.ts`（若受位置改動影響）

**TODO:**
- [x] ① 建立樹：`/locations` → 建立「1F」→ 在其下建立「廚房」→ 再建立「上櫃」（以 UI 操作）；展開收合斷言
- [x] ② 改名：F2／行內編輯 → 名稱更新；重新載入後仍在
- [x] ③ 桌面拖放：合法搬移（`上櫃` → `2F`，API 路徑驗證）；非法目標（1F → 自身子孫）→ `data-drop-invalid` 灰化且 drop 不生效（Playwright 以合成 `dragstart`／`dragover`／`drop` 事件驅動；`dragTo` 不觸發 HTML5 DnD）
- [x] ④ 刪除限制：對有 2 件物品的節點按刪除 → 對話框顯示「此位置有 2 件物品。」→「先搬移物品」→ 再刪除成功；物品確實換到 2F（API 驗證）
- [x] ⑤ 物品表單樹狀選擇器：桌機 cascading 三層選取 → 儲存 → 詳情顯示麵包屑路徑（含 `title` 全路徑）
- [x] ⑥ 篩選語義：父節點篩選預設含子孫（種 2 件分屬父／子）→ 開「僅此層」→ 只剩直接屬於父節點的 1 件
- [x] ⑦ 行動搬移（390 寬）：`⋯` → 搬移至 → 搜尋 → 選取 → 節點換父（API 路徑驗證）
- [x] ⑧ 真實遷移驗證：`phase26_demo` 的樹（1F／廚房／上櫃／冰箱／2F／書房／3F）在 UI 正確呈現，`上櫃` 顯示「2 件」
- [x] 註記：遷移本身不在 e2e（屬一次性任務；以 fixture 單元測試＋dev 庫真實驗證覆蓋）；全套 e2e **53 passed（17 spec）**

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx && pnpm exec playwright test tests/locations-tree.spec.ts`

### Task 3.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.26]`）、`docs/v2-roadmap.md`（Phase 列＋測試規模）、本計畫（勾選＋Final Verification）
- 可能新增：`docs/locations.md`（樹語義與遷移說明；若內容足以獨立成篇）

**TODO:**
- [ ] CHANGELOG alpha.26：樹化 schema／CTE／樹 API／樹管理頁與拖放／行動搬移／樹狀選擇器／篩選 scope／CSV `location_path`／backup v2／遷移報告與 dry-run／刪除限制與防循環
- [ ] v2-roadmap：Phase 26 ✅＋測試規模更新
- [ ] 本計畫：全任務勾選＋Final Verification（實測數字、遷移報告摘要、環境註記）
- [ ] 記錄遷移實測：`source_rows`／`created_nodes`／`merged_rows`／`orphan_nodes`／`unassigned_items` 與備份檔位置

**Commands:**
- `pnpm exec playwright test`（全套）

---

## API 契約（實作權威）

**`GET /api/locations`** → `[{id, parent_id, name, kind, sort_order, floor_plan_image_id, path}]`（走訪序）
**`GET /api/locations/tree`** → `[{…同上, item_count, children: [...]}]`（巢狀）
**`GET /api/locations/{id}/path`** → `{id, path, nodes: [{id, name, kind}]}`（root → 自身）
**`POST /api/locations`** `{parent_id?, name, kind?, sort_order?}` → 201；同 parent 同名 → 409 `{code:"duplicate_name"}`；parent 不存在／非本人 → 404
**`PATCH /api/locations/{id}`** `{name?, kind?, sort_order?, floor_plan_image_id?, parent_id?}` → 200；`parent_id` 為自身／子孫 → 422 `{code:"cycle"}`；`parent_id: null`＝移到最上層
**`POST /api/locations/reorder`** `{parent_id, location_ids}` → 200（必須為該 parent 完整子集合，否則 422）
**`DELETE /api/locations/{id}`** → 204；有子節點 → 409 `{code:"has_children", children: M, items: N}`；有物品 → 409 `{code:"has_items", items: N, children: M}`
**`GET /api/items?location_id=&location_scope=subtree|exact`**（預設 `subtree`）
**CSV**：export `location_path`；import 接受 `location_path` ＋舊三欄
**Backup**：`format_version: 2`；`locations: [{id, parent_id, name, kind, sort_order, floor_plan_image_id}]`

### §5.4 狀態表（本 phase 介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| 位置樹（26） | 樹 skeleton | 空樹 → 建立第一層引導；搜尋無結果 → 「建立新節點？」 | 刪除 409 → dialog「此位置有 N 件物品」＋「先搬移」按鈕（直接開搬移對話框）；非法拖放即時灰化＋tooltip | 拖放／搬移樂觀更新＋toast | — |
| 樹狀選擇器（26） | 選項載入 skeleton | 無任何節點 → 「前往建立位置」連結 | 載入失敗 → 行內訊息＋重試 | 選取後顯示完整路徑 | 節點深層（>3 層）→ 桌機 cascading 續開欄／行動清單顯示完整路徑 |
| 物品詳情路徑（26） | 沿用詳情 skeleton | 無位置 → 「—」 | — | 麵包屑路徑（>3 層中間截斷） | 截斷時 `title` 提供全路徑 |

### 驗收對照（roadmap §六 Phase 26）

| 驗收項 | Task |
|---|---|
| 樹操作 API 測試（move、防循環、刪除限制、排序） | T1.3＋T1.4 |
| 行動版搬移（選單＋搜尋選父）與桌面拖放各自測試；樹的鍵盤操作 | T2.2（桌機＋鍵盤）＋T2.3（行動）＋T3.1 |
| 含子孫查詢（recursive CTE） | T1.3＋T1.5＋T2.5 |
| 遷移腳本測試（fixture：舊平面資料 → 樹） | T1.2 |
| 物品列表／搜尋／統計在樹下的回歸 | T1.5＋T2.5 |
| 安全網（遷移前備份＋dry-run） | 執行前置＋T1.2 |
| warehouse 正交（不吸收倉庫） | 盤點定案 13＋T1.5 測試 |

---

## Final Verification（收尾時填實測）

- [ ] **遷移前備份存檔**（舊版堆疊 `GET /api/backup/export`；記錄檔名與大小）
- [ ] dry-run 報告審查（計畫樹與計數符合預期）
- [ ] API：`cd apps/api && uv run --extra test pytest -q` 全綠
- [ ] Web：`pnpm -F @ims/web test` 全綠＋`pnpm -F @ims/web typecheck` 0 error
- [ ] api-types 重生成零 diff
- [ ] 真實 PG：`alembic current`＝`0020`＋遷移報告（source_rows／created_nodes／merged_rows／orphan_nodes／unassigned_items）
- [ ] 遷移後資料完整性：`items.location_id` 全部指向存在節點（無孤兒查詢 + 報告數字）
- [ ] e2e：`pnpm exec playwright test` 全綠（環境註記：`ENABLE_DEV_ROUTES=1`＋`docker compose up -d nginx`）
- [ ] 視覺走查：樹頁（展開／拖放灰化／刪除對話框）、樹狀選擇器（桌機 cascading／行動 sheet）、詳情麵包屑截斷、深色模式、390 寬
