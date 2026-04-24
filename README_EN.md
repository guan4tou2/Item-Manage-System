# 🏠 Item Management System v2

> **v2 full rewrite shipped**: Next.js 15 + FastAPI 0.115 + PostgreSQL 16. The v1 (Flask + Jinja2) source remains in `app/` and `templates/` for reference only; no new work lands there.

Inventory for homes and small teams: track where things are, who borrowed what, what's expiring, what's running low. Includes camera QR scanning, AI image recognition, installable PWA, webhooks, and LINE/Telegram/Email/Web Push notifications.

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![API Tests](https://img.shields.io/badge/API%20tests-398%20passed-brightgreen.svg)
![Web Tests](https://img.shields.io/badge/Web%20tests-75%20passed-brightgreen.svg)

[Features](#-features) •
[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[API](#-api) •
[Docs](#-documentation) •
[Changelog](CHANGELOG.md) •
[License](#-license)

</div>

---

## ✨ Features

### Items & organization
- 📦 **Item CRUD** — name, description, quantity, image, notes, tags, favorite
- 🏷 **Categories / tags / custom fields** — item types + custom fields + templates
- 📍 **Location hierarchy** — floor / room / zone with manual sort order and floor-plan images
- 🏢 **Warehouses** — isolation across physical sites (garage, office, storage unit)
- ⭐ **Favorites** — quick access to items you use often

### QR & scanning
- 🏷 **Label generation** — per-item QR label PNG
- 🖨 **Printable** — A4 multi-cell print preview page
- 📷 **Camera scan** — `/scan` opens the camera; scanning a system-issued QR jumps directly to the item
- 🆔 **Bare UUID fallback** — works with UUIDs or full URLs

### AI assistance
- 🤖 **Gemini image recognition** — upload a photo, get name / description / category / tag suggestions in one tap
- 🗣 **Chinese-first prompt** — returns Traditional Chinese

### Loans & movement
- 🤝 **Loan records** — who, what, when do you expect it back
- ⏰ **Overdue flagging** — dashboard auto-marks `is_overdue`
- 🔄 **Transfer history** — location / warehouse changes are logged

### Notifications
- 📧 **Email** (SMTP via fastapi-mail)
- 💬 **LINE Messaging API push**
- 📱 **Telegram Bot `sendMessage`**
- 🔔 **Web Push + VAPID**
- ♻️ **Fail-soft** — a failing channel never blocks the notification itself

### Stocktake & inventory
- 📋 **Batch stocktake** — session scan → apply deltas → quantity log written automatically
- 🚨 **Low stock alerts** — `quantity < min_quantity` surfaces on the dashboard, sorted by deficit
- 📊 **Quantity history** — every change records old → new + reason + user
- 📸 **Version snapshots** — full-state snapshot before material edits

### Webhooks & open API
- 🔗 **Webhook dispatch** — user HTTP endpoints subscribe to `item.created` / `item.updated` / `item.deleted`
- 🔐 **HMAC-SHA256 signature** — `X-IMS-Signature` header
- 🔑 **Personal Access Tokens** — `ims_pat_` prefix, stored as SHA-256
- 🧾 **Audit log** — sensitive ops all recorded

### Dashboard & stats
- 📊 **Overview** — items / quantity / categories / locations / warehouses / low stock / active loans
- 📈 **30-day item trend** — dense daily area chart
- 🥧 **Distribution charts** — category / location / warehouse / tag
- 📝 **Activity feed** — merged quantity log, loans, returns, version snapshots

### Data in/out
- 📥 **Bulk CSV import** — dry-run preview, per-row validation, failure reasons with row numbers
- 📤 **CSV export** — streamed output that respects query filters
- 💾 **Full backup** — `GET /api/backup/export` versioned JSON dump

### Collaboration
- 👥 **Groups** — share item visibility across users
- 🔒 **Roles** — admin / member
- 📜 **Audit** — who did what

### Mobile / PWA
- 📱 **Install to home screen** — full PWA manifest (Android + iOS)
- ⚡ **Home-screen shortcuts** — long-press the icon to jump to Scan / New Item / Dashboard
- 🌐 **Offline page** — service worker cache + fallback
- 🎨 **Dark mode** — follow system or manual toggle
- 🌍 **i18n** — Traditional Chinese + English

---

## 🚀 Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/guan4tou2/Item-Manage-System.git
cd Item-Manage-System
cp .env.example .env       # fill in GEMINI_API_KEY, SMTP, etc. as needed
pnpm install
docker compose up --build
# → http://localhost/
```

Register your first user at `/signup`, then promote yourself via the "啟用管理員 / Enable admin" button in Settings (calls `POST /api/admin/bootstrap`).

### Local dev (no Docker)

Prereqs: Python 3.13, Node 20+, pnpm, PostgreSQL 16 (or `docker compose up postgres`).

```bash
# API
cd apps/api
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000

# Web (separate terminal)
cd apps/web
pnpm install
pnpm dev
# → http://localhost:3000/
```

### Required env vars

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | JWT signing secret |
| `MEDIA_DIR` | Upload storage path |
| `GEMINI_API_KEY` | (opt) enables AI recognition |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | (opt) email notifications |
| `LINE_CHANNEL_ACCESS_TOKEN` | (opt) LINE push |
| `TELEGRAM_BOT_TOKEN` | (opt) Telegram push |
| `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` | (opt) Web Push |

See [.env.example](.env.example) for the full list.

---

## 🏗 Architecture

```
monorepo (pnpm workspace)
├── apps/
│   ├── api/          FastAPI 0.115 + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
│   └── web/          Next.js 15 App Router + shadcn/ui + Tailwind + next-intl
├── packages/
│   └── api-types/    OpenAPI schema → TS types (generator in generate.mjs)
├── docs/             Technical docs (ARCHITECTURE, API, v2-roadmap, specs/)
└── app/, templates/  v1 Flask source (legacy, read-only reference)
```

- **Database**: PostgreSQL 16 (prod) / SQLite (tests). Cross-backend columns unified through custom `GUID` and `JSONType` decorators
- **Auth**: JWT access token (15 min) + httpOnly refresh cookie (7 day)
- **Migrations**: Alembic (current head `0014`)
- **OpenAPI**: auto-generated by FastAPI; TS types in `packages/api-types` regen after every schema change
- **Tests**: pytest-asyncio + FastAPI TestClient (398 passed); vitest + jsdom (75 passed)

---

## 🔌 API

Full spec is auto-generated by FastAPI:

- Dev: http://localhost:8000/docs (Swagger UI)
- OpenAPI JSON: http://localhost:8000/openapi.json
- Repo: [`packages/api-types/openapi.json`](packages/api-types/openapi.json)

Main route families:

| Prefix | Purpose |
|--------|---------|
| `/api/auth` | register / login / refresh / logout |
| `/api/items` | CRUD + search + favorites + bulk CSV + labels |
| `/api/categories` · `/api/locations` · `/api/warehouses` · `/api/tags` | taxonomy |
| `/api/items/{id}/loans` | loan lifecycle |
| `/api/stats/*` | overview / by-category / by-location / by-warehouse / by-tag / low-stock / active-loans / trend / activity / recent |
| `/api/notifications` | in-app notifications |
| `/api/webhooks` | custom HTTP hooks + HMAC signing |
| `/api/images` | upload / fetch / delete |
| `/api/ai/suggest` | Gemini recognition |
| `/api/backup/export` | data export |
| `/api/admin/*` | admin (user list, audit log) |

---

## 📚 Documentation

| Doc | Content |
|-----|---------|
| [CHANGELOG.md](CHANGELOG.md) | Per-phase breakdown of all 16 v2 releases |
| [FEATURES.md](FEATURES.md) | Per-feature deep dive (v2) |
| [docs/v2-roadmap.md](docs/v2-roadmap.md) | Sub-project roadmap and status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture diagrams, data flow, layering |
| [docs/API.md](docs/API.md) | API route index (against OpenAPI) |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development workflow, testing, migrations |
| [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md) | Deployment guide (zh-TW) |
| [User_Manual_zh-TW.md](User_Manual_zh-TW.md) | User manual (zh-TW) |
| [README.md](README.md) | 繁體中文 README |

---

## 🧪 Tests

```bash
# API
cd apps/api && .venv/bin/python -m pytest -q
# → 398 passed

# Web
cd apps/web && pnpm test
# → 75 passed across 19 files
```

---

## 🛠 Contributing

1. Branch from `main`: `git checkout -b feat/my-thing`
2. Each phase is best developed in an isolated worktree at `.claude/worktrees/<name>`
3. Before the PR: run both test suites, regen api-types, typecheck the web app
4. Commit message style: `feat: Phase N — …`

---

## 📜 License

MIT — see [LICENSE](LICENSE).
