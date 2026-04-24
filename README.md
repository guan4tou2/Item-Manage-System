# 🏠 物品管理系統 v2

> **v2 全面重寫已完成**：Next.js 15 + FastAPI 0.115 + PostgreSQL 16。v1（Flask + Jinja2）程式碼保留於 `app/`、`templates/` 目錄作為參考，但不再接受新功能。

家庭與小型團隊的物品管理：記錄放在哪裡、誰借走了、什麼快過期、什麼庫存不足。含相機 QR 掃描、AI 辨識、可安裝 PWA、webhook、LINE/Telegram/Email/Web Push 通知。

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![API Tests](https://img.shields.io/badge/API%20tests-398%20passed-brightgreen.svg)
![Web Tests](https://img.shields.io/badge/Web%20tests-75%20passed-brightgreen.svg)

[功能](#-核心功能) •
[快速開始](#-快速開始) •
[架構](#-技術架構) •
[API](#-api) •
[文件](#-文件) •
[變更紀錄](CHANGELOG.md) •
[授權](#-授權)

</div>

---

## ✨ 核心功能

### 物品與組織
- 📦 **物品 CRUD** — 名稱、描述、數量、圖片、備註、標籤、收藏
- 🏷 **分類 / 標籤 / 自訂欄位** — item types + custom fields + templates
- 📍 **位置階層** — 樓層 / 房間 / 區域，支援手動排序與樓層平面圖
- 🏢 **倉庫** — 跨實體場所的隔離（車庫、辦公室、倉儲）
- ⭐ **收藏** — 常用物品快速存取

### 掃碼 / QR
- 🏷 **標籤產生** — 每件物品專屬 QR 標籤（PNG）
- 🖨 **可列印** — A4 多格列印預覽頁
- 📷 **相機掃碼** — `/scan` 頁開啟相機，掃到本系統 QR 自動跳轉物品頁
- 🆔 **裸 UUID fallback** — 掃到 UUID 或 URL 皆可

### AI 輔助
- 🤖 **Gemini 圖像辨識** — 上傳物品照片後一鍵建議名稱 / 描述 / 分類 / 標籤
- 🗣 **繁中提示** — 提示語為繁體中文，結果就是繁中

### 借出 / 流動追蹤
- 🤝 **借出紀錄** — 誰、借什麼、預計何時歸還
- ⏰ **逾期提示** — 儀表板自動標示 is_overdue
- 🔄 **轉移紀錄** — 位置 / 倉庫變更有歷史

### 通知
- 📧 **Email**（SMTP via fastapi-mail）
- 💬 **LINE Messaging API push**
- 📱 **Telegram Bot `sendMessage`**
- 🔔 **Web Push + VAPID**
- ♻️ **Fail-soft** — 任何管道失敗不影響通知建立本身

### 盤點與庫存
- 📋 **批次盤點** — session 掃碼 → 差額套用 → quantity log 自動記錄
- 🚨 **低庫存警示** — `quantity < min_quantity` 自動上儀表板（依 deficit 排序）
- 📊 **數量歷史** — 每次變動記錄 old → new + reason + user
- 📸 **版本快照** — 關鍵變更前自動 snapshot 完整狀態

### Webhooks & 開放 API
- 🔗 **Webhook dispatch** — 用戶自訂 HTTP endpoint 訂閱 `item.created` / `item.updated` / `item.deleted`
- 🔐 **HMAC-SHA256 簽章** — `X-IMS-Signature` header
- 🔑 **Personal Access Tokens** — `ims_pat_` 前綴、SHA-256 雜湊存放
- 🧾 **稽核日誌** — 敏感操作全紀錄

### 儀表板與統計
- 📊 **Overview** — items / quantity / categories / locations / warehouses / low stock / active loans
- 📈 **30 天新增趨勢** — area chart（稠密時間序列）
- 🥧 **分布圖表** — 分類 / 位置 / 倉庫 / 標籤 pie + bar
- 📝 **活動流** — 合併 quantity log、借出、歸還、版本快照

### 資料進出
- 📥 **CSV 批次匯入** — dry-run 預覽、per-row 驗證、失敗原因附列號
- 📤 **CSV 匯出** — 支援 query 篩選的串流輸出
- 💾 **完整備份** — `GET /api/backup/export` JSON dump（versioned）

### 協作
- 👥 **群組** — 跨用戶分享物品可見性
- 🔒 **權限** — admin / member
- 📜 **稽核** — 誰做了什麼

### 手機 / PWA
- 📱 **安裝到主畫面** — 完整 PWA manifest（Android + iOS）
- ⚡ **Home-screen shortcuts** — 長按 icon 直跳 掃碼 / 新增物品 / 儀表板
- 🌐 **離線頁** — service worker 快取 + fallback
- 🎨 **深色模式** — 跟隨系統或手動切換
- 🌍 **i18n** — 繁體中文 + English

---

## 🚀 快速開始

### 本地開發（推薦用 Docker Compose）

```bash
git clone https://github.com/guan4tou2/Item-Manage-System.git
cd Item-Manage-System
cp .env.example .env       # 視需要填入 GEMINI_API_KEY、SMTP 等
pnpm install
docker compose up --build
# → http://localhost/
```

首次登入請先註冊（`/signup`），之後可自行啟用管理員：在設定頁按「啟用管理員」按鈕（呼叫 `POST /api/admin/bootstrap`）。

### 本機非 Docker

前置需求：Python 3.13、Node 20+、pnpm、PostgreSQL 16（或單獨起 `docker compose up postgres`）。

```bash
# API
cd apps/api
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000

# Web（另一個終端）
cd apps/web
pnpm install
pnpm dev
# → http://localhost:3000/
```

### 必要環境變數

| 變數 | 用途 |
|------|------|
| `DATABASE_URL` | PostgreSQL 連線字串 |
| `JWT_SECRET` | JWT 簽章密鑰 |
| `MEDIA_DIR` | 上傳圖片儲存路徑 |
| `GEMINI_API_KEY` | （選）啟用 AI 辨識 |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | （選）Email 通知 |
| `LINE_CHANNEL_ACCESS_TOKEN` | （選）LINE 推播 |
| `TELEGRAM_BOT_TOKEN` | （選）Telegram 推播 |
| `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` | （選）Web Push |

參見 [.env.example](.env.example) 取得完整列表。

---

## 🏗 技術架構

```
monorepo (pnpm workspace)
├── apps/
│   ├── api/          FastAPI 0.115 + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
│   └── web/          Next.js 15 App Router + shadcn/ui + Tailwind + next-intl
├── packages/
│   └── api-types/    OpenAPI schema → TS types (產生器在 generate.mjs)
├── docs/             技術文件（ARCHITECTURE、API、v2-roadmap、specs/）
└── app/, templates/  v1 Flask 實作（legacy，唯讀參考）
```

- **資料庫**：PostgreSQL 16（正式環境）/ SQLite（測試）。跨後端欄位用自訂 `GUID`、`JSONType` decorator 統一抽象
- **驗證**：JWT access token（15 min）+ httpOnly refresh cookie（7 day）
- **遷移**：Alembic（目前在 `0014`）
- **OpenAPI**：FastAPI 自動產生，TS 型別由 `packages/api-types` 每次 regen 同步
- **測試**：pytest-asyncio + FastAPI TestClient（398 passed）、vitest + jsdom（75 passed）

---

## 🔌 API

完整規格由 FastAPI 自動產生：

- 開發：http://localhost:8000/docs （Swagger UI）
- OpenAPI JSON：http://localhost:8000/openapi.json
- Repo：[`packages/api-types/openapi.json`](packages/api-types/openapi.json)

主要路由家族：

| 前綴 | 說明 |
|------|------|
| `/api/auth` | register / login / refresh / logout |
| `/api/items` | CRUD + search + favorites + bulk CSV + labels |
| `/api/categories` · `/api/locations` · `/api/warehouses` · `/api/tags` | 分類體系 |
| `/api/items/{id}/loans` | 借出週期 |
| `/api/stats/*` | overview / by-category / by-location / by-warehouse / by-tag / low-stock / active-loans / trend / activity / recent |
| `/api/notifications` | 站內通知 |
| `/api/webhooks` | 自訂 HTTP hooks + HMAC 簽章 |
| `/api/images` | 上傳 / 取得 / 刪除 |
| `/api/ai/suggest` | Gemini 辨識 |
| `/api/backup/export` | 資料匯出 |
| `/api/admin/*` | 管理員（users 列表、audit log） |

---

## 📚 文件

| 文件 | 內容 |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | 16 個 v2 phase 的逐項變更 |
| [FEATURES.md](FEATURES.md) | 每個功能的詳細說明（v2） |
| [docs/v2-roadmap.md](docs/v2-roadmap.md) | 子專案路線圖與現況 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架構圖、資料流、分層策略 |
| [docs/API.md](docs/API.md) | API 路由索引（由 OpenAPI 對照） |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 開發流程、測試、遷移 |
| [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md) | 部署指南 |
| [User_Manual_zh-TW.md](User_Manual_zh-TW.md) | 使用手冊 |
| [README_EN.md](README_EN.md) | English README |

---

## 🧪 測試

```bash
# API
cd apps/api && .venv/bin/python -m pytest -q
# → 398 passed

# Web
cd apps/web && pnpm test
# → 75 passed across 19 files
```

---

## 🛠 貢獻

1. 從 `main` 開分支：`git checkout -b feat/my-thing`
2. 每個 phase 建議在 `.claude/worktrees/<name>` 做 worktree 獨立開發
3. PR 前跑滿兩套測試、regen api-types、typecheck web
4. 訊息格式參考既有 `feat: Phase N — …`

---

## 📜 授權

MIT — 參見 [LICENSE](LICENSE)。
