# IMS v2 #1 Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立完整 design tokens + auth-aware 主題同步 + 30 個新 shadcn 元件 + dev-only 展示頁，為 #2–#9 功能子專案鋪設計基礎。

**Architecture:** next-themes 驅動 `html.dark` class；use-theme hook 包裝 next-themes 並在登入時與 `/api/users/me/preferences` 同步；後端以 JSONB 儲存偏好並支援未來擴充；shadcn CLI 逐個加元件，showcase 頁依元件分類拆檔。

**Tech Stack:** next-themes 0.3, sonner 1.5, cmdk 1.0, @hookform/resolvers 3.9, react-hook-form 7.53（#0 已裝）, zod 3.23（#0 已裝）, Radix primitives（shadcn 間接引入）, SQLAlchemy JSONB, Pydantic v2。

**Base:** 分支 `claude/modest-newton-942a6d`，HEAD `3988f71`（spec commit）。

---

## Task 1: Design tokens 擴充

**Files:**
- Modify: `apps/web/app/globals.css`
- Verify: `apps/web/tailwind.config.ts`

- [ ] **Step 1.1: 覆寫 `globals.css` tokens**

完整替換 `apps/web/app/globals.css` 的 `@layer base` 區塊（保留 `@tailwind` 指令）：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222 47% 11%;

    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;

    --popover: 0 0% 100%;
    --popover-foreground: 222 47% 11%;

    --primary: 262 83% 58%;
    --primary-foreground: 210 20% 98%;

    --secondary: 210 40% 96%;
    --secondary-foreground: 222 47% 11%;

    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;

    --accent: 210 40% 96%;
    --accent-foreground: 222 47% 11%;

    --destructive: 0 84% 60%;
    --destructive-foreground: 210 20% 98%;

    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 262 83% 58%;

    --radius: 0.5rem;
  }

  .dark {
    --background: 222 47% 6%;
    --foreground: 210 20% 98%;

    --card: 222 47% 8%;
    --card-foreground: 210 20% 98%;

    --popover: 222 47% 8%;
    --popover-foreground: 210 20% 98%;

    --primary: 263 70% 65%;
    --primary-foreground: 222 47% 11%;

    --secondary: 217 33% 17%;
    --secondary-foreground: 210 20% 98%;

    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;

    --accent: 217 33% 17%;
    --accent-foreground: 210 20% 98%;

    --destructive: 0 72% 51%;
    --destructive-foreground: 210 20% 98%;

    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 263 70% 65%;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
}
```

- [ ] **Step 1.2: 確認 `tailwind.config.ts` colors 映射齊全**

Read `apps/web/tailwind.config.ts`，確保 `theme.extend.colors` 已包含以下映射（若 #0 已設定則跳過）：

```ts
colors: {
  border: "hsl(var(--border))",
  input: "hsl(var(--input))",
  ring: "hsl(var(--ring))",
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  primary: {
    DEFAULT: "hsl(var(--primary))",
    foreground: "hsl(var(--primary-foreground))",
  },
  secondary: {
    DEFAULT: "hsl(var(--secondary))",
    foreground: "hsl(var(--secondary-foreground))",
  },
  destructive: {
    DEFAULT: "hsl(var(--destructive))",
    foreground: "hsl(var(--destructive-foreground))",
  },
  muted: {
    DEFAULT: "hsl(var(--muted))",
    foreground: "hsl(var(--muted-foreground))",
  },
  accent: {
    DEFAULT: "hsl(var(--accent))",
    foreground: "hsl(var(--accent-foreground))",
  },
  popover: {
    DEFAULT: "hsl(var(--popover))",
    foreground: "hsl(var(--popover-foreground))",
  },
  card: {
    DEFAULT: "hsl(var(--card))",
    foreground: "hsl(var(--card-foreground))",
  },
},
borderRadius: {
  lg: "var(--radius)",
  md: "calc(var(--radius) - 2px)",
  sm: "calc(var(--radius) - 4px)",
},
```

- [ ] **Step 1.3: 驗證**

```bash
pnpm -F @ims/web build
```

預期：通過。

- [ ] **Step 1.4: Commit**

```bash
git add apps/web/app/globals.css apps/web/tailwind.config.ts
git commit -m "feat(web): expand design tokens with slate + deep purple (#1)"
```

---

## Task 2: Inter font 載入

**Files:**
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/tailwind.config.ts`（font family 映射）

- [ ] **Step 2.1: 加 Inter 字體**

Modify `apps/web/app/layout.tsx`：

```tsx
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "./providers"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
})

export const metadata: Metadata = {
  title: "物品管理系統 v2",
  description: "IMS v2 — 家庭物品管理",
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

若 `./providers` 尚不存在，本 task 可以先 inline 成一個簡單 wrapper，Task 4 再擴充（但其實會在 Task 3 建立 Providers — 本 Task 只寫 `<>{children}</>` 佔位，Commit 訊息提到會在後續完整補）。

簡化：暫時直接 `<body className={...}>{children}</body>` 跳過 Providers 載入，等 Task 3 寫好 Providers 再接。

- [ ] **Step 2.2: 設定 Tailwind font family**

Modify `apps/web/tailwind.config.ts` 的 `theme.extend`：

```ts
fontFamily: {
  sans: [
    "var(--font-sans)",
    "ui-sans-serif",
    "system-ui",
    "-apple-system",
    "BlinkMacSystemFont",
    "PingFang TC",
    "Microsoft JhengHei",
    "Noto Sans TC",
    "sans-serif",
  ],
},
```

- [ ] **Step 2.3: 驗證**

```bash
pnpm -F @ims/web build
```

預期：通過；首頁渲染時字體使用 Inter（Latin）與系統中文字體。

- [ ] **Step 2.4: Commit**

```bash
git add apps/web/app/layout.tsx apps/web/tailwind.config.ts
git commit -m "feat(web): load Inter via next/font and configure font stack (#1)"
```

---

## Task 3: next-themes Provider

**Files:**
- Create: `apps/web/app/providers.tsx`
- Modify: `apps/web/app/layout.tsx`（改為引用新 Providers）
- Modify: `apps/web/package.json`（新增 `next-themes@0.3.0`）

- [ ] **Step 3.1: 安裝 next-themes**

```bash
pnpm -F @ims/web add next-themes@^0.3.0
```

- [ ] **Step 3.2: 建立 Providers**

Create `apps/web/app/providers.tsx`：

```tsx
"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "next-themes"
import { useState } from "react"

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 3.3: layout.tsx 接上 Providers**

