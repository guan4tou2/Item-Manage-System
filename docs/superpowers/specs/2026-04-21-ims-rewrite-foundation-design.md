# 物品管理系統 v2 — 基礎架構設計文件（#0 Foundation Spec）

| 項目 | 內容 |
|------|------|
| 撰寫日期 | 2026-04-21 |
| 專案階段 | 子專案 #0（基礎決策），Sprint 5 之後的 v2 重構 |
| 文件範疇 | 技術堆疊、倉庫結構、部署拓撲、遷移策略；**不含**單一功能的 UI/UX 設計 |
| 後續文件 | #1 設計系統 → #2 資訊架構 → #3 物品 CRUD → … #9 行動體驗 |

## 1. 背景與動機

現行系統為 Flask 3.1 + Jinja2 + Bootstrap 5 的伺服器渲染應用，經 Sprint 1–5 迭代，累積 60+ 路由、30+ 模板、~7,500 行 Python。功能已齊全，但下列瓶頸阻礙進一步提升 UI/UX：

1. **前端受 MPA 限制**：每個操作需整頁重載，無法提供現代互動（即時篩選、樂觀更新、拖放排序、平滑轉場）。
2. **樣式無設計系統**：Bootstrap + 自製 CSS 堆疊缺乏 token 層，難以一致化深色模式、無障礙、響應式。
3. **型別安全缺席**：Python 後端與前端 JS 各自為政，新功能（NFC、語音、AI 推薦）已暴露鬆散 payload 所帶來的 bug 風險。
4. **元件可重用性低**：既有模板高度耦合頁面 route，難以抽出共用元件。

v2 目標：**在不犧牲功能廣度的前提下，把 UI/UX 天花板抬到現代 SaaS 水準，並建立型別安全、可長期擴展的工程骨幹**。

## 2. 目標與非目標

### 2.1 目標（Goals）

- 前端採用 SPA 架構，所有互動以 JSON API 驅動。
- 後端純 API，統一以 OpenAPI 3.1 描述，型別同步至前端。
- 視覺系統支援深色模式、響應式、a11y WCAG 2.1 AA。
- 部署模型與現行一致（單機 Docker Compose），降低維運切換成本。
- 功能對等：所有 Sprint 1–5 功能在 v2 保留或重新設計。

### 2.2 非目標（Non-Goals）

- **不做** 原生 iOS/Android App（PWA 已足夠）。
- **不做** 微服務拆分或 Kubernetes 遷移（Compose 單機即可）。
- **不保留** 舊資料：v2 為全新部署，使用者重新註冊、重新錄入物品（見 §7）。
- **不做** 功能擴展：#0 僅定義骨架，新功能由 #1–#9 各自設計。

## 3. 技術堆疊

### 3.1 前端

| 面向 | 選型 | 備註 |
|------|------|------|
| 框架 | Next.js 15+（App Router） | React Server Components 選擇性使用；主力仍為 Client Components |
| 語言 | TypeScript 5.4+（strict） | 全專案啟用 `strict` 與 `noUncheckedIndexedAccess` |
| 樣式 | Tailwind CSS 3.4+ | 設計 token 在 `tailwind.config.ts` 單一來源 |
| UI 元件 | shadcn/ui（Radix UI 底層） | 以「複製原始碼到專案」方式使用，不鎖 lock-in |
| 表單 | React Hook Form + Zod | 與後端 Pydantic schema 對齊 |
| 伺服器狀態 | TanStack Query v5 | 快取、樂觀更新、背景重新取得 |
| 本地狀態 | Zustand | 僅用於跨元件 UI 狀態（側欄開合、命令面板等） |
| 路由 | Next.js App Router | 檔案系統路由 |
| i18n | `next-intl` | 預載 zh-TW、en；訊息檔在 `apps/web/messages/` |
| 圖表 | Recharts 或 Tremor | #4 儀表板再定案 |
| 日期 | date-fns + date-fns-tz | |
| 測試 | Vitest（單元）、Playwright（E2E） | |
| 建置 | Turbopack（dev）、Next build（prod） | |

### 3.2 後端

| 面向 | 選型 | 備註 |
|------|------|------|
| 框架 | FastAPI 0.115+ | 自動 OpenAPI 3.1 |
| 語言 | Python 3.13+ | 延續現行版本 |
| ORM | SQLAlchemy 2.0（async） | 轉為 async session，釋放 FastAPI 效能 |
| 資料驗證 | Pydantic v2 | schemas 單一來源 |
| 認證 | 自刻 JWT（python-jose + passlib） | Access + refresh；refresh 放 HttpOnly cookie；不引入 `fastapi-users` 以保最大彈性 |
| 資料庫 | PostgreSQL 16+ | MongoDB 支援**移除**（簡化維護） |
| 快取 | Redis 7+ | 延續現行使用 |
| 排程 | APScheduler 3.11+ | 延續，因 Python 生態熟悉 |
| 背景任務 | FastAPI BackgroundTasks + APScheduler Worker | 不引入 Celery，簡化架構 |
| Email | `fastapi-mail` | |
| 速率限制 | `slowapi` | Flask-Limiter 對等替代 |
| 檔案儲存 | 本地磁碟（預設）/ S3（可選） | 透過 `StorageBackend` 介面抽象 |
| 測試 | pytest + httpx.AsyncClient | 保留現有 services/repositories 測試精神 |
| 遷移 | Alembic | 保留現行設定 |

