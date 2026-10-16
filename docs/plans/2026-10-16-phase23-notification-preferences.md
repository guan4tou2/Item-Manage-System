# Phase 23 — 通知偏好中心 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 23（L298–323）＋ §5.2 設定頁 IA、§5.4 互動狀態、§5.7 響應式與無障礙。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**。
> 完成任一 task 即 commit（Conventional Commits，`feat(api): …`／`feat(web): …`／`test(web): …`）。

**Goal：** 設定頁由單排 tabs 重構為「子路由＋索引頁」四群組（零回歸）；新增「通知偏好」頁——每個通知類型 × 每個管道可獨立開關，為 Phase 24 到期提醒與 Phase 31 報表鋪好降噪機制。

**Architecture：** Web IA 重構先行（獨立於 API、且是零回歸範圍最大的部分，最早隔離）。API 以新表 `notification_preferences` 只存「顯式覆寫」，未存列＝預設；`emit()`（站內建立）與 `deliver_all()`（外部管道）各自查偏好過濾。偏好計算唯一入口＝`app/services/notification_prefs.py`（常數、映射、鎖定、預設全在此，其他模組不得自行組裝類型/管道清單）。fail-soft 紅線不變：偏好查詢出錯一律視為開啟，不得炸觸發交易。

**Tech Stack：** FastAPI、SQLAlchemy async、Alembic（migration `0017`）、pytest（SQLite in-memory：`tests/conftest.py` create_all）、React Query、next-intl、shadcn/ui、Vitest、Playwright。

**關鍵既有資產（重用，勿重造）：**
- `notifications_service.emit()`（`apps/api/app/services/notifications_service.py:20`）：建站內列＋呼叫 `deliver_all`（L51–58）；fail-soft 慣例（例外只 log）
- `external_notifications.deliver_all()`（`apps/api/app/services/external_notifications.py:124`）：email／LINE／Telegram／WebPush 扇出；`deliver_email/line/telegram/web_push` 各自 fail-soft
- 管道綁定現況：`GET /api/channels/status`（`routes/external_channels.py:27`）＋ `LineUserLink`／`TelegramUserLink`／`WebPushSubscription`（`models/external_channels.py`）
- 設定面板元件 10 個（`apps/web/components/settings/`）＋既有 3 個 panel 測試（customization／webhook／channels）
- 頁面測試慣例：`apps/web/app/(app)/**/page.test.tsx`（dashboard／notifications 等已有）
- `middleware.ts`：`/settings` 已列 `PROTECTED_PREFIXES`、matcher `/settings/:path*` → 子路由自動受 cookie 保護，**不需改**
- e2e 慣例：`tests/*.spec.ts`、zh-TW locale、`request.post("/api/auth/register")` 建帳號；`POST /auth/bootstrap-admin` → `profile_service.bootstrap_admin_if_none`（系統無 admin 時首位點擊者升級）

**盤點定案（2026-10-16，實作前一覽）：**
1. 現行實際發送的 `type` 共 5 種：`low_stock`（items_service ×2）、`transfer.request`／`transfer.accepted`（transfers_service）、`system.welcome`（註冊）、`admin.test`（管理員測試通知）。矩陣仍依 roadmap 枚舉建齊 **11 類**（Phase 24 將發 `expiring_soon`／`expired`；借還與報表類先佔位），以類別映射承接：`system.welcome`／`admin.test` → `system`；未映射的新字串 → 視為開啟（向後相容＋debug log）。
2. `deliver_all()` 目前不接收 `type` → **加必填 kwarg `type`**（唯一生產呼叫點＝`emit()`）；每個管道送出前查偏好。
3. 偏好表只存**覆寫列**：`enabled == 預設值` 時不落列（PUT 時自動刪除既有覆寫）；GET 展開完整矩陣。
4. 不可關類別（後端強制）：`group_invite`、`system`（涵蓋帳號安全／系統必要通知）。**整列**（所有管道）鎖定；PUT 對鎖定列 `enabled=false` → 422；emit／deliver 對鎖定列直接視為開啟（雙重保險）。
5. 預設值：全部類型 × 全部管道＝**開啟**（維持現行行為）——唯二例外：`expired`／`expiring_soon` 的 `email`／`line`／`telegram` 預設**關**（「站內＋推播」降噪，roadmap 語意）。
6. 現行 `/settings` 無 `?tab=` 深連結（全 repo 盤點 0 筆）→ 不做 legacy redirect；`/settings`（索引）與 `/settings/taxonomy` 路徑維持，既有連結（`nav-items.ts`／`user-menu.tsx`／`quick-links.tsx`／taxonomy 麵包屑）不動。
7. 未綁定判定（使用者側）：`line`＝`user_line_linked`、`telegram`＝`user_telegram_linked`、`web_push`＝`user_web_push_count > 0`；`in_app`／`email` 恆可用（email＝帳號 email 恆存在）。伺服器端未設定的細節留在「通知管道」面板呈現，偏好頁不管。

