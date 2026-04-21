# IMS v2 Foundation (#0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 v2 重構的 monorepo 基礎骨架：Next.js 15 前端、FastAPI 後端、PostgreSQL、Redis、Nginx，並以 JWT auth 打通 login → refresh → 受保護端點的整段資料流，為後續 #1–#9 子專案提供可以直接擴充的起點。

**Architecture:** pnpm workspaces monorepo，`apps/web`（Next.js App Router + Tailwind + shadcn/ui）、`apps/api`（FastAPI + async SQLAlchemy 2.0 + Alembic）、`packages/api-types`（OpenAPI → TS 型別自動生成）。Docker Compose 單機部署：Nginx 反向代理分流 web / api，Postgres + Redis 內部服務。

**Tech Stack:** Next.js 15、TypeScript 5.4+、Tailwind CSS 3.4、shadcn/ui（Radix）、TanStack Query 5、Zustand、FastAPI 0.115、Pydantic v2、SQLAlchemy 2.0（async）、python-jose、passlib[argon2]、Alembic、pytest + httpx、Vitest、Playwright、Turborepo、pnpm。

---

## File Structure

### Monorepo root
- `package.json` — pnpm workspace 根設定與跨 app 指令
- `pnpm-workspace.yaml` — 宣告 workspace 成員
- `turbo.json` — Turborepo pipeline
- `.gitignore`、`.editorconfig`、`.prettierrc`
- `docker-compose.yml`、`docker-compose.dev.yml`
- `.env.example`
- `nginx/default.conf`
- `.github/workflows/ci.yml`
- `README.md`（更新）

### `apps/api/`（FastAPI）
- `pyproject.toml` — FastAPI 專案宣告（uv 相容）
- `alembic.ini`、`alembic/env.py`、`alembic/versions/0001_initial_users.py`
- `Dockerfile`、`.dockerignore`
- `scripts/export_openapi.py`
- `app/`
  - `main.py` — FastAPI 入口、掛載路由、CORS、lifespan
  - `config.py` — Pydantic Settings 載入環境變數
  - `db/session.py` — async engine + session factory
  - `db/base.py` — Declarative base
  - `models/user.py`
  - `schemas/auth.py`、`schemas/user.py`
  - `auth/password.py`、`auth/jwt.py`、`auth/dependencies.py`
  - `repositories/user_repo.py`
  - `services/auth_service.py`
  - `routes/health.py`、`routes/auth.py`
- `tests/conftest.py`、`tests/test_health.py`、`tests/test_auth.py`

### `apps/web/`（Next.js）
- `package.json`、`tsconfig.json`、`next.config.mjs`
- `tailwind.config.ts`、`postcss.config.mjs`、`components.json`（shadcn）
- `Dockerfile`、`.dockerignore`
- `app/`
  - `layout.tsx`、`page.tsx`、`globals.css`
  - `login/page.tsx`
  - `providers.tsx`
- `components/ui/button.tsx`（shadcn 產生）
- `lib/utils.ts`、`lib/api/client.ts`、`lib/auth/auth-store.ts`、`lib/auth/use-auth.ts`
- `features/auth/login-form.tsx`
- `tests/login.spec.ts`（Playwright）
- `playwright.config.ts`、`vitest.config.ts`

### `packages/api-types/`
- `package.json`
- `generate.mjs` — 從 `apps/api` 抓 OpenAPI 產生 TS
- `src/index.ts`（生成物，gitignore）
- `.gitignore`

---

## Task Graph

```
Task 1 (monorepo root)
  ├─ Task 2 (FastAPI skeleton + health)
  │   └─ Task 3 (DB + Alembic)
  │       └─ Task 4 (User model + migration)
  │           └─ Task 5 (Auth utilities: password + JWT)
  │               └─ Task 6 (Auth routes: register + login + refresh + me)
  │                   └─ Task 7 (FastAPI Dockerfile + OpenAPI export)
  ├─ Task 8 (Next.js skeleton + Tailwind + shadcn Button)
  │   └─ Task 9 (packages/api-types codegen)
  │       └─ Task 10 (Next.js API client + auth store)
  │           └─ Task 11 (Next.js login page)
  │               └─ Task 12 (Next.js Dockerfile)
  ├─ Task 13 (Nginx + docker-compose)
  │   └─ Task 14 (Playwright E2E login)
  └─ Task 15 (CI workflow)
      └─ Task 16 (README v2 quickstart)
```

---

## Task 1: Monorepo Root Setup

**Files:**
- Create: `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `.editorconfig`, `.prettierrc`, `.gitignore`（更新）

- [ ] **Step 1.1: 建立 pnpm workspace 宣告**

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 1.2: 建立根 `package.json`**

Create `package.json`:

```json
{
  "name": "item-manage-system",
  "version": "2.0.0-alpha.0",
  "private": true,
  "packageManager": "pnpm@9.12.0",
  "engines": {
    "node": ">=22.0.0",
    "pnpm": ">=9.0.0"
  },
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "typecheck": "turbo run typecheck",
    "gen:types": "turbo run gen:types",
    "format": "prettier --write ."
  },
  "devDependencies": {
    "prettier": "3.3.3",
    "prettier-plugin-tailwindcss": "0.6.8",
    "turbo": "2.1.3",
    "typescript": "5.6.2"
  }
}
```

- [ ] **Step 1.3: 建立 `turbo.json`**

Create `turbo.json`:

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {},
    "test": {},
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "gen:types": {
      "outputs": ["src/**"]
    }
  }
}
```

- [ ] **Step 1.4: 建立 `.editorconfig`、`.prettierrc`**

Create `.editorconfig`:

```ini
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
```

Create `.prettierrc`:

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

- [ ] **Step 1.5: 更新 `.gitignore`**

Append to `.gitignore` (若已有 `.gitignore` 請只附加下列區塊)：