Modify `apps/web/app/layout.tsx`（覆寫 body）：

```tsx
    <html lang="zh-Hant" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
```

- [ ] **Step 3.4: 驗證**

```bash
pnpm -F @ims/web build
```

預期：通過。`suppressHydrationWarning` 防止 next-themes SSR mismatch。

- [ ] **Step 3.5: Commit**

```bash
git add apps/web/app/providers.tsx apps/web/app/layout.tsx apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): wrap app with ThemeProvider + QueryClientProvider (#1)"
```

---

## Task 4: User.preferences 欄位 + Migration

**Files:**
- Modify: `apps/api/app/models/user.py`
- Create: `apps/api/alembic/versions/0002_user_preferences.py`

- [ ] **Step 4.1: 新增 preferences column**

Read `apps/api/app/models/user.py`，加入 import 與欄位：

```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON, text
# ...
# 在 User class 適當位置新增（建議 created_at 之前）
preferences: Mapped[dict] = mapped_column(
    JSONB().with_variant(JSON(), "sqlite"),
    nullable=False,
    server_default=text("'{}'"),
    default=dict,
)
```

（JSONB 僅 Postgres 支援；SQLite 測試用 JSON fallback，與 Task 4 的 GUID dialect-variant 同策略。）

- [ ] **Step 4.2: Alembic migration**

Create `apps/api/alembic/versions/0002_user_preferences.py`：

```python
"""add preferences column to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "preferences",
            JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferences")
```

- [ ] **Step 4.3: 執行 migration 測試（SQLite memory）**

```bash
cd apps/api
uv run pytest tests/test_auth_routes.py -q
```

預期：現有 7 個測試仍通過（migration 會在 conftest 中自動跑；preferences 欄位存在但不影響現有行為）。

- [ ] **Step 4.4: Commit**

```bash
cd ../..
git add apps/api/app/models/user.py apps/api/alembic/versions/0002_user_preferences.py
git commit -m "feat(api): add preferences JSONB column to users (#1)"
```

---

## Task 5: Preferences Pydantic schemas

**Files:**
- Create: `apps/api/app/schemas/preferences.py`
- Create: `apps/api/tests/test_preferences_schemas.py`

- [ ] **Step 5.1: TDD — 寫測試**

Create `apps/api/tests/test_preferences_schemas.py`：

```python
import pytest
from pydantic import ValidationError

from app.schemas.preferences import PreferencesRead, PreferencesUpdate


class TestPreferencesRead:
    def test_default_theme_is_system(self):
        prefs = PreferencesRead()
        assert prefs.theme == "system"

    def test_accepts_valid_theme(self):
        prefs = PreferencesRead(theme="dark")
        assert prefs.theme == "dark"

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesRead(theme="neon")

    def test_allows_extra_keys(self):
        prefs = PreferencesRead(theme="light", language="zh-TW")
        assert prefs.model_dump()["language"] == "zh-TW"


class TestPreferencesUpdate:
    def test_all_fields_optional(self):
        PreferencesUpdate()  # should not raise

    def test_theme_only(self):
        update = PreferencesUpdate(theme="dark")
        assert update.model_dump(exclude_none=True) == {"theme": "dark"}

    def test_allows_extra_keys(self):
        update = PreferencesUpdate(notifications_enabled=True)
        assert update.model_dump(exclude_none=True)["notifications_enabled"] is True

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesUpdate(theme="aqua")
```

- [ ] **Step 5.2: 確認測試紅**

```bash
cd apps/api
uv run pytest tests/test_preferences_schemas.py -q
```

預期：`ModuleNotFoundError: No module named 'app.schemas.preferences'`

- [ ] **Step 5.3: 實作 schemas**

Create `apps/api/app/schemas/preferences.py`：

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict

Theme = Literal["system", "light", "dark"]


class PreferencesRead(BaseModel):
    theme: Theme = "system"

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None

    model_config = ConfigDict(extra="allow")
```

- [ ] **Step 5.4: 綠**

```bash
uv run pytest tests/test_preferences_schemas.py -q
```

預期：4+4=8 個測試通過。

- [ ] **Step 5.5: Commit**

```bash
cd ../..
git add apps/api/app/schemas/preferences.py apps/api/tests/test_preferences_schemas.py
git commit -m "feat(api): add preferences Pydantic schemas (#1)"
```

---

## Task 6: Preferences repository + service

**Files:**
- Create: `apps/api/app/repositories/preferences_repository.py`
- Create: `apps/api/app/services/preferences_service.py`
- Create: `apps/api/tests/test_preferences_service.py`

- [ ] **Step 6.1: TDD — 寫測試**

Create `apps/api/tests/test_preferences_service.py`：

```python
from uuid import uuid4

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.schemas.preferences import PreferencesUpdate
from app.services.preferences_service import (
    get_preferences,
    update_preferences,
)