**執行前置：**
- worktree：`.claude/worktrees/phase23-notif-prefs`（branch `claude/phase23-notif-prefs`）
- alembic head＝`0016`；T1–T3（除 e2e）不需 docker；Phase 4 前 `docker compose up -d`（worktree `.env` 比照 Phase 22：`ENABLE_DEV_ROUTES=1` 等）
- 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `pnpm -F @ims/web test`／`pnpm -F @ims/web typecheck`；型別 `pnpm -F @ims/api-types gen:types`

**Execution Order**
1. Web：索引頁＋子路由＋守衛＋面板搬遷＋smoke 擴充＋e2e 抽查
2. API：migration＋model＋`notification_prefs` service／repo
3. `emit()`／`deliver_all()` 整合（預設零回歸）
4. Routes＋schemas＋api-types
5. Web：client／hooks（樂觀）→ 偏好頁矩陣 UI → i18n／a11y
6. e2e → CHANGELOG／roadmap／勾選

---

## Phase 1: Web — 設定頁 IA 重構（前置，零回歸）

### Task 1.1: 子路由骨架＋設定首頁索引＋admin 守衛

**Files:**
- Modify: `apps/web/app/(app)/settings/page.tsx`（tabs 版改為四群組索引頁）
- Create: `apps/web/components/settings/settings-nav.ts`（四群組靜態表：id／標題 i18n key／說明 i18n key／href／adminOnly）
- Create: `apps/web/components/settings/settings-page-shell.tsx`（子頁外殼：麵包屑「設定」→`/settings`＋標題／說明）
- Create: `apps/web/components/settings/admin-only.tsx`（client：`useMe()` 判定；loading＝skeleton；非 admin＝「此頁僅限管理員」空態，不 redirect）
- Test: `apps/web/app/(app)/settings/page.test.tsx`

**TODO:**
- [x] 群組映射（§5.2）：個人（profile／password／preferences）｜通知與提醒（channels／notifications）｜整合與資料（webhooks／tokens／data／customization／taxonomy）｜管理（members／audit）——首層 4、各組 ≤6
- [x] 索引頁：群組卡片（標題＋頁面連結列：名稱＋一句說明＋chevron）；`BootstrapAdminButton` 置頂保留（元件僅非 admin 渲染，行為不變）；`管理`卡 `is_admin !== true` 時整卡不渲染
- [x] 卡片與連結鍵盤可達；行動版單欄堆疊
- [x] i18n：新增 `settings.index.*`（群組名／頁名／說明）；既有 `settings.tabs.*` 遷移為頁面標題（不留死鍵）
- [x] 測試：四群組與連結 href 正確、非 admin 隱藏「管理」、`useMe` loading＝skeleton、`BootstrapAdminButton` 僅非 admin 可見

**Commands:**
- `pnpm -F @ims/web test app/(app)/settings`
- `pnpm -F @ims/web typecheck`

### Task 1.2: 十面板子路由化＋面板 smoke 測試擴充