```gitignore
# v2 monorepo
node_modules/
.next/
.turbo/
dist/
.pnpm-store/
packages/api-types/src/

# Python v2
apps/api/.venv/
apps/api/__pycache__/
apps/api/**/__pycache__/
apps/api/.pytest_cache/

# Env
.env
.env.local
.env.*.local
```

- [ ] **Step 1.6: 安裝根依賴並初始化 pnpm**

Run:

```bash
corepack enable
pnpm install
```

Expected: 建立 `pnpm-lock.yaml`、安裝 prettier、turbo、typescript。

- [ ] **Step 1.7: 提交**

```bash
git add package.json pnpm-workspace.yaml turbo.json pnpm-lock.yaml .editorconfig .prettierrc .gitignore
git commit -m "feat(repo): initialize pnpm workspaces + turborepo monorepo (#0)"
```

---

## Task 2: FastAPI Skeleton + Health Endpoint (TDD)

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/app/__init__.py`, `apps/api/app/main.py`, `apps/api/app/config.py`, `apps/api/app/routes/__init__.py`, `apps/api/app/routes/health.py`, `apps/api/tests/__init__.py`, `apps/api/tests/conftest.py`, `apps/api/tests/test_health.py`, `apps/api/package.json`

- [ ] **Step 2.1: 建立 `apps/api/pyproject.toml`**

Create `apps/api/pyproject.toml`:

```toml
[project]
name = "ims-api"
version = "2.0.0a0"
description = "Item Management System v2 API"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]==0.115.0",
    "uvicorn[standard]==0.30.6",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "sqlalchemy[asyncio]==2.0.35",
    "asyncpg==0.29.0",
    "alembic==1.13.3",
    "python-jose[cryptography]==3.3.0",
    "passlib[argon2]==1.7.4",
    "python-multipart==0.0.12",
    "httpx==0.27.2",
    "slowapi==0.1.9",
    "redis==5.1.0",
    "structlog==24.4.0",
    "apscheduler==3.10.4",
    "fastapi-mail==1.4.1"
]

[project.optional-dependencies]
test = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "pytest-cov==5.0.0",
    "aiosqlite==0.20.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2.2: 建立空 package init**

Create `apps/api/app/__init__.py`（空檔案）、`apps/api/app/routes/__init__.py`（空檔案）、`apps/api/tests/__init__.py`（空檔案）。

- [ ] **Step 2.3: 建立 `apps/api/app/config.py`**

Create `apps/api/app/config.py`:

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    app_name: str = "IMS v2 API"
    environment: str = Field(default="dev")
    database_url: str = Field(default="postgresql+asyncpg://ims:ims@localhost:5432/ims")
    redis_url: str = Field(default="redis://localhost:6379/0")
    jwt_secret: str = Field(default="change-me-in-production-please")
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 60 * 15
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 7
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2.4: 撰寫 health 端點失敗測試**

Create `apps/api/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

Create `apps/api/tests/test_health.py`:

```python
async def test_health_endpoint_returns_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ims-api"
```

- [ ] **Step 2.5: 執行測試確認失敗**

Run:

```bash
cd apps/api
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[test]"
pytest tests/test_health.py -v
```

Expected: FAIL（`app.main` 不存在）。

- [ ] **Step 2.6: 撰寫最小實作**

Create `apps/api/app/routes/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ims-api"}
```

Create `apps/api/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0a0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 2.7: 執行測試確認通過**

Run:

```bash
pytest tests/test_health.py -v
```

Expected: 1 passed.

- [ ] **Step 2.8: 建立 `apps/api/package.json`（讓 Turborepo 可識別此 workspace 的指令）**

Create `apps/api/package.json`:

```json
{
  "name": "@ims/api",
  "version": "2.0.0-alpha.0",
  "private": true,
  "scripts": {
    "dev": "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
    "test": "pytest",
    "lint": "ruff check app tests",
    "typecheck": "python -c 'import app.main'",
    "gen:types": "python scripts/export_openapi.py > ../../packages/api-types/openapi.json"
  }
}
```

- [ ] **Step 2.9: 提交**

```bash
cd ../..
git add apps/api
git commit -m "feat(api): add FastAPI skeleton with /api/health (#0)"
```

---

## Task 3: Database Layer + Alembic

**Files:**
- Create: `apps/api/app/db/__init__.py`, `apps/api/app/db/session.py`, `apps/api/app/db/base.py`, `apps/api/alembic.ini`, `apps/api/alembic/env.py`, `apps/api/alembic/script.py.mako`, `apps/api/alembic/versions/.gitkeep`

- [ ] **Step 3.1: 建立 DB base 與 session**

Create `apps/api/app/db/__init__.py`（空檔案）。

Create `apps/api/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `apps/api/app/db/session.py`:

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3.2: 建立 Alembic 設定**

Create `apps/api/alembic.ini`:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://ims:ims@localhost:5432/ims

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3.3: 建立 `alembic/env.py`**

Create `apps/api/alembic/env.py`:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.config import get_settings
from app.db.base import Base
# Import all models so Alembic can autogenerate
from app.models import user  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3.4: 建立 alembic script template**

Create `apps/api/alembic/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create empty `apps/api/alembic/versions/.gitkeep`.

- [ ] **Step 3.5: 提交**

```bash
git add apps/api/app/db apps/api/alembic.ini apps/api/alembic
git commit -m "feat(api): wire async SQLAlchemy + Alembic scaffolding (#0)"
```

---

## Task 4: User Model + Initial Migration

**Files:**
- Create: `apps/api/app/models/__init__.py`, `apps/api/app/models/user.py`, `apps/api/alembic/versions/0001_initial_users.py`

- [ ] **Step 4.1: 建立 User 模型**

Create `apps/api/app/models/__init__.py`:

```python
from app.models.user import User

__all__ = ["User"]
```

Create `apps/api/app/models/user.py`:

```python
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
```

