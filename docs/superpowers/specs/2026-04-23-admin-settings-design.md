# 管理與設定（Admin & Settings）設計 — v2 子專案 #8

## 目標

讓使用者可在 `/settings` 下管理自己的個人資料、密碼、偏好；管理員（`is_admin = true`）多一個 tab 管理全站使用者（啟用/停用、寄送測試通知）。

## 範圍

**In scope：**
- `GET/PATCH /api/users/me`：取得/更新自己的 email 與 username（皆做唯一性檢查）
- `POST /api/users/me/change-password`：需提供當前密碼與新密碼
- 既有 `GET/PUT /api/users/me/preferences`（theme + language）保持不變，前端包裝成 Preferences tab
- Admin 身份檢查：新增 `get_current_admin` dependency → 非 admin 回 403
- `GET /api/admin/users`：列出全部使用者（限 admin）
- `PATCH /api/admin/users/{id}`：切換 `is_active`（限 admin；不可停用自己；不可停用最後一位 admin）
- `POST /api/admin/users/{id}/test-notification`：呼叫 `notifications_service.emit()` 送出 `admin.test` 類型通知
- `POST /api/auth/bootstrap-admin`：當系統尚無 admin 時，允許當前使用者自我提升為 admin（一次性）
- 前端 `/settings` 頁面改為 tabs：個人資料 / 密碼 / 偏好 / （admin 才出現）管理員
- i18n（zh-TW、en）
- 不需要 Alembic migration

**Out of scope（明確延後）：**
- 角色系統（除 admin 以外的權限層級）
- 前端角色升降（非 admin 升為 admin 需透過 bootstrap 或 DB 編輯）
- 使用者刪除（停用即可）
- 密碼重設（需要 email 基礎設施）
- 2FA、OAuth、API tokens
- 頭像 / display_name（留待圖片基礎設施專案）
- 管理員操作審計（audit log）
- 管理員模擬登入（impersonation）

## API

### 使用者自身（non-admin 可用）

| Method | Path | Body / Response |
|---|---|---|
| GET | `/api/users/me` | `UserPublic` — 自己的 id/email/username/is_active/is_admin/created_at |
| PATCH | `/api/users/me` | `UserProfileUpdate { email?, username? }` → `UserPublic`；409 若 email/username 衝突 |
| POST | `/api/users/me/change-password` | `PasswordChange { current_password, new_password }` → `{ success: true }`；422 若 current_password 錯；422 若 new_password < 8 chars |
| GET | `/api/users/me/preferences` | 既有，不改 |
| PUT | `/api/users/me/preferences` | 既有，不改 |

### Bootstrap admin（未認證才能在 0 admin 系統下呼叫）

| Method | Path | Body / Response |
|---|---|---|
| POST | `/api/auth/bootstrap-admin` | 認證 required；若系統已有 ≥1 個 admin → 409；否則將當前使用者 `is_admin = true` 並回 `UserPublic` |

### Admin 專屬

使用 `get_current_admin` dependency：

```python
# app/auth/dependencies.py
async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return user
```

| Method | Path | Body / Response |
|---|---|---|
| GET | `/api/admin/users` | `list[UserPublic]` — 全部使用者，按 `created_at ASC` |
| PATCH | `/api/admin/users/{user_id}` | `UserAdminUpdate { is_active: bool }` → `UserPublic`；422 若試圖停用自己；422 若停用會造成 0 admin |
| POST | `/api/admin/users/{user_id}/test-notification` | 無 body → `{ notified: true }`；emit 一則 `admin.test` 通知到目標使用者 |

通知 payload：
- type: `admin.test`
- title: `「{admin_username}」寄送的測試通知`
- body: `此為管理員測試通知，若您看到此訊息代表通知通道運作正常。`
- link: `/notifications`

## Schemas

```python
# app/schemas/user.py 新增
class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)

    model_config = ConfigDict(extra="forbid")


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class UserAdminUpdate(BaseModel):
    is_active: bool

    model_config = ConfigDict(extra="forbid")
```

## 服務層

新增 `app/services/admin_service.py`：

```python
async def list_users(session: AsyncSession) -> list[User]: ...

async def set_active(
    session: AsyncSession, admin_user: User, target_user_id: UUID, is_active: bool
) -> User:
    # 檢查 target != admin_user
    # 若要停用：檢查停用後 admin 數量 > 0
    # 更新 + commit + refresh
    ...

async def count_active_admins(session: AsyncSession) -> int: ...

async def send_test_notification(
    session: AsyncSession, admin_user: User, target_user_id: UUID
) -> None:
    # 驗證 target 存在
    # 呼叫 notifications_service.emit(...)
```

新增 `app/services/profile_service.py`：

```python
async def update_profile(
    session: AsyncSession, user: User, body: UserProfileUpdate
) -> User:
    # 若更新 email：查 email 是否被其他人佔用 → 409
    # 若更新 username：查 username 是否被其他人佔用 → 409
    # 更新 + commit + refresh


async def change_password(
    session: AsyncSession, user: User, body: PasswordChange
) -> None:
    # 驗證 current_password（verify_password）
    # 若不符 → 422
    # 更新 password_hash = hash_password(new_password)
    # commit


async def bootstrap_admin_if_none(
    session: AsyncSession, user: User
) -> User:
    # 計算目前 admin 數量
    # 若 > 0 → 409
    # 否則 user.is_admin = True；commit
```

## 前端

### `/settings` 頁面

重寫 `apps/web/app/(app)/settings/page.tsx` 為 tabs 版：