@pytest.fixture
async def user(db_session):
    user = User(
        email=f"prefs_{uuid4().hex[:8]}@example.com",
        username=f"prefs_{uuid4().hex[:8]}",
        password_hash=hash_password("secret1234"),
        preferences={},
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


class TestGetPreferences:
    async def test_empty_returns_default_theme(self, db_session, user):
        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs.theme == "system"

    async def test_existing_theme_returned(self, db_session, user):
        user.preferences = {"theme": "dark"}
        await db_session.flush()
        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs.theme == "dark"


class TestUpdatePreferences:
    async def test_sets_theme(self, db_session, user):
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(theme="light"),
        )
        assert result.theme == "light"

    async def test_merges_not_overwrites(self, db_session, user):
        user.preferences = {"theme": "dark", "language": "zh-TW"}
        await db_session.flush()
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(theme="light"),
        )
        assert result.theme == "light"
        assert result.model_dump()["language"] == "zh-TW"

    async def test_ignores_none_fields(self, db_session, user):
        user.preferences = {"theme": "dark"}
        await db_session.flush()
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(),
        )
        assert result.theme == "dark"
```

- [ ] **Step 6.2: 紅**

```bash
cd apps/api
uv run pytest tests/test_preferences_service.py -q
```

預期：ModuleNotFoundError。

- [ ] **Step 6.3: Repository**

Create `apps/api/app/repositories/preferences_repository.py`：

```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_raw_preferences(session: AsyncSession, user_id: UUID) -> dict:
    stmt = select(User.preferences).where(User.id == user_id)
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return value or {}


async def set_raw_preferences(
    session: AsyncSession, user_id: UUID, value: dict
) -> dict:
    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one()
    user.preferences = value
    await session.flush()
    return user.preferences
```

- [ ] **Step 6.4: Service**

Create `apps/api/app/services/preferences_service.py`：

```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import preferences_repository
from app.schemas.preferences import PreferencesRead, PreferencesUpdate


async def get_preferences(
    session: AsyncSession, *, user_id: UUID
) -> PreferencesRead:
    raw = await preferences_repository.get_raw_preferences(session, user_id)
    return PreferencesRead.model_validate(raw)


async def update_preferences(
    session: AsyncSession,
    *,
    user_id: UUID,
    update: PreferencesUpdate,
) -> PreferencesRead:
    current = await preferences_repository.get_raw_preferences(session, user_id)
    incoming = update.model_dump(exclude_none=True)
    merged = {**current, **incoming}
    saved = await preferences_repository.set_raw_preferences(
        session, user_id, merged
    )
    return PreferencesRead.model_validate(saved)
```

- [ ] **Step 6.5: 確保 `__init__.py` 可 import**

確認 `apps/api/app/repositories/__init__.py` 存在（若沒有則建立空檔）：

```python
# apps/api/app/repositories/__init__.py
```

- [ ] **Step 6.6: 綠**

```bash
uv run pytest tests/test_preferences_service.py -q
```

預期：5 個測試通過。

- [ ] **Step 6.7: Commit**

```bash
cd ../..
git add apps/api/app/repositories apps/api/app/services/preferences_service.py apps/api/tests/test_preferences_service.py
git commit -m "feat(api): preferences repository + service (#1)"
```

---

## Task 7: Preferences routes

**Files:**
- Create: `apps/api/app/routes/users.py`
- Modify: `apps/api/app/main.py`（註冊 router）
- Create: `apps/api/tests/test_preferences_routes.py`

- [ ] **Step 7.1: TDD — 寫 route 測試**

Create `apps/api/tests/test_preferences_routes.py`：

```python
import pytest


