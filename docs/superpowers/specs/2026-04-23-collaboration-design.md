# 協作（Collaboration）設計 — v2 子專案 #7

## 目標

讓使用者與其他使用者協作共享物品。三個子功能：
- **群組（Groups）** — 命名的使用者集合，**成員間彼此的物品互相可見（唯讀）**
- **借用（Loans）** — 記錄物品借出紀錄，對象可為站內使用者或自訂文字
- **轉移（Transfers）** — 提議將物品所有權轉給另一使用者，需對方同意

對應 v1 的 groups + loans + transfer_requests 模組之 v2 化。

## 範圍

**In scope：**
- 群組模型、成員管理（僅 owner vs member 兩種身份）
- 跨 group 的物品「讀取可見性」合流（`visible_item_owner_ids`）
- 借用 CRUD（一次至多一筆 active loan per item；borrower 可為站內 user 或純文字）
- 轉移請求流程（pending → accepted / rejected / cancelled），接受時真正變更 `items.owner_id`
- 與 #5 通知串接（轉移事件觸發 `notifications_service.emit()`）
- 物品詳細頁新增 Loan card + Transfer 按鈕 + readonly 徽章
- `/collaboration` 頁面（tabs：Groups / Transfers），以及 `/collaboration/groups/[id]` 成員管理
- i18n（zh-TW / en）、Alembic 0006、E2E flow

**Out of scope（明確延後）：**
- Group roles 超過 owner / member（admin / viewer 暫不支援）
- 成員接受邀請流程（owner 加入即加入，無 accept）
- Group-scope 過濾 UI（「只顯示群組 X 的物品」）
- Option C：group 成員的 **寫入權限**（僅唯讀可見，mutations 仍限 owner）
- 借用提醒 / 逾期自動通知（未來於 #5 emit 延伸）
- 轉移歷史時間軸（單列紀錄即可）、bulk transfer、多物件 transfer
- 外部 invite / 公開分享連結 / 電子郵件邀請
- 使用者搜尋（字首搜尋、自動補全）— 只支援精確 username 查詢

## 資料模型

### `groups`

```python
class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_groups_owner_name"),
    )
    id: UUID primary key
    owner_id: UUID FK users(id) CASCADE, indexed
    name: str(100) not null
    created_at, updated_at
    members: list[GroupMember] relationship(cascade="all, delete-orphan")
```

### `group_members`

```python
class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
    )
    id: UUID primary key
    group_id: UUID FK groups(id) CASCADE, indexed
    user_id: UUID FK users(id) CASCADE, indexed
    joined_at: datetime(tz)
```

注意：
- 建立 `Group` 時，service 層自動插入一列 `GroupMember(owner_id)`。也就是 owner 一定是 member。
- Owner 欄位在 `groups` 表保留，便於 `is_owner` 判斷不需 query 兩張表。
- 兩者同時為 FK 到 users，ondelete CASCADE：使用者帳號若刪除（未來管理員功能），連帶 group 與 membership 也會被清理。

### `item_loans`

```python
class ItemLoan(Base):
    __tablename__ = "item_loans"
    __table_args__ = (
        CheckConstraint(
            "borrower_user_id IS NOT NULL OR borrower_label IS NOT NULL",
            name="ck_loans_borrower_presence",
        ),
        Index(
            "uq_item_loans_one_active",
            "item_id",
            unique=True,
            postgresql_where=sa.text("returned_at IS NULL"),
            sqlite_where=sa.text("returned_at IS NULL"),
        ),
    )
    id: UUID primary key
    item_id: UUID FK items(id) CASCADE, indexed
    borrower_user_id: UUID FK users(id) SET NULL, nullable, indexed
    borrower_label: str(200) nullable
    lent_at: datetime(tz)
    expected_return: date nullable
    returned_at: datetime(tz) nullable, indexed
    notes: text nullable
    created_at, updated_at
```