```tsx
<Tabs defaultValue="profile">
  <TabsList>
    <TabsTrigger value="profile">{t("settings.tabs.profile")}</TabsTrigger>
    <TabsTrigger value="password">{t("settings.tabs.password")}</TabsTrigger>
    <TabsTrigger value="preferences">{t("settings.tabs.preferences")}</TabsTrigger>
    {currentUser.is_admin ? (
      <TabsTrigger value="admin">{t("settings.tabs.admin")}</TabsTrigger>
    ) : null}
  </TabsList>
  <TabsContent value="profile"><ProfileForm /></TabsContent>
  <TabsContent value="password"><PasswordForm /></TabsContent>
  <TabsContent value="preferences"><PreferencesForm /></TabsContent>
  {currentUser.is_admin ? (
    <TabsContent value="admin"><AdminUsersPanel /></TabsContent>
  ) : null}
</Tabs>
```

另加 conditional CTA：如系統尚無 admin（以 current user 的 `is_admin === false` 時，顯示「成為首位管理員」按鈕，呼叫 `/api/auth/bootstrap-admin`）。

### 元件

- `apps/web/components/settings/profile-form.tsx`：兩個欄位 + 儲存按鈕；使用 `useUpdateProfile` mutation；失敗 toast
- `apps/web/components/settings/password-form.tsx`：current + new + confirm，前端檢查 new === confirm；使用 `useChangePassword`；成功後清空表單 + toast
- `apps/web/components/settings/preferences-form.tsx`：theme (radio group)、language (select)；沿用既有 `/api/users/me/preferences`
- `apps/web/components/settings/admin-users-panel.tsx`：表格（username、email、is_active、is_admin、created_at）+ 每行 `[啟用/停用]` 按鈕 + `[寄送測試]` 按鈕
- `apps/web/components/settings/bootstrap-admin-button.tsx`：當 `currentUser.is_admin === false` 且沒有其他 admin 時顯示

### API 客戶端 + hooks

- `apps/web/lib/api/profile.ts`：`getMe`, `updateProfile`, `changePassword`, `bootstrapAdmin`
- `apps/web/lib/api/admin.ts`：`listUsers`, `setUserActive`, `sendTestNotification`
- `apps/web/lib/hooks/use-profile.ts`：`useMe`, `useUpdateProfile`, `useChangePassword`, `useBootstrapAdmin`
- `apps/web/lib/hooks/use-admin.ts`：`useAdminUsers`, `useSetUserActive`, `useSendTestNotification`

### i18n 新增鍵

```
settings.title
settings.tabs.profile
settings.tabs.password
settings.tabs.preferences
settings.tabs.admin
settings.profile.email
settings.profile.username
settings.profile.save
settings.profile.saved
settings.password.current
settings.password.new
settings.password.confirm
settings.password.mismatch
settings.password.save
settings.password.saved
settings.password.wrongCurrent
settings.preferences.theme
settings.preferences.language
settings.preferences.saved
settings.admin.emptyTable
settings.admin.actions.toggleActive
settings.admin.actions.sendTest
settings.admin.status.active
settings.admin.status.inactive
settings.admin.status.admin
settings.admin.errors.cannotDeactivateSelf
settings.admin.errors.cannotRemoveLastAdmin
settings.admin.testSent
settings.bootstrap.prompt
settings.bootstrap.confirm
settings.bootstrap.success
```

## 錯誤處理

- 非 admin 存取 `/api/admin/*` → 403
- 試圖停用自己 → 422 with message `"cannot deactivate self"`
- 試圖停用最後一位 admin → 422 with message `"cannot deactivate last admin"`
- 更新 email/username 衝突 → 409
- 密碼 change current 錯誤 → 422
- bootstrap 時系統已有 admin → 409

前端：
- Mutation 失敗時讀 `ApiError.body.detail`，以 toast 呈現翻譯過的錯誤
- 特定錯誤字串（如 `"cannot deactivate last admin"`）對應到 i18n key

## 測試

### 後端（~30 個新測試）

- `test_profile_service.py`（8）：update email/username；衝突 409；change_password 成功、wrong-current 422、new<8 422；bootstrap 當 0 admin、當 ≥1 admin 409
- `test_admin_service.py`（6）：list_users；set_active 停用他人成功、停用自己 422、停用最後 admin 422；count_active_admins；send_test_notification emit
- `test_users_routes.py`（既有檔擴充）：`GET /api/users/me`、`PATCH /api/users/me`、`change-password` 3 path
- `test_admin_routes.py`（新）：`GET /api/admin/users` auth + admin-only 403、`PATCH` toggle 成功/422、`test-notification` 檢查收件方 notifications 列表
- `test_bootstrap_admin.py`（2）：第一次成功、第二次 409

### 前端 vitest（3 新測試）

- `profile-form.test.tsx`：輸入改變 + 提交呼叫 mutation
- `password-form.test.tsx`：new !== confirm 時禁用送出
- `admin-users-panel.test.tsx`：render 3 row + toggle 呼叫 mutation

### E2E（`apps/web/tests/settings.spec.ts`）

1. Register → 進 `/settings` → profile tab 顯示 current 資料 → 改 email → 儲存 → reload → 新值呈現
2. Change password → logout → login with new password 成功
3. Bootstrap admin：註冊新 user → 點「成為首位管理員」→ 確認 → admin tab 出現
4. Admin 在 `/settings?tab=admin` 看到 user list → 停用另一個 user → API 回 200 + row 反映

## 成功指標

- 使用者可編輯 email / username，衝突正確提示
- 使用者可改密碼，登入流程使用新密碼
- Preferences tab 正常切換主題與語言
- 系統管理員可在 `/settings` 的 admin tab 列出、停用/啟用、發送測試通知
- 非 admin 無法進入 `/settings` 的 admin tab（UI 隱藏）且呼叫 admin API 時得 403
- 首次 bootstrap admin 流程可運作；第二次呼叫被拒絕

## 遷移

無 DB schema 變更；不需要新 Alembic migration。