### 3.3 跨棧

| 面向 | 做法 |
|------|------|
| 型別同步 | FastAPI → OpenAPI 3.1 JSON → `openapi-typescript` 於前端生成 `packages/api-types/index.ts` |
| API 客戶端 | 前端 `lib/api/client.ts`（fetch wrapper，注入型別） |
| 監控 | Sentry（前後端） + 保留現有 `/health`、`/ready`、`/metrics` |
| 日誌 | 後端 `structlog` JSON 格式 |

## 4. 倉庫結構（Monorepo）

採用 pnpm workspaces + Turborepo，Python 側獨立 `pyproject.toml`。

```
item-manage-system/
├── apps/
│   ├── web/                    # Next.js 15
│   │   ├── app/                # App Router 路由
│   │   ├── components/         # 共用 UI 元件
│   │   ├── features/           # feature-sliced：items/, locations/, notifications/...
│   │   ├── lib/                # api client、auth、utils
│   │   ├── messages/           # i18n JSON
│   │   └── tests/              # Playwright E2E
│   └── api/                    # FastAPI
│       ├── app/
│       │   ├── main.py
│       │   ├── models/         # SQLAlchemy
│       │   ├── schemas/        # Pydantic
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── routes/
│       │   ├── auth/
│       │   ├── scheduler/
│       │   └── workers/
│       ├── alembic/            # migrations
│       └── tests/              # pytest
├── packages/
│   ├── api-types/              # OpenAPI 生成的 TS 型別（read-only）
│   └── config/                 # 共用 ESLint、Prettier、tsconfig、tailwind preset
├── docker-compose.yml
├── Dockerfile.web
├── Dockerfile.api
├── .github/workflows/          # CI
├── docs/superpowers/specs/     # 本文件所在
├── package.json                # pnpm workspaces root
└── pnpm-workspace.yaml
```

`apps/web/features/*` 採 feature-sliced 設計：每個功能資料夾自足（`components/`、`hooks/`、`api.ts`、`types.ts`），#3 起每個子專案新增一個 feature slice。

## 5. 部署拓撲

### 5.1 Docker Compose 服務清單

| 服務 | 說明 | Port |
|------|------|------|
| `nginx` | 反向代理；`/` → `web:3000`、`/api/*` → `api:8000` | 80/443 |
| `web` | Next.js（Node 22）standalone 輸出 | 3000（內部） |
| `api` | FastAPI（uvicorn workers） | 8000（內部） |
| `worker` | APScheduler 排程容器（共用 api image） | — |
| `postgres` | PostgreSQL 16 | 5432（內部） |
| `redis` | Redis 7 | 6379（內部） |

優點：單機一鍵啟動、與現行運維心智模型一致、Nginx 集中處理 HTTPS/CORS/快取標頭。

### 5.2 環境

- **dev**：`docker compose -f docker-compose.dev.yml up`，啟用 hot reload（`web` 容器掛載 volume、api 用 uvicorn `--reload`）。
- **prod**：`docker compose up -d`，健康檢查、log rotation、備份 cron（Postgres + `uploads/`）。

## 6. 認證與安全

- **Access token**：JWT（15 分鐘），存於前端 JS 變數（non-persistent，分頁關閉即失效）；每次請求帶 `Authorization: Bearer`。
- **Refresh token**：JWT（7 天），HttpOnly + Secure + SameSite=Lax cookie；`/api/auth/refresh` 換新 access。
- **密碼**：Argon2id（`passlib[argon2]`）。
- **CSRF**：因 access token 非 cookie，攻擊面縮小；refresh 端點加 double-submit cookie token 以防 CSRF。
- **CORS**：僅允許 `https://<your-domain>`；`credentials: include` 支援 refresh cookie。
- **速率限制**：登入端點 5/min/IP；其他 60/min/user。
- **安全標頭**：Nginx 統一注入 CSP、HSTS、X-Content-Type-Options、Referrer-Policy。
- **OAuth/SSO**：Google、GitHub 預留（#0 不實作，#8 管理與設定子專案處理）。

## 7. 資料策略（v1 → v2）

**決策：不遷移舊資料（Drop-and-Rebuild）**。理由與執行：

1. v2 schema 將隨各子專案調整（例如 #3 可能重新設計 `item` 欄位、#7 重新設計 group 模型），保留舊資料會被迫相容 legacy schema。
2. v1 保留於 `legacy/` 分支與 tag `v1-final`，Docker image 保留 6 個月以備查。
3. 上線切換步驟（§9 詳述）包含「匯出 v1 重要報表 → 新環境重新錄入重點資料（若使用者需要）」。
4. 使用者認知：上線公告須明確告知「v2 為全新系統，需要重新註冊並錄入物品」。

