# Phase 30 — 成員權限細化 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 30＋§5.5「viewer 家人旅程」＋§5.4 狀態契約＋§5.7 響應式；測試計畫 `docs/plans/2026-10-15-eng-review-test-plan.md`（`/settings`（管理群組）成員角色指派）。
> 本 phase **有 migration**：`0022_group_member_roles`（`group_members.role`＋CHECK＋backfill）。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**；完成即 commit（Conventional Commits，繁中 body）。

**Goal：** 群組成員角色細化為 `owner / admin / editor / viewer`（owner 事實來源維持 `groups.owner_id`；`group_members.role` 新增 `admin | editor | viewer`，既有成員 backfill `editor`）——新增 **viewer＝唯讀帳號**（適合家人只查不修改；編輯入口一律不渲染、403 為後端防線）＋ **admin 取得群組管理權**（改名、加成員、指派角色；owner 不可被變更／移除）；角色變更寫 audit log。

**Architecture：** 權限判定集中兩處——`visibility_service`（唯讀帳號判定 `read_only_user_ids`／`is_read_only`＋`UserPublic.is_read_only` 組裝）與 `groups_service`（群組管理權 `_ensure_managed`）。唯讀寫入防線以 **`WriterGuardRoute`**（`APIRoute` 子類；僅對非 GET/HEAD/OPTIONS 自動掛 `require_writer` 依賴）套用於庫存／taxonomy 域 routers，`groups` 因「離開群組需對所有角色開放」不套 router guard 而於 service 內個別檢查。Web 端以 `useReadOnly()`（auth store `user.is_read_only`）＋ `<EditableOnly>` 統一「不渲染」策略；一次性 viewer banner 狀態存 `users.preferences.viewer_notice_dismissed`（server-side）。

**Tech Stack：** FastAPI（`APIRoute` 子類、`Literal` role schema、pydantic response_model 進 openapi）、SQLAlchemy async＋Alembic（add_column＋check constraint）、pytest（SQLite in-memory）、React Query、zustand（既有 auth store）、next-intl、shadcn/ui（`Badge`／`Select`／`Card`／`Alert`）、Vitest、Playwright。

**關鍵既有資產（重用，勿重造）：**
- 模型／migration：`apps/api/app/models/group.py`（`Group`＋`GroupMember`；owner 建群時會寫入自身 member row）、`apps/api/alembic/versions/0006_collaboration.py`、`0021_item_cost.py`（add column＋check 範式）
- 權限現況：`apps/api/app/services/visibility_service.py`（`visible_item_owner_ids`）、`groups_service.py`（`_ensure_visible`／`_ensure_owned`）、`groups_repository.py`（`create`（owner 亦建 member row）／`get_for_member`／`list_for_user`）
- 稽核：`apps/api/app/services/audit_service.py`（`log()` **自帶 commit** → 於交易完成後呼叫）
- 偏好：`apps/api/app/schemas/preferences.py`（`extra="allow"`）＋`preferences_service.update_preferences`（`{**current, **incoming}` **merge 語意**）
- 使用者輸出：`UserPublic`（`apps/api/app/schemas/user.py`）於 `routes/auth.py`（login／register／me／bootstrap）與 `routes/users.py`（me GET／PATCH）以 `model_validate` 組裝；admin `list_users` 於 `admin_service`
- Web：`lib/auth/auth-store.ts`（persist `user`）、`lib/auth/use-auth.ts`、`lib/hooks/use-profile.ts`（`useMe`／`useUpdateProfile` 會 `setAuth`）、`components/shell/app-shell.tsx`、`components/collaboration/*`、`app/(app)/collaboration/groups/[id]/page.tsx`（成員清單／leave 已存在）、`lib/hooks/use-groups.ts`、`components/dashboard/quick-links.tsx`
- i18n：`apps/web/messages/zh-TW.json`＋`en.json`（逐鍵插入、鍵集零差異）

**盤點定案（2026-10-17，實作前一覽）：**