- [ ] **Step 4.2: 建立初始 migration**

Create `apps/api/alembic/versions/0001_initial_users.py`:

```python
"""initial users table

Revision ID: 0001
Revises:
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 4.3: 驗證 migration 語法**

Run（需先有 postgres 實例，或暫時改 `sqlalchemy.url` 指向本地，或 skip 此步，於 Task 13 docker compose 時再跑）:

```bash
cd apps/api
alembic upgrade head --sql
```

Expected: 印出 SQL，無錯誤。

- [ ] **Step 4.4: 提交**

```bash
cd ../..
git add apps/api/app/models apps/api/alembic/versions/0001_initial_users.py
git commit -m "feat(api): add User model with initial migration (#0)"
```

---

## Task 5: Auth Utilities — Password + JWT (TDD)

**Files:**
- Create: `apps/api/app/auth/__init__.py`, `apps/api/app/auth/password.py`, `apps/api/app/auth/jwt.py`, `apps/api/tests/test_auth_utils.py`

- [ ] **Step 5.1: 撰寫 password hash 失敗測試**

Create `apps/api/tests/test_auth_utils.py`:

```python
import pytest
from datetime import timedelta

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_token, decode_token, TokenError


def test_hash_password_is_not_plaintext():
    hashed = hash_password("secret1234")
    assert hashed != "secret1234"
    assert hashed.startswith("$argon2")


def test_verify_password_accepts_correct():
    hashed = hash_password("secret1234")
    assert verify_password("secret1234", hashed) is True


def test_verify_password_rejects_wrong():
    hashed = hash_password("secret1234")
    assert verify_password("wrong-pass", hashed) is False


def test_create_and_decode_token_roundtrip():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"


def test_decode_rejects_wrong_type():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="refresh")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_decode_rejects_tampered_token():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(TokenError):
        decode_token(tampered, expected_type="access")
```

- [ ] **Step 5.2: 執行測試確認失敗**

Run:

```bash
cd apps/api
pytest tests/test_auth_utils.py -v
```

Expected: FAIL（`app.auth` 模組不存在）。

- [ ] **Step 5.3: 建立 password 模組**

Create `apps/api/app/auth/__init__.py`（空檔案）。

Create `apps/api/app/auth/password.py`:

```python
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)
```

- [ ] **Step 5.4: 建立 JWT 模組**

Create `apps/api/app/auth/jwt.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from app.config import get_settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    pass


def create_token(subject: str, ttl: timedelta, token_type: TokenType) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload
```

- [ ] **Step 5.5: 執行測試確認通過**

Run:

```bash
pytest tests/test_auth_utils.py -v
```

Expected: 6 passed.

- [ ] **Step 5.6: 提交**

```bash
cd ../..
git add apps/api/app/auth apps/api/tests/test_auth_utils.py
git commit -m "feat(api): add password hashing + JWT utilities (#0)"
```

---

## Task 6: Auth Routes — Register / Login / Refresh / Me (TDD)

**Files:**
- Create: `apps/api/app/schemas/__init__.py`, `apps/api/app/schemas/auth.py`, `apps/api/app/schemas/user.py`, `apps/api/app/repositories/__init__.py`, `apps/api/app/repositories/user_repo.py`, `apps/api/app/services/__init__.py`, `apps/api/app/services/auth_service.py`, `apps/api/app/auth/dependencies.py`, `apps/api/app/routes/auth.py`, `apps/api/tests/test_auth.py`
- Modify: `apps/api/app/main.py`（掛載新路由）、`apps/api/tests/conftest.py`（加 SQLite 測試資料庫）

- [ ] **Step 6.1: 升級 conftest 注入測試資料庫**

Replace `apps/api/tests/conftest.py`:

```python
import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import user as _user_model  # noqa: F401, E402


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session


@pytest.fixture
async def client(test_engine):
    app = create_app()
    maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

因為 SQLite 不支援 PostgreSQL 的 UUID type，`User` 模型在測試環境需能 fallback。新增測試輔助：

Create `apps/api/app/models/user.py` 需微調（重新撰寫，把 UUID 型別改為相容的做法）— **修改** `apps/api/app/models/user.py`，把 `id` 型別改為：

```python
import uuid
from sqlalchemy.types import CHAR, TypeDecorator

class GUID(TypeDecorator):
    """Platform-independent GUID type (UUID on PG, CHAR(36) elsewhere)."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)
```

完整新版 `apps/api/app/models/user.py`：

```python
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator

from app.db.base import Base


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
```

- [ ] **Step 6.2: 撰寫 auth routes 失敗測試**

Create `apps/api/tests/test_auth.py`:

```python
async def test_register_creates_user_and_returns_tokens(client):
    resp = await client.post("/api/auth/register", json={
        "email": "alice@example.com",
        "username": "alice",
        "password": "secret1234",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["username"] == "alice"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "username": "dup1", "password": "secret1234"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json={**payload, "username": "dup2"})
    assert resp.status_code == 409


async def test_login_returns_access_token_and_sets_refresh_cookie(client):
    await client.post("/api/auth/register", json={
        "email": "bob@example.com", "username": "bob", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "bob", "password": "secret1234",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    cookies = resp.cookies
    assert "refresh_token" in cookies


async def test_login_wrong_password_rejected(client):
    await client.post("/api/auth/register", json={
        "email": "carol@example.com", "username": "carol", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "carol", "password": "wrong-pass",
    })
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_returns_user_when_authed(client):
    register = await client.post("/api/auth/register", json={
        "email": "dave@example.com", "username": "dave", "password": "secret1234",
    })
    access = register.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "dave"


async def test_refresh_issues_new_access_token(client):
    await client.post("/api/auth/register", json={
        "email": "eve@example.com", "username": "eve", "password": "secret1234",
    })
    login = await client.post("/api/auth/login", json={
        "username": "eve", "password": "secret1234",
    })
    refresh_cookie = login.cookies.get("refresh_token")
    resp = await client.post("/api/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
```