**Files（全部 Create，內容＝`SettingsPageShell`＋對應 panel）:**
- `apps/web/app/(app)/settings/profile/page.tsx` → `ProfileForm`
- `apps/web/app/(app)/settings/password/page.tsx` → `PasswordForm`
- `apps/web/app/(app)/settings/preferences/page.tsx` → `PreferencesForm`
- `apps/web/app/(app)/settings/tokens/page.tsx` → `ApiTokensPanel`
- `apps/web/app/(app)/settings/customization/page.tsx` → `CustomizationPanel`
- `apps/web/app/(app)/settings/channels/page.tsx` → `NotificationChannelsPanel`
- `apps/web/app/(app)/settings/webhooks/page.tsx` → `WebhookPanel`
- `apps/web/app/(app)/settings/data/page.tsx` → `CsvPanel`
- `apps/web/app/(app)/settings/members/page.tsx` → `AdminOnly`＋`AdminUsersPanel`
- `apps/web/app/(app)/settings/audit/page.tsx` → `AdminOnly`＋`AuditLogPanel`
- Test（補齊 7 個沒有測試的面板，命名同既有慣例）:
  - `apps/web/components/settings/profile-form.test.tsx`、`password-form.test.tsx`、`preferences-form.test.tsx`、`api-tokens-panel.test.tsx`、`csv-panel.test.tsx`、`admin-users-panel.test.tsx`、`audit-log-panel.test.tsx`

**TODO:**
- [x] `/settings/taxonomy` 不動（麵包屑已指回 `/settings`）；`quick-links`／`nav-items`／`user-menu` 既有連結不動（typecheck 驗 typedRoutes）
- [x] 移除舊 tabs 版首頁邏輯（settings 首頁不再用 `Tabs`）
- [x] 面板元件**零修改**（搬的是容器不是元件）；既有 3 個 panel 測試不動、維持綠
- [x] 每個 smoke：render＋核心操作 1 個（tokens：列表渲染／csv：匯出按鈕曝光／admin-users：使用者列表載入／audit：記錄載入／preferences：主題切換等）——mock `lib/api/*` 比照既有 pattern
- [x] `AdminOnly` 的非 admin 空態與 loading 由 T1.1 元件測試覆蓋；panel smoke 僅 happy path＋1 個互動

**Commands:**
- `pnpm -F @ims/web test`
- `pnpm -F @ims/web typecheck`

### Task 1.3: e2e — 子路由可達性＋bootstrap 首引導＋零回歸抽查

**Files:**
- Modify: `apps/web/tests/navigation.spec.ts`（加設定子路由可達性抽查 3 條）
- Create: `apps/web/tests/settings.spec.ts`

**TODO:**
- [x] navigation.spec：登入後 `/settings` 見四群組卡；點「個人資料」「通知管道」到達對應子路由；taxonomy 由索引卡可達
- [x] settings.spec：非 admin 登入 → 「管理」卡不渲染＋`BootstrapAdminButton` 可見 → 點擊 →「管理」卡出現且 `/settings/members` 可達
  - 註：bootstrap 依環境狀態分支——先以 API 探測（`POST /auth/bootstrap-admin` 的回應／`is_admin`），系統已有 admin 時驗證「無引導按鈕、管理卡以 admin 身分可見」；不假設 DB 為空
- [x] 直接 URL 非 admin 訪問 `/settings/members` → 「此頁僅限管理員」空態（不 redirect）
- [x] 既有 12 支 spec 全數不回歸（settings 首頁無 tabs 後，不受影響）

**Commands:**
- `docker compose up -d`（首次）→ `cd apps/web && pnpm exec playwright test`

---

## Phase 2: API — 通知偏好核心

### Task 2.1: Migration `0017`＋`NotificationPreference` model

**Files:**
- Create: `apps/api/app/models/notification_preference.py`
- Modify: `apps/api/app/models/__init__.py`（註冊）
- Create: `apps/api/alembic/versions/0017_notification_preferences.py`
- Test: `apps/api/tests/test_notification_preference_model_smoke.py`