1. **矩陣語意裁定（本 phase 最重要的決定）**：**不引入跨成員寫入**（collaboration 設計中 Option C「group 成員寫入權限」維持 out of scope，mutations 仍限 owner）——既有成員（editor）能力**零回歸**；矩陣中「物品 CRUD／借出歸還／盤點／清單編輯 ✅ owner/admin/editor」＝該角色對**自身資料**的寫入能力（現況）。
2. **viewer＝唯讀帳號**：連自身資料亦不可寫。理由：roadmap 使用情境「家庭為底、協作為輔」＋「適合家人只查不修改」＋§5.5 文案「你是檢視者 — 可以查看所有物品，**內容由群組成員維護**」＋「編輯入口一律不渲染（非禁用）」；若 viewer 僅在群組範圍唯讀，本 phase 與現況無差異（現行成員本就唯讀他人物品）。
3. **唯讀判定（鎖定）**：`is_read_only(user) ⇔ user 有 ≥1 筆 group_members membership 且**全部** role == 'viewer'`。推論：owner 絕不唯讀（owner 的 member row 為 editor）；「A 群組 viewer、B 群組 editor」→ 非唯讀（**避免被他人降權鎖死自身帳號**）；離開所有群組 → 恢復一般使用者（self-leave 既有功能、維持開放）。
4. **角色 → 權限表（實作值）**：
   - 檢視群組物品／統計：全角色 ✓（**不變**，`visible_item_owner_ids` 不動）
   - 物品 CRUD／借出歸還／盤點／清單編輯：viewer ❌ 403；owner／admin／editor 對自身資料不變（零回歸）
   - 群組管理（改名／加成員／改角色）：owner ✓、admin ✓、editor/viewer ❌ 403
   - 刪除群組：**owner only**（admin ❌；破壞性操作收緊，登錄決策）
   - 離開群組：所有角色對自己 ✓（不變；viewer 的解除唯讀出口）
   - admin 不得變更／移除 owner（409）；admin **可**管理其他 admin（簡化；owner 為最終權威）
5. **DB（migration 0022）**：`group_members.role` `String(16)` NOT NULL `server_default='editor'`（backfill 既有列）＋`ck_group_members_role` CHECK `role IN ('admin','editor','viewer')`；model `__table_args__` 加 `CheckConstraint`。downgrade：drop constraint＋drop column。**owner 不存 'owner'**（owner 由 `groups.owner_id` 判定；owner 列 DB 值 'editor'）。
6. **唯讀阻擋範圍（防線＝`WriterGuardRoute`，403）**：routers `items`（含 favorite／bulk／bulk-delete）、`batches`、`items_bulk`（bulk-import；export GET 不受影響）、`images`、`loans`、`lists`、`stocktake`、`transfers`、`backup`（import POST；export GET 不受影響）、`categories`、`locations`、`warehouses`、`tags`、`customization`。**不擋**：`users`（個人資料／偏好／tokens）、`notifications`（個人收件匣）、`webhooks`／`external_channels`（整合設定；`process-retries` 為系統排程、維持現行）、`stats`／`barcodes`／`labels`／`item_history`（讀取）、`jobs`／`admin`（既有 admin 閘門較強）、`ai`（AI 生成為唯讀輔助；P32–34 再定）。**403 先於資源存在性判斷**（router 依賴先跑；不洩漏資源存在與否）。
7. **API 介面**：
   - `GroupMemberRead.role: Literal["owner","admin","editor","viewer"]`（owner 列回 `owner`＝有效角色；DB 值不變）
   - `GroupSummary.my_role: Literal["owner","admin","editor","viewer"]`（當前使用者對該群組有效角色；既有 `is_owner` 保留）
   - `GroupAddMember.role: Literal["admin","editor","viewer"] = "editor"`（可選；允許直接以 viewer 加入家人）
   - 新 `PATCH /api/groups/{group_id}/members/{user_id}`（body `{"role": "admin|editor|viewer"}`）→ 200 `GroupMemberRead`；`role=owner` → 422（Literal）；
   - `UserPublic.is_read_only: bool = False`（login／register／bootstrap／`/auth/me`／`/users/me` GET＋PATCH 計算；admin `GET /admin/users` 以批次查詢附帶）
   - `PreferencesRead.viewer_notice_dismissed: bool = False`／`PreferencesUpdate.viewer_notice_dismissed: bool | None`（PUT 為 merge 語意，無需 migration）