- [ ] **Step 6.3: 執行測試確認失敗**

Run:

```bash
pytest tests/test_auth.py -v
```

Expected: FAIL（schemas / routes / repos / service 皆未建立）。

- [ ] **Step 6.4: 建立 Pydantic schemas**

Create `apps/api/app/schemas/__init__.py`（空檔案）。

Create `apps/api/app/schemas/user.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
```

Create `apps/api/app/schemas/auth.py`:

```python
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserPublic


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 6.5: 建立 user repository**

Create `apps/api/app/repositories/__init__.py`（空檔案）。

Create `apps/api/app/repositories/user_repo.py`:

```python
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, *, email: str, username: str, password_hash: str) -> User:
        user = User(email=email, username=username, password_hash=password_hash)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
```

- [ ] **Step 6.6: 建立 auth service**

Create `apps/api/app/services/__init__.py`（空檔案）。

Create `apps/api/app/services/auth_service.py`:

```python
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_token
from app.auth.password import hash_password, verify_password
from app.config import get_settings
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthError(Exception):
    pass


class EmailAlreadyExists(AuthError):
    pass


class UsernameAlreadyExists(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.settings = get_settings()

    async def register(self, *, email: str, username: str, password: str) -> User:
        if await self.repo.get_by_email(email):
            raise EmailAlreadyExists(email)
        if await self.repo.get_by_username(username):
            raise UsernameAlreadyExists(username)
        return await self.repo.create(
            email=email, username=username, password_hash=hash_password(password)
        )

    async def authenticate(self, *, username: str, password: str) -> User:
        user = await self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        if not user.is_active:
            raise InvalidCredentials()
        return user

    def issue_access_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.access_token_ttl_seconds),
            token_type="access",
        )

    def issue_refresh_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.refresh_token_ttl_seconds),
            token_type="refresh",
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.repo.get_by_id(user_id)
```

- [ ] **Step 6.7: 建立 auth dependencies**

Create `apps/api/app/auth/dependencies.py`:

```python
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import TokenError, decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    service = AuthService(session)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user
```

- [ ] **Step 6.8: 建立 auth routes**

Create `apps/api/app/routes/auth.py`:

```python
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import TokenError, decode_token
from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExists,
    InvalidCredentials,
    UsernameAlreadyExists,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.environment != "dev",
        samesite="lax",
        path="/api/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(session)
    try:
        user = await service.register(
            email=payload.email, username=payload.username, password=payload.password
        )
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="email already registered")
    except UsernameAlreadyExists:
        raise HTTPException(status_code=409, detail="username already taken")
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(session)
    try:
        user = await service.authenticate(username=payload.username, password=payload.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="invalid credentials")
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="missing refresh cookie")
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    from uuid import UUID

    service = AuthService(session)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found")
    access = service.issue_access_token(user)
    new_refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, new_refresh)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    response.delete_cookie("refresh_token", path="/api/auth")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
```

- [ ] **Step 6.9: 更新 `app/main.py` 掛載 auth router**

Edit `apps/api/app/main.py`：在 `from app.routes import health` 之下加一行 `from app.routes import auth`，並在 `app.include_router(health.router)` 之後加 `app.include_router(auth.router)`。

完整檔案：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import auth, health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0a0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
```

- [ ] **Step 6.10: 執行測試確認全部通過**

Run:

```bash
pytest -v
```

Expected: 所有 auth + health + utils 測試通過。

- [ ] **Step 6.11: 提交**

```bash
cd ../..
git add apps/api
git commit -m "feat(api): implement register/login/refresh/logout/me auth endpoints (#0)"
```

---

## Task 7: FastAPI Dockerfile + OpenAPI Export Script

**Files:**
- Create: `apps/api/Dockerfile`, `apps/api/.dockerignore`, `apps/api/scripts/__init__.py`, `apps/api/scripts/export_openapi.py`

- [ ] **Step 7.1: 建立 OpenAPI 匯出腳本**

Create `apps/api/scripts/__init__.py`（空檔案）。

Create `apps/api/scripts/export_openapi.py`:

```python
"""Export OpenAPI JSON to stdout for the api-types package."""
import json
import sys

from app.main import create_app


def main() -> int:
    app = create_app()
    sys.stdout.write(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7.2: 驗證匯出**

Run:

```bash
cd apps/api
python scripts/export_openapi.py | head -20
```

Expected: 顯示 OpenAPI JSON 開頭（`{"openapi": "3.1.0", ...}`）。

- [ ] **Step 7.3: 建立 Dockerfile**

Create `apps/api/Dockerfile`:

```dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY scripts ./scripts

RUN pip install --upgrade pip \
 && pip install uv \
 && uv venv /app/.venv \
 && uv pip install --python /app/.venv/bin/python -e .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7.4: 建立 `.dockerignore`**

Create `apps/api/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
tests/
.env
.env.*
```

- [ ] **Step 7.5: 驗證 Docker 建置**

Run:

```bash
cd ../..
docker build -t ims-api:dev -f apps/api/Dockerfile apps/api
```

Expected: 成功建置 image。

- [ ] **Step 7.6: 提交**

```bash
git add apps/api/Dockerfile apps/api/.dockerignore apps/api/scripts
git commit -m "build(api): add Dockerfile + OpenAPI export script (#0)"
```

---

## Task 8: Next.js Skeleton + Tailwind + shadcn Button

**Files:**
- Create: `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/next.config.mjs`, `apps/web/tailwind.config.ts`, `apps/web/postcss.config.mjs`, `apps/web/components.json`, `apps/web/next-env.d.ts`, `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/app/globals.css`, `apps/web/app/providers.tsx`, `apps/web/components/ui/button.tsx`, `apps/web/lib/utils.ts`

- [ ] **Step 8.1: 建立 `apps/web/package.json`**