- `item_id` CASCADE：item 被刪，loan rows 同時刪
- `borrower_user_id` SET NULL：被借方 user 帳號被刪，保留 loan 紀錄但切斷外鍵（borrower_label 可以是帳號刪除前的 username snapshot，但 YAGNI：先不自動 snapshot）
- Partial unique index 確保一個 item 只有一筆 `returned_at IS NULL` 的 loan

### `item_transfers`

```python
class ItemTransfer(Base):
    __tablename__ = "item_transfers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled')",
            name="ck_transfers_status_valid",
        ),
        Index(
            "uq_item_transfers_one_pending",
            "item_id",
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        ),
    )
    id: UUID primary key
    item_id: UUID FK items(id) CASCADE, indexed
    from_user_id: UUID FK users(id) CASCADE, indexed
    to_user_id: UUID FK users(id) CASCADE, indexed
    status: str(20) not null default 'pending'
    message: text nullable
    created_at: datetime(tz)
    resolved_at: datetime(tz) nullable
```

- 一個 item 只能有一筆 pending transfer
- `accepted`：on accept 改 `items.owner_id = to_user_id`，同時 service 確認 item 沒有 active loan
- `rejected` / `cancelled`：無副作用
- `resolved_at` 在 status 轉換為非 pending 時設定為當下 utc

## 能見度（Visibility）合流

新增 `app/services/visibility_service.py`：

```python
async def visible_item_owner_ids(
    session: AsyncSession, user_id: UUID
) -> set[UUID]:
    """回傳使用者可以讀取其 items 的 owner_id 集合 = 自己 + 所有同 group 的 member。"""
    # 1. 自己
    ids = {user_id}
    # 2. 所有以 user_id 為 member 的 group 中的 user_ids
    stmt = (
        select(GroupMember.user_id)
        .where(GroupMember.group_id.in_(
            select(GroupMember.group_id).where(GroupMember.user_id == user_id)
        ))
    )
    for row in (await session.execute(stmt)).scalars():
        ids.add(row)
    return ids
```

### items_repository + items_service 改動

- `items_repository.list_paginated(...)`：接受 `owner_ids: set[UUID]`，`where(Item.owner_id.in_(owner_ids))` 取代 `Item.owner_id == owner_id`
- `items_repository.get_owned(...)`：重新命名為 `get_visible(session, owner_ids, item_id)`（但保留 `get_owned` 給 mutations）
- `items_service`：
  - `list_items` / `get_item` 使用 `visible_item_owner_ids`
  - `update_item` / `delete_item`：維持 `get_owned(session, user.id, item_id)` — 非 owner 即使看得到也得到 404

### ItemRead schema 新增欄位

```python
class ItemRead(BaseModel):
    # … 既有欄位 …
    owner_id: UUID
    owner_username: str
```

- Repository 透過 `selectinload(Item.owner)` 取得 owner user，`ItemRead` 從 item.owner.username 取值
- 需要在 `Item` model 加 `owner: Mapped["User"] = relationship("User")`（目前只有 owner_id）

## REST API

認證：所有端點需 `Depends(get_current_user)`。

### Groups（7 endpoints）

| Method | Path | Response |
|---|---|---|
| GET | `/api/groups` | `[{id, name, owner_id, owner_username, is_owner, member_count}]` — 使用者自己擁有或加入的群組 |
| POST | `/api/groups` body `{name}` | 201 `GroupRead`；current user 自動成為 owner + 第一位 member |
| GET | `/api/groups/{group_id}` | `{..., members: [{user_id, username, joined_at}]}`；403 → 404 如非成員亦非 owner |
| PATCH | `/api/groups/{group_id}` body `{name}` | 200；僅 owner 可改 |
| DELETE | `/api/groups/{group_id}` | 204；僅 owner |
| POST | `/api/groups/{group_id}/members` body `{username}` | 201 新成員；僅 owner；404 如 username 不存在；409 如已為成員 |
| DELETE | `/api/groups/{group_id}/members/{user_id}` | 204；owner 可移除任何人（除自己）；member 可移除自己；不可移除 owner |