8. **審計**：`group.member_added`／`group.member_role_changed`／`group.member_removed`（`resource_type="group"`、`resource_id=group_id`、meta：target_user_id／target_username／from／to）；`audit_service.log()` 自帶 commit → **於 service 交易完成後**呼叫。
9. **Web「不渲染」範圍（§5.5）**：items（list 新增鈕＋空態 CTA／detail 全部動作＋批次／new＋edit 頁面級不渲染表單／favorite）／lists／stocktakes／scan（建立入口）／dashboard（低庫存補貨清單鈕）／settings data（CSV 匯入）／settings backup（匯入卡；**匯出保留**）／taxonomy 面板（categories／tags／customization／locations 樹：建立／改名／刪除／拖放／鍵盤操作）／collaboration（新增群組、成員管理；**leave 保留**）。**導覽列（nav）不變**（viewer 仍可瀏覽全部頁面，唯讀呈現）。
10. **不做（範圍外）**：跨成員寫入（Option C）；admin 刪群組；owner 轉移；邀請/接受流程；角色變更通知（`emit`）；稽核查詢 UI；taxonomy 頁面的「隱藏導覽」；`ai` router 防線；匯出限制；背景同步。
11. **i18n**：逐鍵插入 zh-TW／en（`viewer.*`、`collab.roles.*`、`collab.groups.detail.*` 角色文案）；鍵集以 python flat-set 驗證零差異。
12. **e2e 確定性**：viewer 帳號以 API 建立（`request` fixture：register → owner 建群組 → `POST members {role:"viewer"}`）；不依賴外部網路；`--workers=2`。
13. **狀態契約（§5.4，本 phase 介面）**：

| 介面 | LOADING | EMPTY | ERROR | SUCCESS |
|---|---|---|---|---|
| 角色變更（成員列 Select） | select disabled＋`aria-busy` | — | 錯誤 toast（「無法變更角色」）＋選單回復原值 | 成功 toast＋角色徽章即時更新（`invalidateQueries`） |
| viewer banner（首次） | 偏好載入中不渲染（避免閃爍） | 已關閉／非 viewer → 不渲染 | 關閉失敗 → 留在畫面＋toast | 關閉 → 立即消失；重新載入不再出現 |
| 物品詳情（viewer） | — | — | — | 底部固定句常駐＋無任何動作鈕（`role="status"` 不適用；純靜態文案） |

**執行前置：**
1. worktree：`git worktree add .claude/worktrees/phase30-member-roles -b claude/phase30-member-roles`
2. worktree 無 `.env`：先 `cp .env .claude/worktrees/phase30-member-roles/.env`
3. worktree 首次 `pnpm install`（node_modules 不存在）
4. 起堆疊：`ENABLE_DEV_ROUTES=1 docker compose up -d --build api web && docker compose up -d nginx`
5. 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `cd apps/web && pnpm test -- <filter>`／`pnpm typecheck`；型別 `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json` ＋ `pnpm --filter @ims/api-types gen:types`；e2e `cd apps/web && pnpm exec playwright test --workers=2`

---

## Phase 1: API（角色模型＋唯讀防線＋群組管理）

### Task 1.1: 角色模型＋migration 0022＋schemas