**風險**：使用者需重新錄入物品。
**緩解**：#8 管理與設定子專案須提供 v1 CSV 匯入工具，允許從 v1 匯出物品 CSV 後一鍵匯入 v2。

## 8. 功能對等清單（v1 → v2 對照）

| 子專案 | 對應 v1 功能 | v2 負責人 |
|--------|--------------|-----------|
| #1 設計系統 | navbar、modals、signin/signup、深色模式 | UI |
| #2 資訊架構 | home、dashboard、manageitem、menu | 前端 |
| #3 物品 CRUD + 搜尋 | additem、edititem、itemdetail、assets、QR、import | 全棧 |
| #4 儀表板 | dashboard、metrics、stats | 全棧 |
| #5 通知中心 | notifications、notifications_settings、reminders | 全棧 |
| #6 清單類 | travel list、shopping list、favorites | 全棧 |
| #7 協作 | groups、group_detail、loans、transfers、move_history | 全棧 |
| #8 管理與設定 | admin_users、admin_custom_fields、api_tokens、backup、logs、locations、types、change_password | 全棧 |
| #9 行動/PWA | PWA manifest、NFC、voice、camera、offline | 全棧 |

**範圍保護**：任何 Sprint 1–5 已有但未列入上表的功能，須在其所屬子專案的設計文件內顯式列出。#0 不負責功能決策。

## 9. 遷移執行（Big Bang）

1. 本分支建立 `apps/web/` 與 `apps/api/` 骨架（本次 #0 實作）。
2. 子專案 #1–#9 依序完成、合併至 `main`。
3. 每個子專案合併後，於 staging Compose 環境部署供內部試用。
4. 全部子專案就緒後：
   - v1 關閉寫入（唯讀模式）。
   - 公告使用者 T+7 天後 v1 下線。
   - T 日：DNS 切換 → v2 Compose。
   - v1 保留為 `legacy.` 子網域 30 天供匯出 CSV。
   - T+30：v1 完全下線，保留 Docker image tag `v1-final` 與資料庫快照。
5. 回滾策略：若 v2 上線後 72 小時內出現阻塞 bug，DNS 切回 v1；期間 v2 寫入的新資料以匯出方式重放。

## 10. 工作分解與時程（粗估）

| 子專案 | 估計人日 | 前置相依 |
|--------|---------|---------|
| #0 基礎骨架（本次） | 3–5 | — |
| #1 設計系統 | 3–4 | #0 |
| #2 資訊架構 | 2–3 | #1 |
| #3 物品 CRUD + 搜尋 | 7–10 | #1, #2 |
| #4 儀表板 | 3–4 | #3 |
| #5 通知中心 | 4–5 | #3 |
| #6 清單類 | 4–5 | #3 |
| #7 協作 | 5–6 | #3 |
| #8 管理與設定 | 5–7 | #3 |
| #9 行動/PWA | 3–4 | #3 起陸續 |
| **合計** | **39–53 人日** | |

假設單人全職投入，約 8–11 週完成；含測試與打磨可抓 3 個月。

## 11. 風險與緩解

| 風險 | 影響 | 緩解 |
|------|------|------|
| FastAPI 重寫引入行為差異 | 高 | 保留 v1 的 pytest 案例做對照，新 API 通過相同測資 |
| 全新認證導致既有 Token 失效 | 中 | #0 即定義 token 結構；v1 使用者重新登入即可 |
| 型別生成漂移（OpenAPI 與 TS 不同步） | 中 | CI 強制跑 `pnpm gen:types` diff check |
| Next.js / shadcn 版本升級破壞 | 低 | 鎖定 minor；Renovate 每週 PR |
| 舊資料丟失爭議 | 中 | CSV 匯出匯入通道；公告明確 |

## 12. 驗收標準（Exit Criteria，#0）

完成 #0 視為達成以下條件：

- [ ] Monorepo 結構建立、pnpm workspaces 可運作。
- [ ] `apps/web` 啟動可看到 Next.js 首頁（空白樣板，含 Tailwind + shadcn Button 示範）。
- [ ] `apps/api` 啟動，`GET /api/health` 回 200 JSON。
- [ ] `docker compose up` 一鍵啟動所有服務，Nginx 路由正確。
- [ ] OpenAPI schema 產出、`packages/api-types` 能生成且 `apps/web` 可 import。
- [ ] 登入/登出/refresh 三端點可運作，前端 `useAuth` hook 範例可通過 E2E。
- [ ] CI pipeline：`pnpm lint`、`pnpm test`、`pytest`、`docker build` 全綠。
- [ ] README 更新，描述 v2 快速啟動與子專案路線圖。

## 13. 未決議題（Deferred）

以下議題留到後續子專案決定，不在 #0 範疇：

- 深色模式切換入口位置（#1）。
- 全域搜尋觸發方式（cmd+k vs 固定欄位）（#2）。
- 物品清單預設檢視（卡片/列表/表格）（#3）。
- 儀表板 widget 種類（#4）。
- 通知分群邏輯（#5）。
- Group 權限模型是否保持 v1（#7）。
- PWA 離線範圍（#9）。

---

**核定狀態**：待使用者審閱。