Owner 離開 group：先刪 group 或 transfer（transfer group ownership 為 out of scope；owner 只能刪除）。

### Loans（4 endpoints，nested 於 items）

| Method | Path | Body / Response |
|---|---|---|
| GET | `/api/items/{item_id}/loans` | `LoanRead[]`，依 `created_at DESC`；僅 item owner 可讀 |
| POST | `/api/items/{item_id}/loans` | `{borrower_username?: str, borrower_label?: str, expected_return?: date, notes?: str}` — 必須剛好提供其中一個 borrower field。409 如 item 已有 active loan。201 `LoanRead` |
| POST | `/api/items/{item_id}/loans/{loan_id}/return` | 200 `LoanRead`，`returned_at = now()` 若原為 null；否則 409 |
| DELETE | `/api/items/{item_id}/loans/{loan_id}` | 204；owner 可刪任何 loan 紀錄 |

- `borrower_username` 必須是站內有效 username，否則 422
- 允許 `borrower_username` 與 `borrower_label` 同時存在（label 作為 display，使用者指定的 user 優先）

### Transfers（5 endpoints）

| Method | Path | Body / Response |
|---|---|---|
| GET | `/api/transfers?direction=incoming\|outgoing\|both&status=pending\|resolved\|all` | `TransferRead[]`（預設 `direction=both, status=all`），依 `created_at DESC` |
| POST | `/api/transfers` | `{item_id, to_username, message?}` — 403/404 如非 item owner；422 if `to_user == from_user`；409 if item 已有 pending transfer 或 active loan。201 `TransferRead` pending；emit notification to to_user |
| POST | `/api/transfers/{id}/accept` | 200；recipient only；202 if already resolved → 409；執行：設 `items.owner_id = to_user_id`、transfer 設為 accepted、`resolved_at = now()`、emit notification 給 from_user |
| POST | `/api/transfers/{id}/reject` | 200；recipient only；409 如 non-pending |
| POST | `/api/transfers/{id}/cancel` | 200；sender only；409 如 non-pending |

錯誤：
- 非 item owner 試圖建立 transfer → 404（掩蓋 item 是否存在）
- 非 sender/recipient 試圖操作 transfer → 404
- Status transition 違規（非 pending 時 accept/reject/cancel）→ 409 with message

### 通知 payload 範本（沿用 #5 emit）

- Transfer 建立：emit to `to_user_id`；type `transfer.request`；title "{from_username} 想轉移「{item_name}」給你"；link `/collaboration?tab=transfers`
- Transfer accepted：emit to `from_user_id`；type `transfer.accepted`；title "{to_username} 已接受「{item_name}」的轉移"；link `/collaboration?tab=transfers`
- Transfer rejected / cancelled：不發通知（使用者看 UI 即可，避免 noise）

### Items API 回應 schema 變更

`ItemRead` 新增：
- `owner_id: UUID`
- `owner_username: str`

Reads (`GET /api/items`, `GET /api/items/{id}`) 會回傳其他 group 成員的物品；但若 `item.owner_id != current_user.id`，mutations（`PATCH`, `DELETE`, `POST /api/items/{id}/loans`, `POST /api/transfers`）一律拒絕。

## Web UI

### 導覽

- 主 nav 加入 `協作`（`nav.collab`，route `/collaboration`）
- `/collaboration` 以 tabs 分兩塊：`群組` / `轉移`（query param `?tab=groups|transfers`）

### `/collaboration` 索引頁

- Breadcrumb: 協作
- Tab: 群組
  - 清單：卡片列出每個群組（name、owner、我是否為 owner、member_count）
  - 右上 `[+ 新增群組]` 按鈕開 Dialog（name input）
  - 點卡片 → `/collaboration/groups/[id]`
- Tab: 轉移
  - 子 tabs: [收到 | 發出] + [等待中 | 歷史]
  - 等待中：每筆 row 顯示 item 名稱、對方、訊息、時間；
    - 收到 → `[接受] [拒絕]` 按鈕
    - 發出 → `[取消]` 按鈕
  - 歷史（accepted/rejected/cancelled）collapse 顯示