**Files:**
- Modify: `apps/api/app/models/group.py`
- Create: `apps/api/alembic/versions/0022_group_member_roles.py`
- Modify: `apps/api/app/schemas/group.py`
- Modify: `apps/api/app/repositories/groups_repository.py`
- Modify: `apps/api/app/services/groups_service.py`（`_summary`／`get_group_detail`／`list_groups`）
- Test: `apps/api/tests/test_group_model_smoke.py`、`tests/test_collab_schemas.py`、`tests/test_groups_repository.py`、`tests/test_groups_routes.py`（擴充）

**TODO:**
- [ ] RED：model smoke——`GroupMember` 具 `role` 欄、預設 `editor`、CHECK 拒絕非法值（SQLite 亦強制）；schema——`GroupMemberRead.role`（owner 列 → `owner`）、`GroupSummary.my_role`（owner／admin／editor／viewer 四態）、`GroupAddMember.role` 預設 `editor`、非法 role 422；repository——`member_roles_for_user` 回傳 {group_id: role}；routes——`GET /api/groups`／`GET /api/groups/{id}` 含 `my_role`、成員列含 role
- [ ] GREEN：model 加 `role: Mapped[str] = mapped_column(String(16), nullable=False, default="editor")`＋`CheckConstraint("role IN ('admin','editor','viewer')", name="ck_group_members_role")`（`__table_args__` 合併）；migration 0022（`add_column(server_default='editor')`＋`create_check_constraint`；downgrade 逆序）；schema 改為 Literal 四態（owner 列計算）；`_summary` 加 `my_role`（先判 `g.owner_id == user_id` → `owner`，再查 member row）；`get_group_detail` 成員 role：`m.user_id == g.owner_id → "owner"` 否則 DB 值；repository `member_roles_for_user`（單查詢，供 list_groups 批次使用）
- [ ] 註：owner 建群時自身 member row 維持 `editor`（owner 判定先行）；`GroupAddMember.role` 僅存值、權限檢查於 T1.4

### Task 1.2: 唯讀判定與暴露（`is_read_only`）

**Files:**
- Modify: `apps/api/app/services/visibility_service.py`
- Modify: `apps/api/app/schemas/user.py`、`apps/api/app/schemas/preferences.py`
- Modify: `apps/api/app/routes/auth.py`、`apps/api/app/routes/users.py`
- Modify: `apps/api/app/services/admin_service.py`（`list_users`）
- Test: Create `apps/api/tests/test_readonly_access.py`；擴充 `tests/test_auth.py`、`tests/test_admin_routes.py`

**TODO:**
- [ ] RED：判定表——①單群組 viewer → True；②viewer＋editor（跨群組）→ False；③owner（含自身 row 為 editor）→ False；④無任何群組 → False；⑤離開所有群組後 → False；暴露——`POST /api/auth/register`／`login`、`GET /api/auth/me`、`GET`／`PATCH /api/users/me` 回應含 `is_read_only`；`GET /api/admin/users` 每列正確；偏好——`PUT /api/users/me/preferences {viewer_notice_dismissed: true}` → GET 回 true 且不覆蓋 theme/currency（merge）
- [ ] GREEN：`visibility_service.read_only_user_ids(session, user_ids) -> set[UUID]`（單查詢 GROUP BY：`COUNT(*) == SUM(role=='viewer')` 且有列）；`is_read_only(session, user_id) -> bool`；`user_public(session, user) -> UserPublic`（`model_validate` ＋ `model_copy(update={"is_read_only": …})`）；`UserPublic.is_read_only: bool = False`；`PreferencesRead/Update` 加 `viewer_notice_dismissed`；auth.py（register／login／me／bootstrap）／users.py（me GET／PATCH）改用 `user_public`；admin_service `list_users` 以 `read_only_user_ids` 批次附帶
- [ ] 註：`PATCH /users/me` 亦需計算（web `useUpdateProfile` 會以回應覆寫 auth store，預設 False 會誤清除）

### Task 1.3: 唯讀寫入防線（`WriterGuardRoute`）

