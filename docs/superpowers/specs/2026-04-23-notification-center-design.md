# 通知中心（Notification Center）設計 — v2 子專案 #5

## 目標

為使用者提供**站內通知收件匣**（in-app inbox），取代 v1 Flask notifications 模組的「收件匣」體驗。外部管道（Email/LINE/Telegram/Web Push）與借用/歸還觸發條件不在本子專案範圍。

## 範圍

**In scope：**
- `Notification` 資料表、Repository、Service、REST 路由（5 支）
- 通用 `emit(user, type, title, body, link)` 服務，作為後續子專案接通通知的單一擴充點
- 生產者（producers）：
  - 低庫存提醒（需新增 Item `min_quantity` 欄位）
  - 註冊歡迎訊息（welcome）
- 前端 `/notifications` 頁面、header 鈴鐺 badge、nav 連結
- i18n（zh-TW 為主；en 補翻譯鍵，通知內容以 zh-TW 字面字串儲存）
- Alembic migration

**Out of scope（明確延後）：**
- Email / LINE / Telegram / Web Push 發送 — 各外部管道整合後續各自處理；Web Push 隨 #9 PWA
- 借用/歸還觸發 — #7 協作 完成後呼叫 `emit()`
- 到期 / 保養 / 更換觸發 — 需要 Item `expiration_date`、`replacement_interval` 等欄位，v2 尚未引入
- 通知偏好 / opt-out（per-type subscriptions）
- 管理員廣播 UI
- 通知內容的動態 i18n（template key + params 渲染）— 目前僅以 zh-TW 字面字串儲存

## 資料模型

```python
class Notification(Base):
    __tablename__ = "notifications"

    id: UUID primary key
    user_id: UUID FK users(id) ON DELETE CASCADE, indexed
    type: str(40) not null            # "low_stock" | "system.welcome" | 之後： "loan.due" 等
    title: str(200) not null          # 後端以 zh-TW 字面字串渲染
    body: text nullable
    link: str(500) nullable           # 前端相對路由，例：/items/{id}
    read_at: datetime(tz) nullable    # null = 未讀
    created_at: datetime(tz) not null, indexed desc
```

設計決定：
- **硬刪除（hard delete）**：無 `is_deleted` soft-delete。通知是使用者收件匣的即時訊息；刪除就是刪除。
- **無保留上限 / 自動清除**：YAGNI；若未來出現效能問題再加 cron 清除。
- **字面字串儲存，非 template key**：後端於 `emit()` 時直接渲染 zh-TW 字串。改語系不會 re-translate 既有通知。此決定換簡單性，後續若需多語通知再改 schema（加 `template_key` + `params JSON`）。
- **`read_at` 而非 `is_read`**：保留已讀時間資訊，便於未來統計。

### Item 新增欄位

```python
# app/models/item.py
min_quantity: Mapped[Optional[int]] = mapped_column(
    Integer, nullable=True, default=None
)
```

- nullable：預設關閉低庫存提醒
- 配合新增 `CheckConstraint("min_quantity IS NULL OR min_quantity >= 0")`
- schema 同步加入 `min_quantity: int | None` 於 `ItemCreate`、`ItemUpdate`、`ItemRead`

## REST API

所有端點需認證（`Depends(get_current_user)`），作用於目前使用者之通知。

| Method | Path | Body / Query | Response |
|--------|------|--------------|----------|
| GET | `/api/notifications` | `unread_only: bool = false`, `limit: int = 20 (1-100)`, `offset: int = 0` | `{ items: Notification[], total: int, unread_count: int }` |
| GET | `/api/notifications/unread-count` | — | `{ count: int }` |
| PATCH | `/api/notifications/{id}/read` | — | `Notification`（200；已讀則保持原 `read_at` 不動）|
| POST | `/api/notifications/mark-all-read` | — | `{ marked: int }` |
| DELETE | `/api/notifications/{id}` | — | `204` |

- 跨使用者存取（`user_id` 不符）→ 404（避免資訊外洩 vs. 403）
- `limit` 上限 100；預設 20
- 排序固定 `created_at DESC`

## 通用 emit 服務

```python
# app/services/notifications_service.py
async def emit(
    session: AsyncSession,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification | None:
    """建立一則通知。失敗（例如 DB error）不會 propagate — 回傳 None 並 log。"""
```

