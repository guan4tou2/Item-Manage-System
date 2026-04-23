# 清單類（Lists）設計 — v2 子專案 #6

## 目標

提供使用者自訂的**命名清單**（旅行打包、購物、收藏、通用），每份清單含有序條目（可勾選完成）。對應 v1 的 travels + shopping_lists 模組，拿掉協作（assignee/visibility/shared_with/groups）相關欄位，並合併為單一資料表以降低複雜度。

## 範圍

**In scope：**
- 單一 `lists` + `list_entries` 模型，由 `kind` discriminator 區分類型
- 四種 kind：`travel` | `shopping` | `collection` | `generic`；kind 僅影響前端顯示，不影響後端儲存邏輯
- 10 支 REST endpoints（清單 CRUD + 條目 CRUD + 切換完成 + 重排）
- `/lists` 索引頁（依 kind 分組的卡片）與 `/lists/[id]` 詳細頁
- 新清單 dialog、條目增刪改、drag-to-reorder、toggle done、刪除清單（含確認）
- i18n（zh-TW、en）、Alembic 0005、E2E flow

**Out of scope（明確延後）：**
- Inventory-linking（條目 FK 至 `items.id`）— 未來迭代
- Groups / sections（子節 heading）— 未來迭代
- Assignee / visibility / shared_with — #7 協作
- Templates（預設旅行/購物清單模板）— 未來迭代
- Store / priority / 標籤 on entries — 未來迭代
- 通知觸發（例如超出預算、旅行接近）— 之後呼叫 #5 `emit()` 擴充，#6 不負責

## 資料模型

### `lists`

```python
class List(Base):
    __tablename__ = "lists"

    id: UUID primary key
    owner_id: UUID FK users(id) ON DELETE CASCADE, indexed
    kind: str(20) not null
        # "travel" | "shopping" | "collection" | "generic"
    title: str(120) not null
    description: text nullable
    # kind-specific optional fields
    start_date: date nullable          # 通常用於 travel
    end_date: date nullable            # 通常用於 travel
    budget: Numeric(12, 2) nullable    # 通常用於 shopping
    created_at: datetime(tz) not null
    updated_at: datetime(tz) not null, onupdate

    entries: list[ListEntry] = relationship(cascade="all, delete-orphan")
```

約束：
- `CheckConstraint("kind IN ('travel','shopping','collection','generic')", name="ck_lists_kind_valid")`
- `CheckConstraint("budget IS NULL OR budget >= 0", name="ck_lists_budget_nonneg")`
- `CheckConstraint("start_date IS NULL OR end_date IS NULL OR end_date >= start_date", name="ck_lists_date_order")`

### `list_entries`

```python
class ListEntry(Base):
    __tablename__ = "list_entries"

    id: UUID primary key
    list_id: UUID FK lists(id) ON DELETE CASCADE, indexed
    position: Integer not null, default 0
    name: str(200) not null
    quantity: Integer nullable
    note: text nullable
    price: Numeric(12, 2) nullable     # 通常用於 shopping
    link: str(500) nullable            # 通常用於 shopping
    is_done: Boolean not null, default False
    created_at: datetime(tz) not null
    updated_at: datetime(tz) not null, onupdate
```

約束：
- `CheckConstraint("position >= 0", name="ck_list_entries_position_nonneg")`
- `CheckConstraint("quantity IS NULL OR quantity >= 1", name="ck_list_entries_quantity_positive")`
- `CheckConstraint("price IS NULL OR price >= 0", name="ck_list_entries_price_nonneg")`

Index：`(list_id, position)` 複合索引，支援依序查詢。

**設計決定：**
- **單表 + kind discriminator**：避免 travel_lists/shopping_lists/... 三表雷同的 CRUD 重複；kind 幾乎不影響後端邏輯，僅限制前端顯示與 i18n 分組。
- **Free-text entries**：不 FK inventory — `name` 是 plain string。未來加 `item_id` 可選 FK 即可。
- **Owner-scoped + hard delete**：與 items/categories/locations 一致；沒有 soft-delete，避免 list vs entry 兩層 soft-delete 的 UX 糾結。
- **Entry ordering via `position` column**：簡單；reorder 時整批 rewrite 位置，小集合足夠快。
- **UUIDs 於 list + list_entry**：符合 v2 物品/通知的 ID 慣例。