**Files:**
- Create: `apps/api/app/auth/readonly.py`（`require_writer` 依賴＋`WriterGuardRoute`）
- Modify: routers 套 `route_class=WriterGuardRoute`——`apps/api/app/routes/items.py`、`batches.py`、`items_bulk.py`、`images.py`、`loans.py`、`lists.py`、`stocktake.py`、`transfers.py`、`backup.py`、`categories.py`、`locations.py`、`warehouses.py`、`tags.py`、`customization.py`
- Test: Create `apps/api/tests/test_readonly_guard.py`

**TODO:**
- [ ] RED（矩陣測試）：viewer 帳號 → ①每個擋域各打一個代表性 mutate（items POST／PATCH／DELETE／favorite／bulk-delete、batches POST、items_bulk bulk-import、images POST、loans POST、lists POST、stocktake POST、transfers POST、backup import POST、categories POST、locations POST／reorder、warehouses POST、tags POST、customization POST）→ **403**（含資源不存在情境亦 403）；②讀取（items GET、backup export GET、items_bulk export.csv GET）→ 200；③不擋域：`PUT /users/me/preferences`→200、`PATCH /notifications/{id}/read`→204；④editor 同操作非 403（零回歸）；⑤未認證 → 401（防線不改變既有行為）
- [ ] GREEN：`require_writer(user=Depends(get_current_user), session=Depends(get_db))` → `is_read_only` 為 True 時 403（detail「唯讀帳號不可修改資料」）；`WriterGuardRoute(APIRoute)`：`methods` 非 `{GET,HEAD,OPTIONS}` 子集時 append `Depends(require_writer)`；各 router 建構子加 `route_class=WriterGuardRoute`
- [ ] 註：`groups` router **不套**（leave 需開放，見 T1.4）；`labels`／`barcodes`／`stats`／`item_history` 唯讀不套；403 發生於路由依賴階段（早於 body 解析與資源查詢）

### Task 1.4: 群組管理權限＋角色變更端點＋audit

**Files:**
- Modify: `apps/api/app/services/groups_service.py`
- Modify: `apps/api/app/routes/groups.py`
- Modify: `apps/api/app/repositories/groups_repository.py`（`list_members` 需帶 role；`add_member(role=…)`；`update_member_role`）
- Test: `apps/api/tests/test_groups_service.py`、`tests/test_groups_routes.py`（擴充）

**TODO:**
- [ ] RED：
  - 建立群組：viewer → **403**；一般使用者 → 201
  - 加入成員：owner ✓、**admin ✓**、editor/viewer → 403；`role` 參數（省略 → editor；`role="viewer"` → 該使用者 `is_read_only` 成 True）；非成員 caller → 404；目標非使用者 → 404；重複 → 409
  - 角色變更 `PATCH .../members/{user_id}`：owner ✓、admin ✓（可改其他 admin）；editor → 403；非成員 → 404；**目標為 owner → 409**；`role="owner"` → 422；目標非成員 → 404；成功回 `GroupMemberRead`（role 新值）
  - 改名：admin ✓、editor/viewer → 403；**刪群組：admin → 403、owner → 204**
  - 移除成員：self → 204（editor／viewer 亦可，維持）、owner／admin 移除他人 → 204、editor 移除他人 → 403、移除 owner → 409
  - audit：`group.member_added`／`group.member_role_changed`／`group.member_removed` 各寫入 audit_logs（meta 含 from/to／target）
- [ ] GREEN：`_ensure_managed(session, user_id, group_id)`（`get_for_member` → 非成員 404；`owner_id == user_id` → 通過；否則 member row `role == "admin"` → 通過；editor/viewer → 403）；`create_group` 先擋 `is_read_only` → 403；`update_group`／`add_member_by_username`／`change_member_role`／`remove_member` 套用（remove 保留 self／owner 特別規則）；`delete_group` 維持 owner-only（`_ensure_owned`）；role 變更寫入後於交易外呼叫 `audit_service.log`
- [ ] 註：admin 可管理其他 admin（簡化決策）；owner 的 member row 不可被 PATCH（409）；`GroupAddMember.role` 僅 owner／admin 可指定