**TODO:**
- [x] `NotificationPreference`：`id`(UUID pk)、`user_id`(FK `users.id` ondelete=CASCADE, index)、`type`(String(40), nullable=False)、`channel`(String(20), nullable=False)、`enabled`(bool, nullable=False)、`created_at`/`updated_at`（`_utcnow` 慣例）；`UniqueConstraint("user_id","type","channel", name="uq_notification_prefs_cell")`
- [x] migration 0017：`revision="0017"`、`down_revision="0016"`；upgrade＝建表＋unique＋user_id index；downgrade 對稱（比照 `0016_item_batches.py` 風格）
- [x] smoke：建列、同 cell 重複→unique 違反、刪 user→cascade 清列

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_notification_preference_model_smoke.py`
- `cd apps/api && uv run alembic upgrade head`

### Task 2.2: `notification_prefs` service＋repository（預設展開／鎖定／驗證）

**Files:**
- Create: `apps/api/app/repositories/notification_preferences_repository.py`
- Create: `apps/api/app/services/notification_prefs.py`
- Test: `apps/api/tests/test_notification_prefs_service.py`

**TODO:**
- [x] 常數（唯一出口）：`TYPES`（有序 11 類＋group：`items`／`collab`／`system`）、`CHANNELS`（`in_app`／`email`／`line`／`telegram`／`web_push`）、`LOCKED_TYPES = {group_invite, system}`、`EMIT_TYPE_MAP = {"system.welcome": "system", "admin.test": "system"}`、`TYPE_DEFAULT_OVERRIDES`（`expired`／`expiring_soon`：email／line／telegram=False）、`DEFAULT_ENABLED = True`
- [x] `default_enabled(type, channel)`；`is_enabled(session, user_id, *, type, channel)`：鎖定→True；emit 字串經 `EMIT_TYPE_MAP`（未映射→True＋debug log）；查覆寫列、無列→預設
- [x] `get_snapshot(session, user_id)`：types（含 group／locked）、channels、matrix（有效值）、`has_custom`、`channel_availability`（使用者側綁定）
- [x] `apply_updates(session, user_id, updates)`：驗證 type／channel 合法、鎖定不可關；`enabled == default` → 刪覆寫列、否則 upsert；單交易；回傳新 snapshot
- [x] `reset(session, user_id)`：刪全部覆寫；回傳 snapshot
- [x] repo 慣例：`get_cell`／`list_for_user`／`upsert`／`delete_cell`／`delete_all`／`has_any`
- [x] 測試：全新使用者＝全預設＋`has_custom=False`；覆寫→再切回預設（列被刪）；鎖定列關閉→錯誤；未知 type／channel→錯誤；`system.welcome` 受 `system` 控制、未映射字串→True；`expired` 預設 in_app True／email False

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_notification_prefs_service.py`

### Task 2.3: `emit()`／`deliver_all()` 偏好過濾整合（預設零回歸）

**Files:**
- Modify: `apps/api/app/services/notifications_service.py`（emit）
- Modify: `apps/api/app/services/external_notifications.py`（`deliver_all` 加 `type`、逐管道過濾）
- Test: `apps/api/tests/test_notifications_prefs_filtering.py`

**TODO:**
- [x] `emit()`：`in_app` 偏好關 → **不建站內列**（回 None）；偏好查詢 fail-soft（查詢失敗視為開啟）；照舊 fail-soft 呼叫 `deliver_all(..., type=type)`
- [x] `deliver_all(..., *, type)`：email／line／telegram／web_push 各自送出前 `is_enabled(...)`；鎖定類型不受偏好影響；簽名變更同步所有呼叫端（唯一生產呼叫點＝emit）
- [x] 既有測試零回歸（預設全開＝現行行為）：`test_notifications_service.py`／`test_notifications_low_stock.py`／`test_notifications_welcome.py`／`test_notifications_routes.py`／`test_external_channels.py` 全綠（若有直呼 `deliver_all` 的測試，同步補 `type`）
- [x] 新測試：關 `low_stock`×`email` → email 不呼叫、站內仍有；關 `low_stock`×`in_app` → 站內無列、email 仍發；全關 → 皆無（emit 回 None）；`group_invite`／`system` 關不掉（強制發）；`system.welcome` 經映射受 `system` 控制

**Commands:**
- `cd apps/api && uv run --extra test pytest -q`

### Task 2.4: `GET/PUT/DELETE /api/notifications/preferences`＋schemas＋api-types