Create `apps/web/package.json`:

```json
{
  "name": "@ims/web",
  "version": "2.0.0-alpha.0",
  "private": true,
  "scripts": {
    "dev": "next dev --turbo -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "gen:types": "echo 'api-types generated in packages/api-types'"
  },
  "dependencies": {
    "@ims/api-types": "workspace:*",
    "@radix-ui/react-slot": "1.1.0",
    "@tanstack/react-query": "5.59.0",
    "class-variance-authority": "0.7.0",
    "clsx": "2.1.1",
    "lucide-react": "0.447.0",
    "next": "15.0.0",
    "next-intl": "3.21.1",
    "react": "19.0.0-rc-65a56d0e-20241020",
    "react-dom": "19.0.0-rc-65a56d0e-20241020",
    "react-hook-form": "7.53.0",
    "tailwind-merge": "2.5.3",
    "tailwindcss-animate": "1.0.7",
    "zod": "3.23.8",
    "zustand": "5.0.0-rc.2"
  },
  "devDependencies": {
    "@playwright/test": "1.48.0",
    "@types/node": "22.7.4",
    "@types/react": "18.3.11",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "4.3.2",
    "autoprefixer": "10.4.20",
    "eslint": "9.12.0",
    "eslint-config-next": "15.0.0",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.13",
    "typescript": "5.6.2",
    "vitest": "2.1.2"
  }
}
```

- [ ] **Step 8.2: 建立 `tsconfig.json`**

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "noUncheckedIndexedAccess": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "tests"]
}
```

- [ ] **Step 8.3: 建立 Next config + 樣式**

Create `apps/web/next.config.mjs`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
}

export default nextConfig
```

Create `apps/web/postcss.config.mjs`:

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
```

Create `apps/web/tailwind.config.ts`:

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './features/**/*.{ts,tsx}'],
  theme: {
    container: { center: true, padding: '2rem', screens: { '2xl': '1400px' } },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
```

Create `apps/web/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 240 10% 3.9%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --secondary: 240 4.8% 95.9%;
    --secondary-foreground: 240 5.9% 10%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --accent: 240 4.8% 95.9%;
    --accent-foreground: 240 5.9% 10%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --ring: 240 5.9% 10%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 240 10% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 240 3.7% 15.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }

  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 8.4: 建立 shadcn utils + Button 元件**

Create `apps/web/components.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

Create `apps/web/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

Create `apps/web/components/ui/button.tsx`:

```tsx
import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
  },
)
Button.displayName = 'Button'

export { buttonVariants }
```

- [ ] **Step 8.5: 建立首頁 layout + page**

Create `apps/web/app/providers.tsx`:

```tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
  }))
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
```

Create `apps/web/app/layout.tsx`:

```tsx
import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: '物品管理系統 v2',
  description: 'Item Management System v2',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

Create `apps/web/app/page.tsx`:

```tsx
import Link from 'next/link'

import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <h1 className="text-4xl font-bold tracking-tight">物品管理系統 v2</h1>
      <p className="text-muted-foreground">骨架已就緒。下一步：#1 設計系統。</p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/login">登入</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/docs" target="_blank" rel="noreferrer">API 文件</a>
        </Button>
      </div>
    </main>
  )
}
```

Create `apps/web/next-env.d.ts`:

```typescript
/// <reference types="next" />
/// <reference types="next/image-types/global" />
```

- [ ] **Step 8.6: 安裝依賴並啟動**

Run:

```bash
cd apps/web
pnpm install
pnpm dev
```

Expected: Next.js dev server 啟動於 `http://localhost:3000`，瀏覽器看到標題「物品管理系統 v2」與兩顆按鈕（登入、API 文件）。

停止 dev server (Ctrl+C)。

- [ ] **Step 8.7: 提交**

```bash
cd ../..
git add apps/web pnpm-lock.yaml
git commit -m "feat(web): scaffold Next.js 15 + Tailwind + shadcn Button (#0)"
```

---

## Task 9: `packages/api-types` — OpenAPI → TypeScript Codegen

**Files:**
- Create: `packages/api-types/package.json`, `packages/api-types/generate.mjs`, `packages/api-types/.gitignore`, `packages/api-types/README.md`

- [ ] **Step 9.1: 建立 package 設定**

Create `packages/api-types/package.json`:

```json
{
  "name": "@ims/api-types",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "gen:types": "node generate.mjs"
  },
  "devDependencies": {
    "openapi-typescript": "7.4.1"
  }
}
```

Create `packages/api-types/.gitignore`:

```
src/
openapi.json
```

Create `packages/api-types/README.md`:

```markdown
# @ims/api-types

Auto-generated TypeScript types from the FastAPI OpenAPI 3.1 schema.

## Regenerate

```bash
pnpm --filter @ims/api gen:types   # writes openapi.json into this package
pnpm --filter @ims/api-types gen:types  # writes src/index.ts
```

Do NOT edit `src/index.ts` by hand — it is generated.
```

- [ ] **Step 9.2: 建立生成腳本**

Create `packages/api-types/generate.mjs`:

```javascript
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'

const __dirname = dirname(fileURLToPath(import.meta.url))
const schemaPath = resolve(__dirname, 'openapi.json')
const outPath = resolve(__dirname, 'src/index.ts')

const ast = await openapiTS(new URL(`file://${schemaPath}`))
const banner = `// THIS FILE IS AUTO-GENERATED BY openapi-typescript. DO NOT EDIT.\n\n`