### Task 1.5: api-types 重生成

**Files:**
- Modify: `packages/api-types/openapi.json`、`packages/api-types/src/index.ts`（tracked 生成檔）

**TODO:**
- [ ] `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json`
- [ ] `pnpm --filter @ims/api-types gen:types`
- [ ] 確認新 schema 進型別：`GroupMemberRead.role`、`GroupSummary.my_role`、`PATCH …/members/{user_id}`、`UserPublic.is_read_only`、`Preferences.viewer_notice_dismissed`
- [ ] commit（與 T1.1–T1.4 一起或獨立；生成檔一併入版控）

---

## Phase 2: Web（唯讀體驗＋角色管理）

### Task 2.1: Web 基礎（`useReadOnly`／`EditableOnly`／`ViewerBanner`／`MeSync`／i18n）

**Files:**
- Create: `apps/web/lib/auth/use-readonly.ts`
- Create: `apps/web/components/common/editable-only.tsx`
- Create: `apps/web/components/shell/viewer-banner.tsx`、`apps/web/components/shell/me-sync.tsx`
- Modify: `apps/web/components/shell/app-shell.tsx`、`apps/web/app/(app)/layout.tsx`
- Modify: `apps/web/messages/zh-TW.json`、`en.json`
- Test: `apps/web/components/shell/viewer-banner.test.tsx`、`apps/web/components/common/editable-only.test.tsx`、`apps/web/lib/auth/use-readonly.test.ts`（新增）

**TODO:**
- [ ] RED／GREEN：`useReadOnly()`（`useAuthStore(s => s.user?.is_read_only ?? false)`）；`MeSync`（`useMe()` 成功 → `setAuth(token, user)` 同步 store；render null；掛於 `(app)/layout.tsx`）；`EditableOnly`（readOnly → 回 `null`，否則 children）；`ViewerBanner`——readOnly 且偏好未載入 → 不渲染（避免閃爍）；readOnly 且 `!viewer_notice_dismissed` → 顯示 §5.5 文案＋關閉鈕；關閉 → `PUT /users/me/preferences {viewer_notice_dismissed:true}` → 樂觀隱藏＋invalidate；非 viewer 不渲染；掛於 `AppShell`（`AppHeader` 之後）
- [ ] i18n 逐鍵插入：`viewer.banner.title`（你是檢視者）、`viewer.banner.body`（可以查看所有物品，內容由群組成員維護）、`viewer.banner.dismiss`、`viewer.itemNotice`（你是檢視者，如需修改請聯絡群組管理員）；en 對應
- [ ] 鍵集驗證：python flat-set 比對 zh-TW／en 零差異

### Task 2.2: 物品介面唯讀