### `/collaboration/groups/[id]`

- Breadcrumb: 協作 / 群組 / {name}
- Header: group name + inline edit（owner only） + `[刪除群組]` 按鈕
- Members 清單：每行 username + joined_at + `[移除]`（owner 可移除任何人；member 可移除自己）
- `[+ 加入成員]` 按鈕開 Dialog：username input → submit → 加入或顯示錯誤

### 物品詳細頁改動（`/items/[id]`）

新增區塊：

1. 若 current user ≠ item owner：在頁首顯示徽章
   ```
   🔒 由 {owner_username} 分享（唯讀）
   ```
   並隱藏 `[編輯]` `[刪除]` 按鈕
2. **Loan card**（僅 owner 看得到）
   - 有 active loan：顯示 borrower、lent_at、expected_return、notes + `[歸還]` 按鈕
   - 無 active loan：顯示 `[新增借用]` 按鈕開 Dialog（borrower 輸入：可選 toggle user/label、選填日期、備註）
   - Collapse 「歷史紀錄」列出 returned loans
3. **Transfer 按鈕**（僅 owner，無 active loan 且無 pending transfer 時可見）
   - 開 Dialog：recipient username + message → `[送出請求]`
4. 若 item 有 pending transfer outgoing：顯示 "等待 {to_username} 接受" + `[取消]` 按鈕

### 文件結構（前端）

新增：
- `apps/web/app/(app)/collaboration/page.tsx`
- `apps/web/app/(app)/collaboration/groups/[id]/page.tsx`
- `apps/web/components/collaboration/group-card.tsx` + test
- `apps/web/components/collaboration/new-group-dialog.tsx`
- `apps/web/components/collaboration/add-member-dialog.tsx`
- `apps/web/components/collaboration/loan-card.tsx` + test
- `apps/web/components/collaboration/new-loan-dialog.tsx`
- `apps/web/components/collaboration/transfer-card.tsx`
- `apps/web/components/collaboration/new-transfer-dialog.tsx`
- `apps/web/components/collaboration/readonly-badge.tsx`
- `apps/web/lib/api/groups.ts`
- `apps/web/lib/api/loans.ts`
- `apps/web/lib/api/transfers.ts`
- `apps/web/lib/hooks/use-groups.ts`
- `apps/web/lib/hooks/use-loans.ts`
- `apps/web/lib/hooks/use-transfers.ts`

Modify：
- `apps/web/app/(app)/items/[id]/page.tsx`：掛入 Loan card、Transfer button、readonly badge
- `apps/web/components/shell/nav-items.ts`：新增 `collab` entry

### i18n 新增鍵

```
nav.collab
collab.title
collab.tabs.groups
collab.tabs.transfers
collab.groups.new
collab.groups.empty
collab.groups.memberCount
collab.groups.youAreOwner
collab.groups.detail.addMember
collab.groups.detail.removeMember
collab.groups.detail.confirmRemove
collab.groups.detail.delete
collab.groups.detail.leave
collab.transfers.tabs.incoming
collab.transfers.tabs.outgoing
collab.transfers.tabs.pending
collab.transfers.tabs.history
collab.transfers.actions.accept
collab.transfers.actions.reject
collab.transfers.actions.cancel
collab.transfers.message.placeholder
collab.loan.card.title
collab.loan.card.borrowerLabel
collab.loan.card.active
collab.loan.card.history
collab.loan.actions.new
collab.loan.actions.return
collab.loan.actions.delete
collab.loan.new.borrowerUser
collab.loan.new.borrowerLabel
collab.loan.new.expectedReturn
collab.loan.new.notes
collab.transfer.actions.new
collab.transfer.new.toUsername
collab.transfer.new.message
collab.readonly.sharedBy
collab.pending.awaiting
collab.errors.userNotFound
collab.errors.alreadyMember
collab.errors.activeLoanExists
collab.errors.pendingTransferExists
collab.errors.itemHasActiveLoan
collab.errors.selfTransfer
```