## REST API

所有端點需認證。路由 prefix `/api/lists`；條目端點巢狀於清單之下。

| Method | Path | Query / Body | Response |
|--------|------|--------------|----------|
| GET | `/api/lists` | `kind?`, `limit: int = 20 (1-100)`, `offset: int = 0` | `{ items: ListSummary[], total: int }` |
| POST | `/api/lists` | `ListCreate` body | `ListRead`（201） |
| GET | `/api/lists/{list_id}` | — | `ListDetail`（含 entries）|
| PATCH | `/api/lists/{list_id}` | `ListUpdate` body | `ListRead` |
| DELETE | `/api/lists/{list_id}` | — | `204` |
| POST | `/api/lists/{list_id}/entries` | `ListEntryCreate` | `ListEntryRead`（201；position 自動設為當前最大+1 若省略）|
| PATCH | `/api/lists/{list_id}/entries/{entry_id}` | `ListEntryUpdate` | `ListEntryRead` |
| POST | `/api/lists/{list_id}/entries/{entry_id}/toggle` | — | `ListEntryRead`（翻轉 is_done）|
| POST | `/api/lists/{list_id}/entries/reorder` | `{ entry_ids: UUID[] }` | `204`；所有提供的 id 需屬於該 list，position 按陣列順序寫入 0, 1, 2…；若缺漏任一 entry 的 id → 422 |
| DELETE | `/api/lists/{list_id}/entries/{entry_id}` | — | `204` |

Schema 詳情：
```python
class ListSummary(BaseModel):
    id: UUID
    kind: str
    title: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: Optional[Decimal]
    entry_count: int
    done_count: int
    created_at: datetime
    updated_at: datetime

class ListRead(ListSummary):
    pass  # 結構相同

class ListDetail(ListSummary):
    entries: list[ListEntryRead]

class ListCreate(BaseModel):
    kind: Literal["travel", "shopping", "collection", "generic"]
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)

class ListUpdate(BaseModel):
    kind: Optional[Literal[...]] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)
    model_config = ConfigDict(extra="forbid")

class ListEntryRead(BaseModel):
    id: UUID
    list_id: UUID
    position: int
    name: str
    quantity: Optional[int]
    note: Optional[str]
    price: Optional[Decimal]
    link: Optional[str]
    is_done: bool
    created_at: datetime
    updated_at: datetime

class ListEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    position: Optional[int] = Field(default=None, ge=0)
    quantity: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    link: Optional[str] = Field(default=None, max_length=500)
    is_done: bool = False

class ListEntryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    link: Optional[str] = Field(default=None, max_length=500)
    is_done: Optional[bool] = None
    model_config = ConfigDict(extra="forbid")

class ReorderRequest(BaseModel):
    entry_ids: list[UUID]
```

跨使用者存取 → 404。所有 nested route 若 `list_id` 的 owner 不是當前使用者 → 404（不先認 entry）。

`end_date < start_date` → 422（來自 DB check constraint，也在 service 層提前驗證回 422）。

## Web UI

### `/lists` 索引頁

```
Breadcrumb: 清單
h1 清單 ───────────────── [+ 新增清單]

Filter chips: [全部]  [旅行]  [購物]  [收藏]  [通用]

── 旅行 ──────────────────────
┌──────────────────┐  ┌──────────────────┐
│ 日本九州 10 天    │  │ 週末露營          │
│ 3/15 – 3/25      │  │ 4/12 – 4/14      │
│ 12 項 · 3 已完成  │  │ 25 項 · 10 已完成 │
└──────────────────┘  └──────────────────┘

── 購物 ──────────────────────
┌──────────────────┐
│ 生日禮物          │
│ 預算 $2,000       │
│ 5 項 · 2 已完成   │
└──────────────────┘

（若某 kind 無清單則該分組不顯示）

若完全無清單: EmptyState + [建立第一份清單]
```