**Files:**
- Create: `apps/api/app/schemas/notification_preferences.py`
- Modify: `apps/api/app/routes/notifications.py`
- Test: `apps/api/tests/test_notification_preferences_routes.py`
- Regen: `pnpm -F @ims/api-types gen:types`

**TODO:**
- [x] GET → snapshot（形狀見「API 契約」節）
- [x] PUT `{"updates":[{type,channel,enabled}]}`：422＝未知 type／channel、鎖定列 `enabled=false`；成功回新 snapshot
- [x] DELETE → 重置回預設、回 snapshot；**路由宣告順序必須在 `/{notification_id}` 之前**（DELETE 動詞路徑衝突）
- [x] 401（未登入）行為與既有 notifications 路由一致
- [x] 契約測試：GET 形狀（11×5＋locked／availability）、PUT→GET 反映、PUT 冪等、切回預設→`has_custom` 回 false、422 各案、DELETE 後全預設
- [x] api-types 重生成並 `typecheck`

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_notification_preferences_routes.py`
- `pnpm -F @ims/api-types gen:types`

---

## Phase 3: Web — 通知偏好頁（`/settings/notifications`）

### Task 3.1: API client＋hooks（樂觀更新＋回滾）

**Files:**
- Create: `apps/web/lib/api/notification-preferences.ts`
- Create: `apps/web/lib/hooks/use-notification-preferences.ts`
- Test: `apps/web/lib/api/notification-preferences.test.ts`（比照 `lib/api/channels.test.ts`）

**TODO:**
- [x] client：`getNotificationPreferences()`／`updateNotificationPreferences(updates)`／`resetNotificationPreferences()`（型別取 `@ims/api-types`）
- [x] hooks：query key（如 `["notification-preferences"]`）；`onMutate`＝取消進行中查詢＋快照＋樂觀套用；`onError`＝回滾＋toast；`onSuccess`＝以伺服器 snapshot `setQueryData`＋「偏好已更新」toast
- [x] 測試：樂觀套用、錯誤回滾、snapshot 覆蓋

**Commands:**
- `pnpm -F @ims/web test lib/api/notification-preferences`

### Task 3.2: 偏好矩陣 UI（三群組卡＋§5.4 狀態）

**Files:**
- Create: `apps/web/components/settings/notification-preferences-panel.tsx`
- Create: `apps/web/app/(app)/settings/notifications/page.tsx`（`SettingsPageShell`＋panel）
- Test: `apps/web/components/settings/notification-preferences-panel.test.tsx`、`apps/web/app/(app)/settings/notifications/page.test.tsx`

**TODO:**
- [x] 三群組卡（§5.4）：物品提醒（low_stock／expiring_soon／expired）｜借還與協作（loan_*／transfer.*／group_invite）｜系統與報表（report_ready／system）
- [x] 桌面＝矩陣表（列＝類型、欄＝5 管道 toggle）；`md` 以下＝每類型卡片（管道 toggle 列）——§5.7 寬表格卡片化
- [x] 樂觀切換＋失敗回滾＋toast（aria-live）；成功 toast「偏好已更新」
- [x] 鎖定列：鎖頭 icon＋tooltip「此類通知不可關閉」，toggle disabled
- [x] 未綁定（line／telegram／web_push）：該欄（桌）／列（卡）disabled＋「前往綁定」連 `/settings/channels`
- [x] 空狀態（`has_custom=false`）：頂部摘要條「目前使用預設值」＋副文精確描述預設（比照 §5.4『目前等同全部開啟』語意，含到期提醒例外）；有覆寫時隱藏
- [x] 「重置為預設」按鈕（`has_custom` 時顯示）：確認對話框 → DELETE → toast「已重置為預設」
- [x] LOADING＝三群組卡 skeleton；載入失敗＝頁面錯誤＋重試
- [x] 測試：矩陣 render、toggle→樂觀＋mutation 呼叫、錯誤回滾、鎖定 disabled＋tooltip、未綁定 disabled＋連結、空狀態摘要條出現／消失、重置流程

**Commands:**
- `pnpm -F @ims/web test`

### Task 3.3: i18n／深色／a11y

**Files:**
- Modify: `apps/web/messages/zh-TW.json`、`apps/web/messages/en.json`
- Modify: 上述新元件（文案與樣式）

**TODO:**
- [x] `settings.notificationPreferences.*`：群組名、11 類型名、5 管道名、狀態文案、tooltip、按鈕、toast（zh-TW＋en 全鍵對齊）
- [x] 深色模式以既有 token 檢查對比（不新增語義色）
- [x] a11y（§5.7）：toggle 鍵盤可達、tap target ≥44px、icon-only 必有 aria-label、toast aria-live、狀態不只用顏色（鎖頭 icon＋tooltip 文字）
- [x] 桌面／行動斷點實機檢查（實作期以瀏覽器截圖；見 Final Verification 視覺走查）

**Commands:**
- `pnpm -F @ims/web test && pnpm -F @ims/web typecheck`

---

## Phase 4: e2e＋文件

### Task 4.1: e2e — 偏好切換持久化＋零回歸

**Files:**
- Modify: `apps/web/tests/settings.spec.ts`（延伸）
- Create: `apps/web/tests/notification-preferences.spec.ts`

**TODO:**
- [x] 登入 → `/settings/notifications`：三群組卡 render；切換 `low_stock`×email → toast → 重載後仍為關
- [x] 鎖定列 toggle 不可操作（disabled）
- [x] 未綁定（line）欄位 disabled＋「前往綁定」→ 到達 `/settings/channels`
- [x] 「重置為預設」→ 回復預設（摘要條再現）
- [x] 通知零回歸：`notifications.spec.ts` 維持綠（站內未讀／已讀流程不受影響）

**Commands:**
- `docker compose up -d` → `cd apps/web && pnpm exec playwright test`

### Task 4.2: 文件收尾

**Files:**
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.23]`）
- Modify: `docs/v2-roadmap.md`（Phase 23 列）
- Modify: 本計畫（勾選＋Final Verification 環境註記）