- **失敗吞噬**：`emit()` 內部包裹 `try/except`。若 insert 失敗，回傳 `None` 並寫 `logger.warning`。**觸發方（例如 `items_service.update_item`）不應因通知失敗而回滾主交易。** 此決定的取捨：使用者偶爾漏收通知可接受；物品更新失敗則是資料完整性問題。
- 不做頻率限制（rate-limit）、不做去重（dedup）— 生產者自行判斷是否該呼叫。

## 生產者（Producers）

### 1. 低庫存（`low_stock`）

位置：`items_service.update_item`（以及 `create_item`，若初始 quantity 即低於 `min_quantity`）

邏輯：
```python
# pseudocode
if item.min_quantity is not None and item.min_quantity > 0:
    was_above = (old_quantity > item.min_quantity)
    now_below = (new_quantity <= item.min_quantity)
    if was_above and now_below:
        await notifications_service.emit(
            session,
            user_id=item.owner_id,
            type="low_stock",
            title=f"「{item.name}」庫存不足",
            body=f"目前數量：{new_quantity}，提醒閾值：{item.min_quantity}",
            link=f"/items/{item.id}",
        )
```

- **僅在「跨越」閾值時觸發**：持續低於不會重複提醒；若補充後再度跌落才重新觸發
- `create_item` 特例：`old_quantity` 視為 `+∞`（即只看 `new_quantity <= min_quantity` 是否成立）
- 若使用者修改 `min_quantity` 使 item 瞬間變成低於，是否觸發？→ **不觸發**（只在 quantity 變動時才看跨越）。YAGNI，使用者可手動補。

### 2. 歡迎訊息（`system.welcome`）

位置：`routes/auth.py` 的 register 端點（成功建立 user 後、回傳前）

```python
await notifications_service.emit(
    session,
    user_id=new_user.id,
    type="system.welcome",
    title="歡迎使用 IMS",
    body="從儀表板開始管理你的物品吧。",
    link="/dashboard",
)
```

## 前端

### 路由結構

- `apps/web/app/(app)/notifications/page.tsx` — 通知列表頁
- Header：`apps/web/components/shell/notification-bell.tsx` 掛入 `components/shell/header.tsx`
- Nav：`components/shell/nav-items.ts` 加入 `notifications` key，路由 `/notifications`

### 通知列表頁

```
Breadcrumb: 儀表板 / 通知

h1 通知 ──────────────── [全部標為已讀]

Tabs: [全部] [未讀]
──────────────────────────────────
[icon] 「便當盒」庫存不足              [✕]
       目前數量：1，提醒閾值：2
       3 分鐘前
──────────────────────────────────
[icon] 歡迎使用 IMS                   [✕]
       從儀表板開始管理你的物品吧。
       2 小時前
──────────────────────────────────
（分頁：若 total > 20 顯示「載入更多」）
```

- 未讀項目左側顯示深色圓點（`● title`）；已讀項目灰階
- 整個 row 可點擊：觸發 `markAsRead(id)`（若未讀）+ `router.push(link)`（若有 `link`）
- 刪除按鈕：`✕` icon，optimistic update，失敗 rollback + toast
- Empty state：`尚無通知` + 小 CTA「前往儀表板查看摘要」
- Loading：skeleton（3 個 row）
- Error：簡單錯誤訊息 + 重試按鈕

### Notification bell（header）

- `apps/web/components/shell/notification-bell.tsx`
- 鈴鐺 icon（lucide `Bell`），右上小 badge 顯示 `unread_count`
  - `unread_count === 0`：不顯示 badge
  - `1..99`：顯示數字
  - `> 99`：顯示 `99+`
- 使用 `useUnreadCount()` React Query：`staleTime: 30_000`, `refetchOnWindowFocus: true`, `refetchInterval: 60_000`
- 點擊 → `router.push("/notifications")`
- a11y：`aria-label={t("nav.notifications")}` + `aria-live="polite"` for badge

### React Query hooks（`apps/web/lib/hooks/use-notifications.ts`）

- `useNotifications({ unreadOnly, limit, offset })` — 列表
- `useUnreadCount()` — 純計數，給鈴鐺
- `useMarkNotificationRead()` — mutation，成功時 `invalidateQueries(["notifications"])`
- `useMarkAllNotificationsRead()` — mutation
- `useDeleteNotification()` — mutation

### i18n（messages/zh-TW.json + en.json）