### 新增清單 dialog

shadcn `Dialog`：Kind select (4 options with icon/label) + title input + optional description → `Create` 按鈕。成功後 push `/lists/[id]`。

### `/lists/[id]` 詳細頁

```
Breadcrumb: 清單 / <title>

h1 <inline editable title>          [kind badge]   [⋮]
description (optional, inline editable)

── kind-specific panel ──
travel:    start/end date pickers、進度條（done/total）
shopping:  predicted spend = sum(price * qty) of done entries、budget
           → 若 > budget 顯示紅字警告
collection/generic: 無 panel（或只顯示 entry 統計）

── Entries ──
[drag] ☐ 便當盒         1    /items note…   [×]
[drag] ☑ 牙刷                              [×]
[drag] ☐ 登山鞋          2                  [×]

+ add entry ________________________ [Enter 新增]
```

條目列 row 行為：
- click checkbox 或 toggle button → optimistic update + `POST .../toggle`
- click delete icon → optimistic remove + `DELETE`
- drag handle → reorder；釋放後 `POST .../reorder` with full id 序列
- click name 進入 inline edit（Enter 儲存、Escape 取消）；其他欄位（qty、note、price、link）若該 kind 支援，透過小 popover 或 row 的展開狀態編輯

底部 `[Delete list]`：彈 `AlertDialog` 確認 → `DELETE /api/lists/{id}` → push `/lists`.

空清單：`尚無項目` + 提示可在下方輸入。

### 元件拆分

- `list-card.tsx` — 索引頁使用，顯示 kind badge + title + kind-specific meta + entry 計數
- `list-card.test.tsx`
- `list-entry-row.tsx` — 詳細頁列項
- `list-entry-row.test.tsx`
- `new-list-dialog.tsx` — 新增 dialog
- `kind-badge.tsx` — 視覺化 kind + 圖示
- `list-kind-filter.tsx` — 索引頁的 filter chips（含 `全部` 以及 4 個 kind）

### Drag-to-reorder

使用 `@dnd-kit/core` + `@dnd-kit/sortable`（shadcn 官方建議）：
- 拖曳中使用 keyboard sensor（Space 選取 / Arrow 移動 / Space 放下）以符合 a11y
- drop 後觸發 `reorderMutation({ entry_ids })`；失敗 rollback + toast
- 若未來決定使用 CSS-only sortable, 可替換但接口不變

### i18n 新增鍵

```
nav.lists (已存在)
lists.title: "清單" / "Lists"
lists.actions.newList: "新增清單"
lists.actions.delete: "刪除清單"
lists.actions.confirmDelete: "確定刪除此清單?"
lists.actions.confirmDeleteBody: "清單與所有項目將被永久刪除。"
lists.filter.all: "全部"
lists.kind.travel: "旅行"
lists.kind.shopping: "購物"
lists.kind.collection: "收藏"
lists.kind.generic: "通用"
lists.new.titlePlaceholder: "清單名稱…"
lists.new.descriptionPlaceholder: "描述（選填）"
lists.new.kindLabel: "類型"
lists.new.create: "建立"
lists.detail.entryCount: "{count} 項 · {done} 已完成"
lists.detail.budget: "預算 ${amount}"
lists.detail.spent: "已花 ${amount}"
lists.detail.overBudget: "超出預算 ${amount}"
lists.detail.dateRange: "{start} – {end}"
lists.empty.title: "尚無清單"
lists.empty.cta: "建立第一份清單"
lists.entry.empty: "尚無項目"
lists.entry.placeholder: "輸入項目名稱，按 Enter 新增"
lists.entry.fieldQty: "數量"
lists.entry.fieldPrice: "價格"
lists.entry.fieldLink: "連結"
lists.entry.fieldNote: "備註"
```

### React Query hook