**TODO:**
- [x] CHANGELOG：設定 IA 重構（含零回歸驗證）＋通知偏好中心＋API 契約＋行為整合
- [x] roadmap Phase 表更新；本計畫全部勾選
- [x] `git diff --check`；桌面（1280）＋行動（390）視覺走查：索引頁、偏好頁（表／卡）、鎖定與未綁定態、空狀態、toast、深色

---

## API 契約（定案）

**GET `/api/notifications/preferences`** → 200

```json
{
  "types": [
    {"key": "low_stock",       "group": "items",  "locked": false},
    {"key": "expiring_soon",   "group": "items",  "locked": false},
    {"key": "expired",         "group": "items",  "locked": false},
    {"key": "loan_open",       "group": "collab", "locked": false},
    {"key": "loan_overdue",    "group": "collab", "locked": false},
    {"key": "loan_returned",   "group": "collab", "locked": false},
    {"key": "transfer.request","group": "collab", "locked": false},
    {"key": "transfer.accepted","group": "collab","locked": false},
    {"key": "group_invite",    "group": "collab", "locked": true},
    {"key": "report_ready",    "group": "system", "locked": false},
    {"key": "system",          "group": "system", "locked": true}
  ],
  "channels": ["in_app", "email", "line", "telegram", "web_push"],
  "matrix": {
    "low_stock": {"in_app": true, "email": true, "line": true, "telegram": true, "web_push": true},
    "expired":   {"in_app": true, "email": false, "line": false, "telegram": false, "web_push": true}
  },
  "has_custom": false,
  "channel_availability": {"in_app": true, "email": true, "line": false, "telegram": false, "web_push": false}
}
```

- `matrix`＝有效值（預設＋覆寫展開）；`has_custom`＝存在任一覆寫列
- `channel_availability`＝使用者側綁定（盤點定案 7）

**PUT `/api/notifications/preferences`** body：

```json
{"updates": [{"type": "low_stock", "channel": "email", "enabled": false}]}
```

→ 200（同 GET 形狀）
- 422：未知 type／channel；鎖定列 `enabled=false`；`updates: []` → 200 no-op（冪等）
- `enabled == 預設值` → 覆寫列刪除（表保持精簡）