新增鍵：
- `nav.notifications` → `通知` / `Notifications`
- `notifications.title` → `通知` / `Notifications`
- `notifications.filters.all` → `全部` / `All`
- `notifications.filters.unread` → `未讀` / `Unread`
- `notifications.actions.markRead` → `標為已讀` / `Mark read`
- `notifications.actions.markAllRead` → `全部標為已讀` / `Mark all read`
- `notifications.actions.delete` → `刪除` / `Delete`
- `notifications.empty.title` → `尚無通知` / `No notifications yet`
- `notifications.empty.cta` → `前往儀表板` / `Go to dashboard`
- `notifications.loadMore` → `載入更多` / `Load more`

## 測試

### 後端

- `tests/test_notifications_repository.py`
  - create、list（分頁、`unread_only`、order by `created_at DESC`）、unread_count、mark_read（冪等）、mark_all_read 回傳筆數、delete、owner 隔離
- `tests/test_notifications_service.py`
  - `emit()` 建立一列；異常路徑：session.add 失敗時回傳 `None` + 不 raise（以 monkeypatch 觸發）
- `tests/test_notifications_integration.py`
  - 低庫存：set `min_quantity=2`, quantity 5→1 ⇒ 1 通知；再 1→0 ⇒ 仍僅 1 通知（未跨越）；補 0→5 後再 5→1 ⇒ 共 2 通知
  - 低庫存：create 初始 quantity=1、min_quantity=2 ⇒ 1 通知
  - Welcome：register 成功 ⇒ unread_count=1
- `tests/test_notifications_routes.py`
  - 所有 5 支端點的 auth、happy path、owner 隔離（其他使用者的 id → 404）

### 前端

- `components/notifications/notification-item.test.tsx`：render 基本欄位、unread dot、click 觸發 onRead + onNavigate
- `components/shell/notification-bell.test.tsx`：無 count 不顯示 badge、count=5 顯示 5、count=150 顯示 99+
- `tests/notifications.spec.ts`（Playwright E2E）：
  1. Register 新使用者 → header 鈴鐺顯示 `1` → 點擊 → `/notifications` 顯示「歡迎」→ 標為已讀後 `0`
  2. 透過 API 建立 item min_quantity=2 quantity=5 → PATCH quantity=1 → 重整頁面 → 鈴鐺顯示 `1` 且 `/notifications` 列出「庫存不足」
  3. 「全部標為已讀」→ 未讀 tab 清空
  4. 刪除一則通知 → 列表少一項

## 錯誤處理

- 所有路由使用既有的 `get_db` + `get_current_user` 依賴鏈
- 跨使用者 GET/PATCH/DELETE → 404（不揭示通知是否存在）
- `DELETE /api/notifications/{id}`：
  - 找不到 → 404
  - 找到但 owner 不符 → 404
  - 成功 → 204
- 前端 mutations：
  - Optimistic updates（mark-read、delete）
  - 失敗時 rollback + toast 提示
  - `useNotifications` 失敗時顯示錯誤 card + 重試按鈕

## 遷移（Alembic）

單一 migration 檔案，同時處理兩項變更：

```python
def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", [sa.text("created_at DESC")])

    op.add_column(
        "items",
        sa.Column("min_quantity", sa.Integer, nullable=True),
    )
    op.create_check_constraint(
        "ck_items_min_quantity_nonneg",
        "items",
        "min_quantity IS NULL OR min_quantity >= 0",
    )

def downgrade():
    op.drop_constraint("ck_items_min_quantity_nonneg", "items", type_="check")
    op.drop_column("items", "min_quantity")
    op.drop_index("ix_notifications_created_at", "notifications")
    op.drop_index("ix_notifications_user_id", "notifications")
    op.drop_table("notifications")
```

## 成功指標

- 新使用者註冊後，即能在 `/notifications` 看到歡迎訊息，header 鈴鐺顯示 `1`
- Item 設置 `min_quantity` 後，quantity 跨越閾值時產生一則 `low_stock` 通知；未跨越（已低於仍繼續下降）不重複提醒
- 通知可標為已讀、全部標為已讀、刪除
- 鈴鐺 badge 在 30 秒 stale time 內自動更新；page focus 時立即 refetch
- 所有既有測試維持綠燈；新增約 20 個後端測試 + 4 個前端 vitest + 4 個 E2E 場景