await mkdir(dirname(outPath), { recursive: true })
await writeFile(outPath, banner + astToString(ast), 'utf8')
console.log(`wrote ${outPath}`)
```

- [ ] **Step 9.3: 執行生成並驗證**

Run:

```bash
cd apps/api
source .venv/bin/activate
python scripts/export_openapi.py > ../../packages/api-types/openapi.json
cd ../../packages/api-types
pnpm install
pnpm gen:types
head -20 src/index.ts
```

Expected: `src/index.ts` 存在，檔案開頭為 auto-generated banner，後面有 `export interface paths` 定義。

- [ ] **Step 9.4: 提交**

```bash
cd ../..
git add packages/api-types pnpm-lock.yaml
git commit -m "feat(types): add @ims/api-types OpenAPI codegen package (#0)"
```

---

## Task 10: Next.js API Client + Auth Store

**Files:**
- Create: `apps/web/lib/api/client.ts`, `apps/web/lib/auth/auth-store.ts`, `apps/web/lib/auth/use-auth.ts`

- [ ] **Step 10.1: 建立 API client**

Create `apps/web/lib/api/client.ts`:

```typescript
import type { paths } from '@ims/api-types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`api error ${status}`)
  }
}

type RequestInitWithToken = RequestInit & { accessToken?: string | null }

export async function apiFetch(path: string, init: RequestInitWithToken = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('content-type', 'application/json')
  if (init.accessToken) {
    headers.set('authorization', `Bearer ${init.accessToken}`)
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body)
  }
  return response
}

export type Paths = paths
```

- [ ] **Step 10.2: 建立 Zustand auth store**

Create `apps/web/lib/auth/auth-store.ts`:

```typescript
import { create } from 'zustand'
import type { paths } from '@ims/api-types'

type UserPublic = paths['/api/auth/me']['get']['responses']['200']['content']['application/json']

interface AuthState {
  accessToken: string | null
  user: UserPublic | null
  setAuth: (token: string, user: UserPublic) => void
  setAccessToken: (token: string | null) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (accessToken, user) => set({ accessToken, user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null, user: null }),
}))
```

- [ ] **Step 10.3: 建立 `useAuth` hook**

Create `apps/web/lib/auth/use-auth.ts`:

```typescript
'use client'

import { useMutation } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api/client'
import { useAuthStore } from './auth-store'
import type { paths } from '@ims/api-types'

type LoginBody = paths['/api/auth/login']['post']['requestBody']['content']['application/json']
type TokenResponse = paths['/api/auth/login']['post']['responses']['200']['content']['application/json']

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: async (body: LoginBody) => {
      const res = await apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(body) })
      return (await res.json()) as TokenResponse
    },
    onSuccess: (data) => {
      setAuth(data.access_token, data.user)
    },
  })
}

export function useLogout() {
  const clear = useAuthStore((s) => s.clear)
  return useMutation({
    mutationFn: async () => {
      await apiFetch('/auth/logout', { method: 'POST' })
    },
    onSuccess: () => clear(),
  })
}

export function useCurrentUser() {
  return useAuthStore((s) => s.user)
}

export function useAccessToken() {
  return useAuthStore((s) => s.accessToken)
}
```

- [ ] **Step 10.4: 驗證 typecheck**

Run:

```bash
cd apps/web
pnpm typecheck
```

Expected: 無錯誤（若 `@ims/api-types` 尚未 symlink，Task 9 結束後應已可用）。

- [ ] **Step 10.5: 提交**

```bash
cd ../..
git add apps/web/lib
git commit -m "feat(web): add API client + Zustand auth store + auth hooks (#0)"
```

---

## Task 11: Next.js Login Page

**Files:**
- Create: `apps/web/app/login/page.tsx`, `apps/web/features/auth/login-form.tsx`

- [ ] **Step 11.1: 建立登入表單元件**

Create `apps/web/features/auth/login-form.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'
import { useLogin } from '@/lib/auth/use-auth'

export function LoginForm() {
  const router = useRouter()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ username, password })
      router.push('/')
    } catch (err) {
      if (err instanceof ApiError) {
        setError('帳號或密碼錯誤')
      } else {
        setError('登入失敗，請稍後再試')
      }
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="username" className="text-sm font-medium">
          使用者名稱
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          密碼
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? '登入中…' : '登入'}
      </Button>
    </form>
  )
}
```

- [ ] **Step 11.2: 建立 login page**

Create `apps/web/app/login/page.tsx`:

```tsx
import { LoginForm } from '@/features/auth/login-form'

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">登入</h1>
      <LoginForm />
    </main>
  )
}
```

- [ ] **Step 11.3: 驗證 typecheck + build**

Run:

```bash
cd apps/web
pnpm typecheck
pnpm build
```

Expected: 皆通過。

- [ ] **Step 11.4: 提交**

```bash
cd ../..
git add apps/web
git commit -m "feat(web): add /login page with login form (#0)"
```

---

## Task 12: Next.js Dockerfile

**Files:**
- Create: `apps/web/Dockerfile`, `apps/web/.dockerignore`

- [ ] **Step 12.1: 建立 Dockerfile（multi-stage with standalone output）**

Create `apps/web/Dockerfile`:

```dockerfile
FROM node:22-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

FROM base AS deps
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY apps/web/package.json ./apps/web/
COPY packages/api-types/package.json ./packages/api-types/
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY --from=deps /repo/packages/api-types/node_modules ./packages/api-types/node_modules
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY apps/web ./apps/web
COPY packages/api-types ./packages/api-types
# api-types src/ must be generated before build
RUN test -f packages/api-types/src/index.ts || (echo "run gen:types before docker build" && exit 1)
RUN pnpm --filter @ims/web build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
```

注意：`apps/web/public` 目錄可能尚未建立——若不存在請先 `mkdir -p apps/web/public && touch apps/web/public/.gitkeep`。

- [ ] **Step 12.2: 建立 `.dockerignore`**

Create `apps/web/.dockerignore`:

```
node_modules
.next
.turbo
tests
playwright-report
test-results
```

- [ ] **Step 12.3: 驗證 Docker 建置**

Run（需先生成 api-types）:

```bash
mkdir -p apps/web/public && touch apps/web/public/.gitkeep
# 假設 api-types 已於 Task 9 生成
docker build -t ims-web:dev -f apps/web/Dockerfile .
```

Expected: image 建置成功。

- [ ] **Step 12.4: 提交**

```bash
git add apps/web/Dockerfile apps/web/.dockerignore apps/web/public
git commit -m "build(web): add multi-stage Next.js Dockerfile with standalone output (#0)"
```

---

## Task 13: Nginx + docker-compose

**Files:**
- Create: `nginx/default.conf`, `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`

- [ ] **Step 13.1: 建立 Nginx 設定**

Create `nginx/default.conf`:

```nginx
upstream web_upstream {
    server web:3000;
}