**DELETE `/api/notifications/preferences`** → 200（同 GET 形狀；全覆寫清除＝重置為預設）
- **路由宣告順序必須先於 `DELETE /api/notifications/{notification_id}`**

**行為整合**
- `emit()`：`in_app` 開→建列；關→不建（回 None）；外部管道照走（各自過濾）
- `deliver_all(..., type=…)`：逐管道 `is_enabled` 過濾；鎖定類型視為開啟
- 預設值＝現行行為（零回歸）；偏好查詢失敗 fail-soft 視為開啟

---

## §5.4 狀態契約（Phase 23 新介面）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 設定首頁索引（23） | 群組卡 skeleton ×4 | 不適用（恆有頁面）；`useMe` 失敗→頁面錯誤＋重試 | 頁面錯誤＋「重試」 | 卡片連結鍵盤可達、hover 態 | 非 admin：管理群組不渲染；BootstrapAdminButton 僅非 admin 顯示 |
| 通知偏好（23） | 群組卡 skeleton ×3 | 未設定過→摘要條「目前使用預設值」＋三群組卡（物品提醒／借還與協作／系統與報表） | 切換失敗回滾＋toast；載入失敗→頁面錯誤＋重試 | 樂觀切換＋「偏好已更新」toast（aria-live） | 未綁定管道→該欄禁用＋「前往綁定」；鎖定列→鎖頭＋tooltip |

---

## 驗收對照（roadmap §六 → 本計畫）

- 偏好過濾單元測試（emit／deliver_all 各情境、不可關類別強制）→ T2.2、T2.3
- API 契約：GET 回傳矩陣結構（類型×管道）、PUT→GET 反映、未知 type／管道拒絕 → T2.4
- UI 測試（切換、儲存、重置）→ T3.2
- 既有通知流程零回歸 → T2.3 全綠＋T4.1 `notifications.spec.ts`
- CRITICAL 設定 IA 回歸：10 面板子路由化 smoke（render＋核心操作）、`/settings/taxonomy`、admin-only 可見性（非 admin 隱藏、BootstrapAdminButton 首次引導）、以既有 3 面板測試為基礎擴充、`navigation.spec.ts` 加設定子路由可達性抽查 → T1.1–T1.3
- §5.2 硬上限：首層群組 4（≤4）、各群組頁面 3／2／5／2（≤6）

## Final Verification

- [x] `cd apps/api && uv run --extra test pytest -q` 全綠（560 passed；520 既有零回歸）
- [x] `pnpm -F @ims/web test`、`pnpm -F @ims/web typecheck` 全綠（258 passed／61 檔；typecheck 0 errors）
- [x] `docker compose up -d --build api web` → `cd apps/web && pnpm exec playwright test`：35 passed／14 spec（含新增 4 情境）全綠
  - 本機 bundled chromium 安裝異常（下載僅 204K stub、spawn `EBADARCH`；以鏡像站 `--force` 重裝仍未恢復）：以系統 Chrome 臨時 config（`playwright.chrome.config.ts`，不入版控、收尾刪除）等價驗證
  - 既有 `items-crud`／`collaboration` 於平行 2 workers 下偶發 30s 超時；trace 證實為測試端資料競爭（collaboration：Bob 的 transfers 列表請求賽跑 Alice 的 POST，回 `[]` 後無重取），當下 API 無任何 5xx／例外；單跑穩定、多次全套 35 passed，與本 Phase 無關
- [x] `pnpm -F @ims/api-types gen:types` 後無未預期 diff（重生成後 `packages/api-types/` diff 為空）
- [x] 視覺走查（桌面 1280＋行動 390，腳本化截圖）：設定索引四群組卡（非 admin 隱藏管理群組＋BootstrapAdminButton）、偏好預設態（摘要條）／自訂態（重置鈕切換＋「偏好已更新」toast）／重置 AlertDialog／深色矩陣（對比達標）／行動 390 卡片（鎖定＋未綁定態）✓
- [x] `git diff --check`；CHANGELOG／roadmap／本計畫勾選完成
- [x] 收尾：commit 齊、merge 回 main、`docker compose down`（本 commit 後執行）