`apps/web/lib/hooks/use-lists.ts` 輸出：
- `useLists(params)` — 列表 with entry_count
- `useList(listId)` — 單一清單含 entries
- `useCreateList()`
- `useUpdateList()`
- `useDeleteList()`
- `useCreateEntry(listId)`
- `useUpdateEntry(listId)`
- `useToggleEntry(listId)` — 使用 optimistic update flipping `is_done` locally before network
- `useDeleteEntry(listId)` — optimistic remove
- `useReorderEntries(listId)` — optimistic reorder (apply new order locally, rollback on fail)

所有 mutation 成功時 `invalidateQueries(["lists"])`；對 detail 頁另需 `invalidateQueries(["lists", listId])`.

## 錯誤處理

- 跨使用者存取（list_id 不屬於當前 user）→ 404
- Entry 不存在（但 list 屬於 user） → 404
- Reorder payload 缺漏任一 entry id 或含不屬於該 list 的 id → 422
- Date 倒序 `end_date < start_date` → 422
- 所有 mutation 失敗 → toast + rollback optimistic

## 遷移（Alembic 0005）

```python
def upgrade():
    op.create_table(
        "lists",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("owner_id", GUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('travel','shopping','collection','generic')", name="ck_lists_kind_valid"),
        sa.CheckConstraint("budget IS NULL OR budget >= 0", name="ck_lists_budget_nonneg"),
        sa.CheckConstraint("start_date IS NULL OR end_date IS NULL OR end_date >= start_date", name="ck_lists_date_order"),
    )
    op.create_index("ix_lists_owner_id", "lists", ["owner_id"])

    op.create_table(
        "list_entries",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("list_id", GUID, sa.ForeignKey("lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("is_done", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("position >= 0", name="ck_list_entries_position_nonneg"),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 1", name="ck_list_entries_quantity_positive"),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_list_entries_price_nonneg"),
    )
    op.create_index("ix_list_entries_list_id_position", "list_entries", ["list_id", "position"])
```

Downgrade: drop tables in reverse order.

## 測試

### 後端（預計 30 個新測試）

`tests/test_lists_repository.py`:
- Lists CRUD (create/list/get/update/delete) owner-scoped
- List listing with kind filter
- entry_count + done_count 計算正確
- Cascade delete 刪除清單時連同 entries

`tests/test_list_entries_repository.py`:
- Entry create (auto position = max+1)
- Entry update / toggle / delete
- Reorder: 全部提供 → rewrite positions; 缺漏 → ValueError
- Cross-list protection: entry_id 屬於別的 list → None

`tests/test_lists_service.py`:
- Kind validation (invalid string → HTTPException 422)
- Date order validation
- Budget nonneg
- Reorder validation (fewer ids → 422)

`tests/test_lists_routes.py`:
- All 10 endpoints
- Auth required
- Cross-owner 404 (list + entry)
- Toggle idempotency
- Pagination

### 前端 vitest（4 新測試）

- `list-card.test.tsx` — 顯示 title + entry_count + done_count + kind badge; budget formatting
- `list-entry-row.test.tsx` — checkbox click → onToggle(entry.id); delete click → onDelete; 顯示 qty/price/note 當非空

### E2E（`apps/web/tests/lists.spec.ts`）

1. 登入 → `/lists` → 空狀態 → 點建立 → 選 `shopping` kind + 輸入 title → 跳轉 detail
2. 新增兩個 entries → 勾選一個 → 顯示 `2 項 · 1 已完成`
3. Reorder（透過 keyboard）→ 順序反映
4. 刪除 entry → 減少一個
5. 返回 index → 看到 shopping 分組下的 card
6. 刪除清單 → 確認 → index 空

## 成功指標

- 使用者可建立/編輯/刪除清單
- 清單詳細頁條目可增刪改、勾選、重排序
- 索引頁依 kind 分組、可過濾
- v2 既有測試維持綠燈；新增 ~30 後端測試 + 4 前端 vitest + 6 E2E 場景
- 全站 typecheck + build 無錯；`/lists` 與 `/lists/[id]` 出現於路由列表