**Files:**
- Modify: `apps/web/app/(app)/items/items-list-client.tsx`（新增物品鈕×2＋空態 CTA）
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`（edit／label／template／transfer／delete／favorite、`BatchSection canEdit`、`LoanCard` 動作、底部固定句）
- Modify: `apps/web/app/(app)/items/new/*`、`apps/web/app/(app)/items/[id]/edit/*`（頁面級：readOnly → 不渲染表單，改渲染提示卡＋返回連結）
- Modify: `apps/web/components/items/items-table.tsx`（列動作／選取批次操作，若有）
- Test: 對應 `page.test.tsx`／`items-list-client.test.tsx` 擴充

**TODO:**
- [ ] RED：readOnly → 列表無「新增物品」與空態 CTA；詳情頁無全部動作鈕（含 favorite、批次、借出）＋底部固定句存在（`role="status"` 靜態文案）；`/items/new`／`/items/[id]/edit` 直達 → 顯示「檢視者無法編輯」提示卡且表單不渲染；非 readOnly → 全部照舊（零回歸斷言）
- [ ] GREEN：以 `<EditableOnly>` 包覆各編輯入口；詳情頁 `const readOnly = useReadOnly()`；`canEdit={isOwner && !readOnly}`；底部固定句 `readOnly` 時渲染
- [ ] 註：`/items/labels`（列印）維持可用（讀取性操作，登錄決策）

### Task 2.3: 清單／盤點／掃碼／儀表板／設定（data＋backup）唯讀

**Files:**
- Modify: `apps/web/app/(app)/lists/*`（新增清單鈕、清單 detail 新增/編輯/勾選/刪除入口）
- Modify: `apps/web/app/(app)/stocktakes/*`（開始盤點鈕、detail 計數/完成/取消入口）
- Modify: `apps/web/app/(app)/scan/*`（掃描結果「建立物品」等建立入口）
- Modify: `apps/web/components/dashboard/low-stock-card.tsx`（建立補貨清單鈕）或實際落點
- Modify: `apps/web/app/(app)/settings/data/page.tsx`＋`components/settings/csv-panel.tsx`（匯入卡；匯出保留）
- Modify: `apps/web/app/(app)/settings/backup/page.tsx`＋`components/settings/backup-panel.tsx`（匯入卡；匯出卡保留）
- Test: 上述各頁 vitest 擴充

**TODO:**
- [ ] RED：readOnly → 各頁編輯入口不渲染（清單新增／勾選、盤點開始與操作、掃碼建立、補貨清單鈕、CSV 匯入卡、備份匯入卡）；`匯出`（CSV export／備份 export）仍渲染；非 readOnly 零回歸
- [ ] GREEN：`<EditableOnly>` 包覆；備份頁：readOnly 僅渲染匯出卡
- [ ] 註：清單 detail readOnly 時為唯讀檢視（項目與數量顯示、無 toggle／delete）

### Task 2.4: taxonomy 面板唯讀

**Files:**
- Modify: `apps/web/components/taxonomy/categories-panel.tsx`、`tags-panel.tsx`＋`tag-row.tsx`
- Modify: `apps/web/components/taxonomy/locations-panel.tsx`＋`location-tree-node.tsx`（`readOnly` prop：停用拖放／鍵盤（F2／Delete／Insert）／節點動作選單／建立鈕／移動 sheet）
- Modify: `apps/web/app/(app)/settings/customization/*` 相關面板（item types／custom fields／templates 建立/編輯/刪除入口）
- Test: `categories-panel.test.tsx`、`tags-panel.test.tsx`、`locations-panel.test.tsx`、customization 測試擴充

**TODO:**
- [ ] RED：readOnly → 各面板不渲染建立／編輯／刪除／合併／拖放入口，資料列仍可見；非 readOnly 零回歸
- [ ] GREEN：`readOnly` prop（或 `<EditableOnly>`＋元件層條件）；locations 樹：`draggable={!readOnly}`、drop handlers 條件、鍵盤 handler 早退、動作選單不渲染
- [ ] fallback（若 locations 成本超預期，主席裁定）：頁面級 `ViewerNotice`（不渲染樹編輯 UI）

### Task 2.5: 群組角色管理 UI（collaboration）

**Files:**
- Modify: `apps/web/app/(app)/collaboration/groups/[id]/page.tsx`
- Modify: `apps/web/components/collaboration/add-member-dialog.tsx`（角色選單）
- Modify: `apps/web/app/(app)/collaboration/page.tsx`＋`components/collaboration/new-group-dialog.tsx`（viewer 隱藏建立入口）
- Modify: `apps/web/lib/api/groups.ts`（`updateMemberRole`）、`apps/web/lib/hooks/use-groups.ts`（`useUpdateMemberRole`）
- Test: `groups/[id]/page.test.tsx`（新增）、`add-member-dialog.test.tsx` 擴充

**TODO:**
- [ ] RED：`my_role ∈ {owner, admin}` → 成員列顯示角色 Select（admin／editor／viewer 三選）＋「新增成員」；`owner` 列顯示「擁有者」徽章不可改；`my_role ∈ {editor, viewer}` → 成員列唯讀（角色徽章、無 Select）＋無新增入口；viewer → 「新增群組」不渲染；leave 鈕對所有非 owner 保留；變更成功 → toast＋群組 query invalidate；失敗 → toast＋select 回復
- [ ] GREEN：member row role 徽章／Select（`useUpdateMemberRole` → `PATCH`）；角色說明文案（`collab.roles.*`）；`<EditableOnly>` 包新群組入口
- [ ] i18n：`collab.roles.owner/admin/editor/viewer`（擁有者／管理員／編輯者／檢視者）＋說明行＋`members.changeRoleFailed`

---

## Phase 3: E2E＋文件

### Task 3.1: e2e（viewer 旅程＋角色管理）

**Files:**
- Create: `apps/web/tests/viewer-role.spec.ts`

**TODO:**
- [ ] 情境① viewer 旅程：API 建 owner＋viewer 帳號 → owner 建群組、`POST members {role:"viewer"}` → viewer 登入 → banner 顯示（§5.5 文案）→ 關閉 → reload 不再出現 → `/items` 無「新增物品」→ owner 的物品詳情顯示唯讀徽章＋底部固定句 → 直接 `POST /api/items`（viewer token）→ 403 → viewer 於群組頁 leave → reload → 可編輯（零唯讀）
- [ ] 情境② 角色管理：owner 將 editor 升 `admin` → admin 登入可新增成員／改角色；改回 `editor` → 管理入口消失；`PATCH` owner 的 role → 409
- [ ] 情境③ 越權：editor 呼叫 `PATCH .../members/{user}` → 403；viewer 呼叫 `POST /api/groups` → 403
- [ ] 全部以 `request` fixture 準備狀態（多帳號 context 範式沿用 `backup.spec.ts`）

### Task 3.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[Unreleased]` → alpha.30：角色模型／viewer 唯讀／admin 群組管理／migration 0022）
- Modify: `docs/v2-roadmap.md`（Phase 30 row ✅＋測試規模更新）
- Modify: 本計畫（勾選＋Final Verification 實測）

**TODO:**
- [ ] CHANGELOG alpha.30（繁中）
- [ ] v2-roadmap Phase 30 ✅＋測試統計
- [ ] 本計畫全勾選＋驗收對照確認

---

## 驗收對照（roadmap §六 Phase 30）

| 驗收項 | Task |
|---|---|
| 角色模型 `owner/admin/editor/viewer`（owner＝`groups.owner_id`） | T1.1 |
| 權限矩陣（角色 × 操作矩陣式測試） | T1.3（唯讀域）＋T1.4（群組管理） |
| 越權 403 | T1.3＋T1.4＋T3.1③ |
| 角色變更寫 audit log | T1.4 |
| 遷移後既有群組權限零回歸（含 owner 判定） | T1.1（backfill editor）＋T1.3④ |
| 權限檢查集中（visibility／group service） | T1.2＋T1.3＋T1.4 |
| `PATCH /api/groups/{id}/members/{user_id}` | T1.4 |
| 群組詳情頁角色管理（Web） | T2.5 |
| viewer §5.5 旅程（banner／入口不渲染／固定句） | T2.1–T2.4＋T3.1① |
| 403 為後端防線（非主 UX） | T1.3＋T3.1① |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run --extra test pytest -q` → 全部 passed
- [ ] Web：`pnpm test` → 全部 passed＋`pnpm typecheck` 0 error
- [ ] api-types 重生成零 diff（`openapi.json`／`src/index.ts`）
- [ ] e2e：`pnpm exec playwright test --workers=2`（含 `viewer-role.spec.ts`；程式碼凍結後重跑）
- [ ] 視覺走查：桌機（viewer banner／items 唯讀／詳情固定句／群組角色管理）＋行動 390；截圖人工檢視
- [ ] migration 0022 up／down 演練（`alembic upgrade head`／`downgrade -1`）

### 收尾環境註記（2026-10-17 起填）

- （待填）