upstream api_upstream {
    server api:8000;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 32m;

    # API
    location /api/ {
        proxy_pass http://api_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
    }

    # Next.js (everything else)
    location / {
        proxy_pass http://web_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

- [ ] **Step 13.2: 建立 `.env.example`**

Create `.env.example`:

```bash
# Database
POSTGRES_DB=ims
POSTGRES_USER=ims
POSTGRES_PASSWORD=ims_change_me
DATABASE_URL=postgresql+asyncpg://ims:ims_change_me@postgres:5432/ims

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=replace-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256

# App
ENVIRONMENT=dev
CORS_ORIGINS=["http://localhost"]

# Next.js
NEXT_PUBLIC_API_BASE=/api
```

- [ ] **Step 13.3: 建立 `docker-compose.yml`（production-like）**

Create `docker-compose.yml`:

```yaml
name: ims-v2

services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - web
      - api
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    environment:
      NODE_ENV: production
      NEXT_PUBLIC_API_BASE: /api
    expose:
      - "3000"
    depends_on:
      - api
    restart: unless-stopped

  api:
    build:
      context: apps/api
      dockerfile: Dockerfile
    env_file: .env
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    expose:
      - "8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  worker:
    build:
      context: apps/api
      dockerfile: Dockerfile
    env_file: .env
    command: ["python", "-m", "app.workers.main"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    profiles: ["worker"]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-ims}
      POSTGRES_USER: ${POSTGRES_USER:-ims}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ims_change_me}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ims}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

注意：`worker` 服務位於 `worker` profile，預設不啟動；#5 通知中心再啟用。`app.workers.main` 於本次 #0 尚未實作，因此 worker 預設關閉是合理的。

- [ ] **Step 13.4: 建立 dev override**

Create `docker-compose.dev.yml`:

```yaml
name: ims-v2

services:
  web:
    command: ["pnpm", "dev"]
    volumes:
      - ./apps/web:/app
      - /app/node_modules
    environment:
      NODE_ENV: development

  api:
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    volumes:
      - ./apps/api:/app
```

- [ ] **Step 13.5: 端對端驗證**

Run:

```bash
cp .env.example .env
# 生成一次 api-types（docker 建置需要）
pnpm --filter @ims/api gen:types
pnpm --filter @ims/api-types gen:types
docker compose build
docker compose up -d
sleep 10
curl -s http://localhost/api/health
curl -s -I http://localhost/
docker compose logs api | tail -20
```

Expected:
- `/api/health` 回傳 `{"status":"ok","service":"ims-api"}`
- `/` 回傳 HTTP 200（Next.js 首頁）
- API log 顯示 `alembic upgrade` 成功

清理：

```bash
docker compose down
```

- [ ] **Step 13.6: 提交**

```bash
git add nginx docker-compose.yml docker-compose.dev.yml .env.example
git commit -m "build: add docker-compose + nginx reverse proxy (#0)"
```

---

## Task 14: Playwright E2E — Login Flow

**Files:**
- Create: `apps/web/playwright.config.ts`, `apps/web/tests/login.spec.ts`

- [ ] **Step 14.1: 建立 Playwright 設定**

Create `apps/web/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
```

- [ ] **Step 14.2: 撰寫 E2E 測試**

Create `apps/web/tests/login.spec.ts`:

```typescript
import { expect, test } from '@playwright/test'

const unique = () => Date.now().toString()

test('register via API then login via UI lands on home', async ({ page, request }) => {
  const suffix = unique()
  const username = `e2e_${suffix}`
  const email = `e2e_${suffix}@example.com`
  const password = 'secret1234'

  const reg = await request.post('/api/auth/register', {
    data: { email, username, password },
  })
  expect(reg.status()).toBe(201)

  await page.goto('/login')
  await page.getByLabel('使用者名稱').fill(username)
  await page.getByLabel('密碼').fill(password)
  await page.getByRole('button', { name: /登入/ }).click()

  await page.waitForURL('/')
  await expect(page.getByRole('heading', { name: '物品管理系統 v2' })).toBeVisible()
})

test('wrong password shows error', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('使用者名稱').fill('does-not-exist')
  await page.getByLabel('密碼').fill('wrong-pass')
  await page.getByRole('button', { name: /登入/ }).click()

  await expect(page.getByRole('alert')).toHaveText('帳號或密碼錯誤')
})
```

- [ ] **Step 14.3: 安裝 Playwright 瀏覽器**

Run:

```bash
cd apps/web
pnpm exec playwright install --with-deps chromium
```

- [ ] **Step 14.4: 執行 E2E（要求 compose 環境存活）**

Run：

```bash
cd ../..
docker compose up -d
sleep 10
cd apps/web
E2E_BASE_URL=http://localhost pnpm test:e2e
cd ../..
docker compose down
```

Expected: 兩個測試通過。

- [ ] **Step 14.5: 提交**

```bash
git add apps/web/playwright.config.ts apps/web/tests
git commit -m "test(web): add Playwright E2E login flow (#0)"
```

---

## Task 15: CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 15.1: 建立 CI**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: ims_test
          POSTGRES_USER: ims
          POSTGRES_PASSWORD: ims
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U ims"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install uv
      - run: uv venv .venv
      - run: |
          . .venv/bin/activate
          uv pip install -e ".[test]"
      - run: |
          . .venv/bin/activate
          pytest -q
        env:
          DATABASE_URL: postgresql+asyncpg://ims:ims@localhost:5432/ims_test
          JWT_SECRET: ci-secret

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9.12.0
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "pnpm"
      - run: pnpm install --frozen-lockfile
      - name: Generate OpenAPI schema (stubbed)
        run: |
          mkdir -p packages/api-types/src
          echo "export type paths = Record<string, never>" > packages/api-types/src/index.ts
      - run: pnpm --filter @ims/web typecheck
      - run: pnpm --filter @ims/web lint
      - run: pnpm --filter @ims/web test
      - run: pnpm --filter @ims/web build

  docker:
    runs-on: ubuntu-latest
    needs: [api, web]
    steps:
      - uses: actions/checkout@v4
      - name: Build API image
        run: docker build -t ims-api:ci -f apps/api/Dockerfile apps/api
      - name: Stub api-types for web build
        run: |
          mkdir -p packages/api-types/src
          echo "export type paths = Record<string, never>" > packages/api-types/src/index.ts
      - name: Build web image
        run: docker build -t ims-web:ci -f apps/web/Dockerfile .
```

說明：CI 的 web job 為避免對 API 產生依賴，以 stub 方式放空的 `paths` 型別——這足夠通過 typecheck 與 build。真正的型別同步驗證由本地 `pnpm gen:types` 與後續每個子專案的整合測試負責。

- [ ] **Step 15.2: 提交**

```bash
git add .github
git commit -m "ci: add api/web/docker build pipelines (#0)"
```

---

## Task 16: README v2 Quickstart & Roadmap

**Files:**
- Modify: `README.md`（在最上方加入 v2 通告區塊）
- Create: `docs/v2-roadmap.md`

- [ ] **Step 16.1: 建立 v2 roadmap 文件**

Create `docs/v2-roadmap.md`:

```markdown
# v2 重構路線圖

參見 [`docs/superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md`](superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md) 了解基礎決策。

## 子專案

| # | 主題 | 狀態 |
|---|------|------|
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 進行中 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ⏳ 未開始 |
| 2 | 資訊架構與全域導航 | ⏳ 未開始 |
| 3 | 物品 CRUD + 搜尋 | ⏳ 未開始 |
| 4 | 儀表板與統計 | ⏳ 未開始 |
| 5 | 通知中心 | ⏳ 未開始 |
| 6 | 清單類（旅行、購物、收藏） | ⏳ 未開始 |
| 7 | 協作（群組、借用、轉移） | ⏳ 未開始 |
| 8 | 管理與設定 | ⏳ 未開始 |
| 9 | 行動/PWA 體驗 | ⏳ 未開始 |

## 快速啟動（v2）

```bash
cp .env.example .env
pnpm install
pnpm --filter @ims/api gen:types
pnpm --filter @ims/api-types gen:types
docker compose up --build
# 開啟 http://localhost/
```

## 與 v1 的關係

v1（Flask + Jinja2）程式碼保留於 `app/`、`templates/`、`static/` 等目錄，直到 v2 全部子專案完成後於 `v1-final` tag 保留快照並移除。上線切換採 Big Bang — 舊資料**不遷移**，使用者需重新註冊與錄入。
```

- [ ] **Step 16.2: 更新 `README.md` 最上方**

在 `README.md` 最開頭的 `# 🏠 物品管理系統` 標題下方（第 3 行左右），插入：

```markdown
> **⚠️ v2 重構進行中**：專案正在以 Next.js + FastAPI 全面重寫，參見 [v2 路線圖](docs/v2-roadmap.md)。v1（Flask + Jinja2）仍可運行於 `app/`、`templates/` 目錄，v2 新程式碼位於 `apps/` 目錄。
```

- [ ] **Step 16.3: 提交**

```bash
git add README.md docs/v2-roadmap.md
git commit -m "docs: add v2 quickstart banner and roadmap (#0)"
```

---

## Exit Criteria（#0 完成檢查）

完成以下全部視為 #0 達成，可進入 #1 設計系統子專案的 brainstorming：

- [ ] `pnpm install` 成功、`turbo run build` 全綠
- [ ] `pnpm --filter @ims/api test` 所有測試通過（health + auth utils + auth endpoints，共 14 項）
- [ ] `pnpm --filter @ims/web typecheck` + `build` 全綠
- [ ] `docker compose up` 一鍵啟動，`curl http://localhost/api/health` 回 200
- [ ] 使用者可 POST `/api/auth/register` 建立帳號、以 UI `/login` 登入、refresh cookie 可換發 access token
- [ ] `packages/api-types/src/index.ts` 從 OpenAPI 自動生成可用
- [ ] Playwright E2E 兩個案例通過（正確流程 + 錯誤密碼）
- [ ] CI `.github/workflows/ci.yml` 全綠
- [ ] `README.md` + `docs/v2-roadmap.md` 存在並指向 spec

## Non-Goals（延後到 #1+）

- 深色模式切換 UI（tokens 已就位，但沒有切換按鈕）— #1
- 多語系載入（`next-intl` 已宣告依賴但未建立 messages 檔）— #1 或 #2
- 註冊頁 UI（後端端點已存在，前端 UI 於 #2 資訊架構做）
- 登入端點 rate limit（`slowapi` 已安裝，5/min/IP 於 #8 管理與設定實作時一併加上）
- OAuth（Google/GitHub）— #8
- Web Push、NFC、語音、相機 — 各功能子專案
- APScheduler worker（compose profile 保留，但 #5 通知才啟用）
- `structlog` JSON logging（已安裝，但 `app/main.py` 尚未替換預設 logger；於 #5 通知或 #8 管理時配置）
- Sentry（錯誤監控，延後到上線前 —— 與 #9 整合時一併加入）
- v1 CSV 匯入工具 — #8