### React Query key 設計

- `["groups", "index"]`、`["groups", "detail", groupId]`
- `["loans", itemId]`（item 借用歷史）
- `["transfers", "index", { direction, status }]`
- 每次 mutation 以最小集合 invalidate（例如 accept transfer → invalidate `["transfers"]` 與 `["items"]`）

## 錯誤處理

- 所有 cross-owner / 404 一致採 `404 Not Found`，不揭示物件存在性
- 409：state conflict（active loan、pending transfer、already member、already resolved）
- 422：validation（self-transfer、非 exact username、both/neither borrower 欄位、status transition 無效）
- 接受 transfer 時，service 先檢查 `item.owner_id == transfer.from_user_id` 仍為真（否則舉 409：the item was transferred again / deleted）

## 遷移（Alembic 0006）

單一 migration 建立 4 張表（groups、group_members、item_loans、item_transfers）+ indexes + check constraints。降級 drop 順序反向。

## 測試策略

### 後端（~60 個新測試）

- `test_group_models_smoke.py` (2)：model create + cascade delete
- `test_loan_model_smoke.py` (2)：model create + borrower check constraint
- `test_transfer_model_smoke.py` (2)：model create + status check
- `test_groups_repository.py` (6)：CRUD + list (owner/member) + members add/remove + unique (owner,name)
- `test_loans_repository.py` (6)：CRUD + active uniqueness + return + list history + borrower variants
- `test_transfers_repository.py` (6)：CRUD + unique pending + list by direction + status transitions
- `test_visibility_service.py` (4)：own + group members + empty group + multiple groups union
- `test_groups_service.py` (4)：owner auto-member; rename owner-only; remove-self vs remove-other rules; non-owner cannot invite
- `test_loans_service.py` (6)：borrower exactly-one validation; username → user_id lookup; existing active → 409
- `test_transfers_service.py` (6)：accept flips owner_id; reject doesn't; cancel doesn't; self-transfer 422; pending-not-found 409; active-loan blocks 409
- `test_groups_routes.py` (6)：all 7 endpoints + auth
- `test_loans_routes.py` (5)：all 4 endpoints + auth
- `test_transfers_routes.py` (6)：all 5 endpoints + cross-owner 404 + notification emitted (inspect `GET /api/notifications` of recipient)
- `test_items_visibility.py` (4)：owner sees own; member sees group owner's items read-only; non-member doesn't see; group owner can still edit; non-owner update returns 404

Adjustments to existing tests: `test_items_routes.py` 既有斷言 `ItemRead.owner_*` 可能新增；需補 `owner_username` 欄位到 smoke。

### 前端 vitest（~6 個）

- `group-card.test.tsx`：name + member count + owner badge
- `loan-card.test.tsx`：active state (borrower + dates) + return button; empty state
- `transfer-card.test.tsx`：incoming pending shows accept/reject; outgoing pending shows cancel; resolved shows status

### E2E（`apps/web/tests/collaboration.spec.ts`）

核心 flow：
1. Register two users alice + bob；alice create item；alice create group; add bob
2. Bob logs in → `/items` 看到 alice 的 item 帶 readonly 徽章；點進去看不到 edit / delete 按鈕
3. Alice lends item to bob via loan dialog (username = bob) → loan card shows active → return
4. Alice creates transfer to bob → bob's 通知 bell 增加；bob 去 `/collaboration?tab=transfers` → accept
5. Bob 的 items 現在 owner 改為 bob（alice 看不到了，除非還在同 group）

## 成功指標

- 兩名使用者可建立 group + 彼此可見對方 items（readonly）
- Lender 可以建立 loan、標示歸還、查歷史
- Sender/Recipient 可以走完 transfer pending → accepted 並真正轉移 item 擁有權
- `/collaboration` 頁 tabs 正常運作
- API 測試 223 + 60 ≈ 283 全綠；web typecheck / vitest / build 全綠
- `/collaboration`、`/collaboration/groups/[id]` 出現於 build output
