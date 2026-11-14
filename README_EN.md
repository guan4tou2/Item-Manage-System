# 🏠 Item Management System v2

> **v2 全面重寫已完成**：Next.js 15 + FastAPI + PostgreSQL 16。v1（Flask + Jinja2）已下線，歷史快照保留於 `v1-final` tag。

Inventory for homes and small teams: track where things are, who borrowed what, what's expiring, what's running low. Includes camera QR scanning, AI image recognition, installable PWA, webhooks, and LINE/Telegram/Email/Web Push notifications.

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162.6-009688.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![API Tests](https://img.shields.io/badge/API%20tests-1524%20passed-brightgreen.svg)
![Web Tests](https://img.shields.io/badge/Web%20tests-926%20passed-brightgreen.svg)

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
make install
make up
# → http://localhost/
```

Register your first user at `/signup`, then promote yourself via the "啟用管理員 / Enable admin" button in Settings (calls `POST /api/admin/bootstrap`).

### 本機開發（不使用 Docker）

需要 Python 3.13、Node.js 22、pnpm 9.12.0、uv 與可連線的 PostgreSQL 16。API 與 Web 分別啟動；本機的資料庫連線、API base 與環境變數設定請依[開發指南](docs/DEVELOPMENT.md)。Compose 的 PostgreSQL 沒有對主機發佈 port。

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

常用設定見 [.env.example](.env.example)；完整欄位以 `apps/api/app/config.py` 為準。

---

## 🏗 Architecture

```
monorepo (pnpm workspace)
├── apps/
│   ├── api/          FastAPI 0.162.6 + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
│   └── web/          Next.js 15 App Router + shadcn/ui + Tailwind + next-intl
├── packages/
│   └── api-types/    OpenAPI schema → TS types (generator in generate.mjs)
├── docs/             架構、開發、排程與路線圖
├── nginx/            HTTP 反向代理
└── docker-compose.yml  v2 服務編排
```

- **Database**: PostgreSQL 16 (prod) / SQLite (tests). Cross-backend columns unified through custom `GUID` and `JSONType` decorators
- **Auth**: JWT access token (15 min) + httpOnly refresh cookie (7 day)
- **Migrations**: Alembic (current head `0028`)
- **OpenAPI**: auto-generated by FastAPI; TS types in `packages/api-types` regen after every schema change
- **Tests**: pytest-asyncio + FastAPI TestClient (1524 passed); vitest + jsdom (926 passed across 148 files)

---

## 🔌 API

Full spec is auto-generated by FastAPI:

- Dev: http://localhost:8000/api/docs (Swagger UI)
- OpenAPI JSON: http://localhost:8000/api/openapi.json
- Repo: [`packages/api-types/openapi.json`](packages/api-types/openapi.json)

文件頁與 `/api/openapi.json` 僅 dev 預設開啟，`API_DOCS_ENABLED` 可覆寫；非 dev 預設關閉。`make gen-types` 的離線 schema 匯出不受影響。部署包含 DB readiness、request id／結構化日誌與 nginx CSP，詳見[部署指南](Deployment_Guide_zh-TW.md)。

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
| [CHANGELOG.md](CHANGELOG.md) | 逐 phase 變更 |
| [FEATURES.md](FEATURES.md) | Per-feature deep dive (v2) |
| [docs/v2-roadmap.md](docs/v2-roadmap.md) | Sub-project roadmap and status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture diagrams, data flow, layering |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development workflow, testing, migrations |
| [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md) | Deployment guide (zh-TW) |
| [User_Manual_zh-TW.md](User_Manual_zh-TW.md) | User manual (zh-TW) |
| [README.md](README.md) | 繁體中文 README |

---

## 🧪 Tests

```bash
# API
make test-api
# → 1524 passed

# Web
make test-web
# → 926 passed across 148 files
```

---

既有 e2e 基線：Phase 47 為 **31 spec／99 情境**（含 ai-stub；1 個位置樹情境依賴舊 fixture 而 skip），Phase 48–50 新增的情境由 CI 執行。

## 🛠 Contributing

1. Branch from `main`: `git checkout -b feat/my-thing`
2. Each phase is best developed in an isolated worktree at `.claude/worktrees/<name>`
3. Before the PR: run both test suites, regen api-types, typecheck the web app
4. Commit message style: `feat: Phase N — …`

---

## 📜 License

MIT — see [LICENSE](LICENSE).