@pytest.fixture
async def auth_headers(client):
    """Register + login, return Bearer auth headers."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "prefs@example.com",
            "username": "prefs_user",
            "password": "secret1234",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "prefs_user", "password": "secret1234"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestGetPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/users/me/preferences")
        assert resp.status_code == 401

    async def test_returns_default_theme(self, client, auth_headers):
        resp = await client.get(
            "/api/users/me/preferences", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"theme": "system"}


class TestPutPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.put(
            "/api/users/me/preferences", json={"theme": "dark"}
        )
        assert resp.status_code == 401

    async def test_updates_theme(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark"},
        )
        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"

    async def test_merge_preserves_other_keys(self, client, auth_headers):
        await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark", "language": "zh-TW"},
        )
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "light"},
        )
        body = resp.json()
        assert body["theme"] == "light"
        assert body["language"] == "zh-TW"

    async def test_invalid_theme_returns_422(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "neon"},
        )
        assert resp.status_code == 422
```

- [ ] **Step 7.2: 紅**

```bash
cd apps/api
uv run pytest tests/test_preferences_routes.py -q
```

預期：failures（路由不存在 → 404）。

- [ ] **Step 7.3: Routes**

Create `apps/api/app/routes/users.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.routes.auth import require_user
from app.schemas.preferences import PreferencesRead, PreferencesUpdate
from app.services import preferences_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me/preferences", response_model=PreferencesRead)
async def get_my_preferences(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
) -> PreferencesRead:
    return await preferences_service.get_preferences(session, user_id=user.id)


@router.put("/me/preferences", response_model=PreferencesRead)
async def update_my_preferences(
    update: PreferencesUpdate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
) -> PreferencesRead:
    return await preferences_service.update_preferences(
        session, user_id=user.id, update=update
    )
```

**註：** `require_user` 可能位於 `app.routes.auth`；若不存在，改 import from `app.auth.dependencies` 或同等路徑。先 Read `apps/api/app/routes/auth.py` 確認。

- [ ] **Step 7.4: 確保 `app/services/__init__.py` export**

Read `apps/api/app/services/__init__.py`。若它不曾 import `preferences_service`，加一行：

```python
from . import auth_service, preferences_service  # noqa: F401
```

（若 `__init__.py` 是空的也 OK，改用 `from app.services import preferences_service` 直接引用。）

- [ ] **Step 7.5: 註冊 router**

Modify `apps/api/app/main.py`，在 create_app 中加入：

```python
from app.routes import auth, users  # 加 users

# ... 在既有的 app.include_router(auth.router) 之後：
app.include_router(users.router)
```

- [ ] **Step 7.6: 綠**

```bash
uv run pytest tests/test_preferences_routes.py -q
```

預期：5 個測試通過。

- [ ] **Step 7.7: 回歸**

```bash
uv run pytest -q
```

預期：原有 16 個（含 #0 最終修復）+ 8（schemas）+ 5（service）+ 5（routes）= 34 個測試通過。

- [ ] **Step 7.8: Commit**

```bash
cd ../..
git add apps/api/app/routes/users.py apps/api/app/services/__init__.py apps/api/app/main.py apps/api/tests/test_preferences_routes.py
git commit -m "feat(api): add /api/users/me/preferences endpoints (#1)"
```

---

## Task 8: 重新產生 api-types

**Files:**
- Regenerate: `packages/api-types/src/index.ts`、`packages/api-types/openapi.json`

- [ ] **Step 8.1: 產生**

```bash
pnpm -F @ims/api gen:types   # export OpenAPI to packages/api-types/openapi.json
pnpm -F @ims/api-types gen:types   # convert to TS
```

- [ ] **Step 8.2: 驗證 TS 有新路徑**

```bash
grep -q "/api/users/me/preferences" packages/api-types/src/index.ts && echo OK
```

預期：`OK`。

- [ ] **Step 8.3: web typecheck**

```bash
pnpm -F @ims/web typecheck
```

預期：綠。

- [ ] **Step 8.4: Commit（僅 openapi.json；`src/` 仍 gitignored）**

```bash
git add packages/api-types/openapi.json
git commit -m "chore(types): regenerate OpenAPI schema with preferences (#1)"
```

---

## Task 9: Frontend preferences hook

**Files:**
- Create: `apps/web/lib/preferences/use-preferences.ts`
- Create: `apps/web/lib/preferences/types.ts`

- [ ] **Step 9.1: Types**

Create `apps/web/lib/preferences/types.ts`：

```ts
import type { paths } from "@ims/api-types"

export type PreferencesRead =
  paths["/api/users/me/preferences"]["get"]["responses"]["200"]["content"]["application/json"]

export type PreferencesUpdate =
  paths["/api/users/me/preferences"]["put"]["requestBody"]["content"]["application/json"]

export type ThemePreference = "system" | "light" | "dark"
```

- [ ] **Step 9.2: Hook**

Create `apps/web/lib/preferences/use-preferences.ts`：

```ts
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"

import type { PreferencesRead, PreferencesUpdate } from "./types"

const KEY = ["preferences", "me"] as const

export function usePreferences() {
  const token = useAccessToken()
  return useQuery<PreferencesRead>({
    queryKey: KEY,
    queryFn: () =>
      apiFetch<PreferencesRead>("/users/me/preferences", { token }),
    enabled: Boolean(token),
    staleTime: 5 * 60_000,
  })
}

export function useUpdatePreferences() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation<PreferencesRead, Error, PreferencesUpdate>({
    mutationFn: (body) =>
      apiFetch<PreferencesRead>("/users/me/preferences", {
        method: "PUT",
        body: JSON.stringify(body),
        token,
      }),
    onSuccess: (data) => {
      qc.setQueryData(KEY, data)
    },
  })
}
```

- [ ] **Step 9.3: typecheck**

```bash
pnpm -F @ims/web typecheck
```

預期：綠。

- [ ] **Step 9.4: Commit**

```bash
git add apps/web/lib/preferences
git commit -m "feat(web): add preferences query + mutation hooks (#1)"
```

---

## Task 10: Auth-aware useTheme hook

**Files:**
- Create: `apps/web/lib/theme/use-theme.ts`
- Create: `apps/web/lib/theme/theme-sync.tsx`
- Modify: `apps/web/app/providers.tsx`（加入 `<ThemeSync />`）

- [ ] **Step 10.1: Hook 包裝**

Create `apps/web/lib/theme/use-theme.ts`：

```ts
"use client"

import { useTheme as useNextTheme } from "next-themes"
import { useCallback } from "react"

import {
  useUpdatePreferences,
  usePreferences,
} from "@/lib/preferences/use-preferences"
import type { ThemePreference } from "@/lib/preferences/types"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useThemePreference() {
  const { theme, setTheme: setNextTheme } = useNextTheme()
  const token = useAccessToken()
  const update = useUpdatePreferences()

  const setTheme = useCallback(
    (next: ThemePreference) => {
      setNextTheme(next)
      if (token) {
        update.mutate({ theme: next })
      }
    },
    [setNextTheme, token, update],
  )

  return {
    theme: (theme ?? "system") as ThemePreference,
    setTheme,
    isSyncing: update.isPending,
  }
}

export { usePreferences }
```

- [ ] **Step 10.2: ThemeSync component**

Create `apps/web/lib/theme/theme-sync.tsx`：

```tsx
"use client"

import { useTheme } from "next-themes"
import { useEffect, useRef } from "react"

import { usePreferences } from "@/lib/preferences/use-preferences"

export function ThemeSync() {
  const { data, isSuccess } = usePreferences()
  const { setTheme } = useTheme()
  const synced = useRef(false)

  useEffect(() => {
    if (!isSuccess || synced.current) return
    if (data?.theme) {
      setTheme(data.theme)
    }
    synced.current = true
  }, [isSuccess, data, setTheme])

  return null
}
```

- [ ] **Step 10.3: 接入 Providers**

Modify `apps/web/app/providers.tsx`，在 ThemeProvider 內加入 ThemeSync：

```tsx
import { ThemeSync } from "@/lib/theme/theme-sync"

// ...
<ThemeProvider ...>
  <ThemeSync />
  {children}
</ThemeProvider>
```

- [ ] **Step 10.4: typecheck + build**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

預期：通過。

- [ ] **Step 10.5: Commit**

```bash
git add apps/web/lib/theme apps/web/app/providers.tsx
git commit -m "feat(web): auth-aware theme sync with preferences API (#1)"
```

---

## Task 11: shadcn components batch 1 — Forms

**Files:**
- Create: `apps/web/components/ui/{input,label,textarea,select,checkbox,radio-group,switch,slider,form}.tsx`

- [ ] **Step 11.1: 批次安裝**

```bash
cd apps/web
pnpm dlx shadcn@latest add input label textarea select checkbox radio-group switch slider form --yes
cd ../..
```

若 CLI 互動提問，選：New York / Slate / CSS variables / tsx / `@/components/ui` / `@/lib/utils`。

- [ ] **Step 11.2: 檢查必要依賴**

Shadcn 會自動加入：`@radix-ui/react-label`, `@radix-ui/react-select`, `@radix-ui/react-checkbox`, `@radix-ui/react-radio-group`, `@radix-ui/react-switch`, `@radix-ui/react-slider`, `@radix-ui/react-slot`, `@hookform/resolvers`（若未裝）。

檢查：

```bash
grep -q '"@hookform/resolvers"' apps/web/package.json && echo OK
```

若 `@hookform/resolvers` 未自動安裝：

```bash
pnpm -F @ims/web add @hookform/resolvers@^3.9.0
```

- [ ] **Step 11.3: 驗證**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

預期：通過。

- [ ] **Step 11.4: Commit**

```bash
git add apps/web/components/ui apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): add shadcn form components (#1)"
```

---

## Task 12: shadcn components batch 2 — Overlays

**Files:**
- Create: `apps/web/components/ui/{dialog,sheet,popover,dropdown-menu,tooltip,alert-dialog}.tsx`

- [ ] **Step 12.1: 安裝**

```bash
cd apps/web
pnpm dlx shadcn@latest add dialog sheet popover dropdown-menu tooltip alert-dialog --yes
cd ../..
```

- [ ] **Step 12.2: 驗證**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

- [ ] **Step 12.3: Commit**

```bash
git add apps/web/components/ui apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): add shadcn overlay components (#1)"
```

---

## Task 13: shadcn components batch 3 — Feedback

**Files:**
- Create: `apps/web/components/ui/{sonner,alert,badge,skeleton,progress}.tsx`

- [ ] **Step 13.1: 安裝**

```bash
cd apps/web
pnpm dlx shadcn@latest add sonner alert badge skeleton progress --yes
cd ../..
```

注意：Toast 在 shadcn 新版已改用 `sonner`；CLI 將產生 `apps/web/components/ui/sonner.tsx`。

- [ ] **Step 13.2: 在 Providers 內加 Toaster**

Modify `apps/web/app/providers.tsx`，在 `<ThemeProvider>` 底下、`{children}` 後加入：

```tsx
import { Toaster } from "@/components/ui/sonner"

// ...
<ThemeProvider ...>
  <ThemeSync />
  {children}
  <Toaster richColors closeButton />
</ThemeProvider>
```

- [ ] **Step 13.3: 驗證**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

- [ ] **Step 13.4: Commit**

```bash
git add apps/web/components/ui apps/web/app/providers.tsx apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): add shadcn feedback components + Toaster (#1)"
```

---

## Task 14: shadcn components batch 4 — Navigation

**Files:**
- Create: `apps/web/components/ui/{tabs,breadcrumb,pagination,command}.tsx`

- [ ] **Step 14.1: 安裝**

```bash
cd apps/web
pnpm dlx shadcn@latest add tabs breadcrumb pagination command --yes
cd ../..
```

- [ ] **Step 14.2: 驗證**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

- [ ] **Step 14.3: Commit**

```bash
git add apps/web/components/ui apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): add shadcn navigation components (#1)"
```

---

## Task 15: shadcn components batch 5 — Data display

**Files:**
- Create: `apps/web/components/ui/{card,table,avatar,separator,accordion,scroll-area}.tsx`

- [ ] **Step 15.1: 安裝**

```bash
cd apps/web
pnpm dlx shadcn@latest add card table avatar separator accordion scroll-area --yes
cd ../..
```

- [ ] **Step 15.2: 驗證**

```bash
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

- [ ] **Step 15.3: Commit**

```bash
git add apps/web/components/ui apps/web/package.json pnpm-lock.yaml
git commit -m "feat(web): add shadcn data-display components (#1)"
```

---

## Task 16: `/__dev/components` 展示頁 — 骨架 + 守衛

**Files:**
- Create: `apps/web/app/__dev/components/page.tsx`
- Create: `apps/web/app/__dev/components/section.tsx`
- Create: `apps/web/app/__dev/components/dev-theme-toggle.tsx`

- [ ] **Step 16.1: DevThemeToggle**

Create `apps/web/app/__dev/components/dev-theme-toggle.tsx`：

```tsx
"use client"

import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

export function DevThemeToggle() {
  const { theme, setTheme } = useTheme()
  const next = theme === "dark" ? "light" : "dark"
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(next)}
      aria-label={`切換到 ${next === "dark" ? "深色" : "淺色"}模式`}
    >
      切換 {next === "dark" ? "深色" : "淺色"}
    </Button>
  )
}
```

- [ ] **Step 16.2: Section wrapper**

Create `apps/web/app/__dev/components/section.tsx`：

```tsx
import type { ReactNode } from "react"

export function Section({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-4 border-b border-border pb-10">
      <header className="space-y-1">
        <h2 className="text-xl font-semibold">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </header>
      <div className="flex flex-wrap items-start gap-6">{children}</div>
    </section>
  )
}
```

- [ ] **Step 16.3: Page skeleton with guard**

Create `apps/web/app/__dev/components/page.tsx`：

```tsx
import { notFound } from "next/navigation"

import { DevThemeToggle } from "./dev-theme-toggle"

export const dynamic = "force-dynamic"

export default function ComponentsShowcasePage() {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_ENABLE_DEV_ROUTES !== "1"
  ) {
    notFound()
  }
  return (
    <main className="mx-auto w-full max-w-5xl space-y-12 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">UI 元件展示</h1>
          <p className="text-sm text-muted-foreground">
            開發模式專屬頁面；生產環境預設 404。
          </p>
        </div>
        <DevThemeToggle />
      </header>
      <p className="text-sm text-muted-foreground">
        後續 Task 會依元件分類填入 Section。
      </p>
    </main>
  )
}
```

- [ ] **Step 16.4: 驗證**

```bash
pnpm -F @ims/web build
```

- [ ] **Step 16.5: Commit**

```bash
git add apps/web/app/__dev
git commit -m "feat(web): scaffold /__dev/components showcase with guard (#1)"
```

---

## Task 17: Showcase — Form 元件 section

**Files:**
- Create: `apps/web/app/__dev/components/sections/forms.tsx`
- Modify: `apps/web/app/__dev/components/page.tsx`（引入 Section）

- [ ] **Step 17.1: Section 內容**

Create `apps/web/app/__dev/components/sections/forms.tsx`：

```tsx
"use client"

import { useState } from "react"

import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"

import { Section } from "../section"

export function FormsSection() {
  const [slider, setSlider] = useState([50])
  return (
    <Section title="Forms" description="輸入類元件。所有元件皆以鍵盤與讀屏友善為目標。">
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-input">Input</Label>
        <Input id="demo-input" placeholder="物品名稱" />
      </div>
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-textarea">Textarea</Label>
        <Textarea id="demo-textarea" placeholder="備註" />
      </div>
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-select">Select</Label>
        <Select>
          <SelectTrigger id="demo-select">
            <SelectValue placeholder="選擇位置" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="bedroom">臥室</SelectItem>
            <SelectItem value="kitchen">廚房</SelectItem>
            <SelectItem value="office">書房</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-3">
        <Checkbox id="demo-check" />
        <Label htmlFor="demo-check">已整理</Label>
      </div>
      <RadioGroup defaultValue="a" className="flex gap-4">
        <div className="flex items-center gap-2">
          <RadioGroupItem value="a" id="r1" />
          <Label htmlFor="r1">選項 A</Label>
        </div>
        <div className="flex items-center gap-2">
          <RadioGroupItem value="b" id="r2" />
          <Label htmlFor="r2">選項 B</Label>
        </div>
      </RadioGroup>
      <div className="flex items-center gap-3">
        <Switch id="demo-switch" />
        <Label htmlFor="demo-switch">開啟通知</Label>
      </div>
      <div className="w-64 space-y-2">
        <Label>Slider — {slider[0]}</Label>
        <Slider value={slider} onValueChange={setSlider} max={100} />
      </div>
    </Section>
  )
}
```

- [ ] **Step 17.2: 引入 page**

Modify `apps/web/app/__dev/components/page.tsx` 的 return，把佔位 `<p>` 換成：

```tsx
<FormsSection />
```

並 import `import { FormsSection } from "./sections/forms"`。

- [ ] **Step 17.3: 驗證**

```bash
pnpm -F @ims/web build
```

- [ ] **Step 17.4: Commit**

```bash
git add apps/web/app/__dev
git commit -m "feat(web): showcase forms section (#1)"
```

---

## Task 18: Showcase — Overlays + Feedback

**Files:**
- Create: `apps/web/app/__dev/components/sections/overlays.tsx`
- Create: `apps/web/app/__dev/components/sections/feedback.tsx`
- Modify: `apps/web/app/__dev/components/page.tsx`

- [ ] **Step 18.1: Overlays section**

Create `apps/web/app/__dev/components/sections/overlays.tsx`：

```tsx
"use client"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { Section } from "../section"

export function OverlaysSection() {
  return (
    <Section title="Overlays" description="Modal 類元件。全部支援 Esc 關閉與 focus trap。">
      <Dialog>
        <DialogTrigger asChild>
          <Button>開啟 Dialog</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增物品</DialogTitle>
            <DialogDescription>示範 Dialog 基礎樣式。</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>

      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline">開啟 Sheet</Button>
        </SheetTrigger>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Sheet 標題</SheetTitle>
            <SheetDescription>從右側滑出的抽屜。</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>

      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline">Popover</Button>
        </PopoverTrigger>
        <PopoverContent>
          <p className="text-sm">位置：書房書桌</p>
        </PopoverContent>
      </Popover>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">Dropdown</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>操作</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>編輯</DropdownMenuItem>
          <DropdownMenuItem>刪除</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost">Hover me</Button>
          </TooltipTrigger>
          <TooltipContent>提示文字</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="destructive">刪除</Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>確認刪除？</AlertDialogTitle>
            <AlertDialogDescription>此操作無法復原。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction>確認</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Section>
  )
}
```

- [ ] **Step 18.2: Feedback section**

Create `apps/web/app/__dev/components/sections/feedback.tsx`：

```tsx
"use client"

import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"

import { Section } from "../section"

export function FeedbackSection() {
  return (
    <Section title="Feedback" description="狀態與訊息類元件。">
      <Alert className="max-w-md">
        <AlertTitle>資訊</AlertTitle>
        <AlertDescription>這是一個 Alert 的示範內容。</AlertDescription>
      </Alert>

      <div className="flex flex-wrap gap-2">
        <Badge>預設</Badge>
        <Badge variant="secondary">次要</Badge>
        <Badge variant="destructive">錯誤</Badge>
        <Badge variant="outline">外框</Badge>
      </div>

      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-40" />
      </div>

      <div className="w-64 space-y-2">
        <Progress value={62} />
        <p className="text-xs text-muted-foreground">62% 完成</p>
      </div>

      <Button
        onClick={() =>
          toast.success("已儲存", { description: "偏好設定已同步。" })
        }
      >
        觸發 Toast
      </Button>
    </Section>
  )
}
```

- [ ] **Step 18.3: 接入 page**

Modify `apps/web/app/__dev/components/page.tsx`：

```tsx
import { FeedbackSection } from "./sections/feedback"
import { FormsSection } from "./sections/forms"
import { OverlaysSection } from "./sections/overlays"

// 在 return 內容中依序渲染：
<FormsSection />
<OverlaysSection />
<FeedbackSection />
```

- [ ] **Step 18.4: 驗證**

```bash
pnpm -F @ims/web build
```

- [ ] **Step 18.5: Commit**

```bash
git add apps/web/app/__dev
git commit -m "feat(web): showcase overlays + feedback sections (#1)"
```

---

## Task 19: Showcase — Navigation + Data display

**Files:**
- Create: `apps/web/app/__dev/components/sections/navigation.tsx`
- Create: `apps/web/app/__dev/components/sections/data.tsx`
- Modify: `apps/web/app/__dev/components/page.tsx`

- [ ] **Step 19.1: Navigation section**

Create `apps/web/app/__dev/components/sections/navigation.tsx`：

```tsx
"use client"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { Section } from "../section"

export function NavigationSection() {
  return (
    <Section title="Navigation" description="導航類元件。">
      <Tabs defaultValue="a" className="w-full max-w-md">
        <TabsList>
          <TabsTrigger value="a">概覽</TabsTrigger>
          <TabsTrigger value="b">詳情</TabsTrigger>
          <TabsTrigger value="c">紀錄</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Tab A 內容</TabsContent>
        <TabsContent value="b">Tab B 內容</TabsContent>
        <TabsContent value="c">Tab C 內容</TabsContent>
      </Tabs>

      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="#">首頁</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink href="#">物品</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>詳情</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <Pagination>
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious href="#" />
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#" isActive>
              1
            </PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#">2</PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationEllipsis />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext href="#" />
          </PaginationItem>
        </PaginationContent>
      </Pagination>

      <div className="w-full max-w-sm rounded-md border">
        <Command>
          <CommandInput placeholder="搜尋…" />
          <CommandList>
            <CommandEmpty>無結果。</CommandEmpty>
            <CommandGroup heading="建議">
              <CommandItem>新增物品</CommandItem>
              <CommandItem>查詢歷史</CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </div>
    </Section>
  )
}
```

- [ ] **Step 19.2: Data display section**

Create `apps/web/app/__dev/components/sections/data.tsx`：

```tsx
"use client"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { Section } from "../section"

export function DataSection() {
  return (
    <Section title="Data Display" description="資料呈現類元件。">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Card 標題</CardTitle>
          <CardDescription>一個完整 Card 結構。</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm">這裡放內容。</p>
        </CardContent>
      </Card>

      <Table className="max-w-md">
        <TableHeader>
          <TableRow>
            <TableHead>名稱</TableHead>
            <TableHead>位置</TableHead>
            <TableHead className="text-right">數量</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>相機</TableCell>
            <TableCell>書房</TableCell>
            <TableCell className="text-right">1</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>筆記本</TableCell>
            <TableCell>抽屜</TableCell>
            <TableCell className="text-right">3</TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarImage src="" alt="" />
          <AvatarFallback>IM</AvatarFallback>
        </Avatar>
        <div>
          <div className="text-sm font-medium">User</div>
          <div className="text-xs text-muted-foreground">email@example.com</div>
        </div>
      </div>

      <div className="w-48">
        <div className="text-sm">左</div>
        <Separator className="my-2" />
        <div className="text-sm">右</div>
      </div>

      <Accordion type="single" collapsible className="w-full max-w-md">
        <AccordionItem value="a">
          <AccordionTrigger>什麼是 shadcn/ui？</AccordionTrigger>
          <AccordionContent>
            一組可複製貼上的 React 元件，構建於 Radix primitives 之上。
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="b">
          <AccordionTrigger>為什麼要深色模式？</AccordionTrigger>
          <AccordionContent>
            降低視覺疲勞、配合 OLED 省電、尊重使用者偏好。
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <ScrollArea className="h-32 w-48 rounded-md border p-3 text-sm">
        {Array.from({ length: 20 }).map((_, i) => (
          <div key={i}>項目 {i + 1}</div>
        ))}
      </ScrollArea>
    </Section>
  )
}
```

- [ ] **Step 19.3: 接入 page**

Modify `apps/web/app/__dev/components/page.tsx`：

```tsx
import { DataSection } from "./sections/data"
import { NavigationSection } from "./sections/navigation"

// 加到既有的 sections 之後：
<NavigationSection />
<DataSection />
```

- [ ] **Step 19.4: 驗證**

```bash
pnpm -F @ims/web build
```

- [ ] **Step 19.5: Commit**

```bash
git add apps/web/app/__dev
git commit -m "feat(web): showcase navigation + data sections (#1)"
```

---

## Task 20: Playwright theme E2E

**Files:**
- Create: `apps/web/tests/theme.spec.ts`

- [ ] **Step 20.1: 測試**

Create `apps/web/tests/theme.spec.ts`：

```typescript
import { expect, test } from "@playwright/test"

test.describe("Theme persistence", () => {
  test("anon user switching via __dev page persists across reload", async ({
    page,
  }) => {
    await page.goto("/__dev/components")
    await expect(page.getByRole("heading", { name: "UI 元件展示" })).toBeVisible()

    // 初始 class 應為 light（system 預設在測試環境常為 light）或 dark；切換一次再驗證
    const before = await page.locator("html").getAttribute("class")
    await page.getByRole("button", { name: /切換/ }).click()
    const after = await page.locator("html").getAttribute("class")
    expect(after).not.toBe(before)

    const expectedDark = after?.includes("dark") ?? false
    await page.reload()
    const reloaded = await page.locator("html").getAttribute("class")
    expect(reloaded?.includes("dark") ?? false).toBe(expectedDark)
  })

  test("authenticated user: theme loads from preferences API", async ({
    page,
    request,
  }) => {
    const suffix = Date.now().toString()
    const username = `theme_${suffix}`
    const email = `theme_${suffix}@example.com`
    const password = "secret1234"

    const reg = await request.post("/api/auth/register", {
      data: { email, username, password },
    })
    expect(reg.status()).toBe(201)

    const login = await request.post("/api/auth/login", {
      data: { username, password },
    })
    const { access_token } = await login.json()

    await request.put("/api/users/me/preferences", {
      headers: { Authorization: `Bearer ${access_token}` },
      data: { theme: "dark" },
    })

    // UI 登入並訪問 /__dev/components
    await page.goto("/login")
    await page.getByLabel("使用者名稱").fill(username)
    await page.getByLabel("密碼").fill(password)
    await page.getByRole("button", { name: /登入/ }).click()
    await page.waitForURL("/")
    await page.goto("/__dev/components")
    // 等 ThemeSync 生效
    await page.waitForFunction(() =>
      document.documentElement.classList.contains("dark"),
    )
    await expect(page.locator("html")).toHaveClass(/dark/)
  })
})
```

- [ ] **Step 20.2: 列出**

```bash
cd apps/web
pnpm exec playwright test --list
cd ../..
```

預期：看到 3 個測試（#0 的 login 2 個 + theme 2 個…不，是 2 個 theme + 2 個 login = 4 個）。

- [ ] **Step 20.3: Commit（實際執行在 CI）**

```bash
git add apps/web/tests/theme.spec.ts
git commit -m "test(web): add Playwright E2E for theme persistence (#1)"
```

---

## Task 21: CI 調整 — 增加新測試路徑

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 21.1: 確認 CI web job 會跑新增的 Playwright**

Read `.github/workflows/ci.yml`。目前 web job 有 `pnpm --filter @ims/web test`；Playwright 走 `pnpm test:e2e`，並未排在 web job 中（#0 將 e2e 視為本地/compose 驗證）。此次仍延續：CI 不強制跑 Playwright。

確認一下既有 CI 能抓到：
- `pnpm --filter @ims/web typecheck`
- `pnpm --filter @ims/web build`（含 /__dev/components 守衛）
- `pnpm --filter @ims/api test`（含 34 個測試）

若 `pnpm --filter @ims/web test` 此時指向 Vitest 而 Vitest 還沒設定，需先檢查 Task 8 是否有 Vitest 設定檔。若 `package.json` 的 `test` script 是 `echo 'no tests'` 則略過；若是 `vitest` 但沒有測試檔，會 0 exit（vitest 沒檔也會綠）。

讀 `apps/web/package.json` 的 `test` script 以確認。若需要，加入一個空 `apps/web/tests-unit/.gitkeep` 或把 `test` 指向 `--passWithNoTests`：

```bash
# package.json:
"test": "vitest run --passWithNoTests"
```

- [ ] **Step 21.2: 修正 web test script（若需要）**

```bash
pnpm -F @ims/web run test
```

若失敗，改 script 為 `vitest run --passWithNoTests` 或 `echo '(vitest not configured yet)'`（保守），commit。

- [ ] **Step 21.3: 若修改 Commit**

```bash
git add apps/web/package.json
git commit -m "ci(web): ensure test script tolerates no unit tests yet (#1)"
```

（若無需改動，跳過此 commit。）

---

## Task 22: 最終回歸與 roadmap 更新

**Files:**
- Modify: `docs/v2-roadmap.md`（標記 #1 為完成）

- [ ] **Step 22.1: 全部驗證**

```bash
pnpm -F @ims/api test
pnpm -F @ims/web typecheck
pnpm -F @ims/web build
```

預期：
- API：≥ 34 tests passed
- Web typecheck：綠
- Web build：綠，`/__dev/components` 出現在 route list

- [ ] **Step 22.2: 更新 roadmap**

Modify `docs/v2-roadmap.md`，把 #0 和 #1 的狀態列更新：

```markdown
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 完成 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ✅ 完成 |
```

- [ ] **Step 22.3: Commit**

```bash
git add docs/v2-roadmap.md
git commit -m "docs: mark #0 and #1 complete on roadmap (#1)"
```

---

## Exit Criteria（#1 完成檢查）

- [ ] `pnpm -F @ims/api test` 綠（≥ 34 tests）
- [ ] `pnpm -F @ims/web typecheck` + `build` 綠
- [ ] `packages/api-types/src/index.ts` 含 `/api/users/me/preferences` 路徑
- [ ] `apps/web/components/ui/` 下有 31 個元件檔（含 #0 Button）
- [ ] `/__dev/components` 在 dev 渲染 5 個 sections 且 light/dark 皆正常
- [ ] `/__dev/components` 在 production build 輸出 404（未設 `NEXT_PUBLIC_ENABLE_DEV_ROUTES=1` 時）
- [ ] Playwright tests 檔案存在（執行延至 CI / local compose）
- [ ] Alembic migration 0002 能 up/down（在 SQLite + Postgres 皆通）
- [ ] Roadmap 已標 #1 完成

## Non-Goals（延後）

- Header 頭像下拉的實際主題切換 UI → #2
- next-intl messages 載入 → #2
- Logo、品牌插畫 → 視需要開獨立子專案
- Storybook → 維持 `/__dev` 替代，元件數超過 80 再評估
- Chart / DataViz 元件 → #4
- Date / Time picker → #3 遇到日期欄位再裝
