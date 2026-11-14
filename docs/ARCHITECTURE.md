# 系統架構（v2）

IMS v2 是 pnpm workspace monorepo。Web 使用 Next.js 15 App Router、React、Tailwind CSS 與 next-intl；API 使用 Python 3.13、FastAPI、Pydantic v2 與 SQLAlchemy async。正式資料庫為 PostgreSQL 16，Alembic migration 目前到 `0033`。

## 程式碼分工

| 路徑 | 責任 |
|------|------|
| `apps/api/app/routes/` | HTTP 路由、認證依賴與請求／回應介面 |
| `apps/api/app/services/` | 物品、通知、AI、排程等業務邏輯 |
| `apps/api/app/repositories/` | 資料存取 |
| `apps/api/app/models/`、`schemas/` | SQLAlchemy model 與 Pydantic schema |
| `apps/api/alembic/` | 資料庫遷移 |
| `apps/web/` | Web 介面、API client、PWA 與前端測試 |
| `packages/api-types/` | OpenAPI 匯出資料與產生的 TypeScript 型別 |
| `nginx/` | Compose 對外 HTTP 入口 |

## 請求與資料流

```text
瀏覽器 → nginx :80 ─ /api/* → API :8000 → PostgreSQL
                  └ 其他路徑 → Web :3000
```

Compose 只有 nginx 發佈主機 port。API 與 Web 使用內部網路；nginx 保留 `/api/` 路徑並轉送來源 IP 等 headers。API 的 uvicorn 信任 proxy headers，因此不可直接暴露 API 到不受信任的網路。

API 啟動時執行 `alembic upgrade head`。PostgreSQL 與圖片分別使用 `pgdata`、`media` named volumes；圖片在 API 容器內的 `MEDIA_DIR=/app/media`。API 以 uid 10001、Web 以 node 執行；API 依 uv.lock 多階段建置，media 需可寫。

## 認證與整合

- JWT access token 預設 15 分鐘，httpOnly refresh cookie 預設 7 天；session 版本用於改密碼與登出所有裝置的撤銷。
- Personal Access Token 用於 API 整合與外部排程；權限隨所屬使用者。
- 通知可透過 SMTP、LINE、Telegram 與 Web Push 發送；設定集中於 `apps/api/app/config.py`。
- Webhook 預設限制公網目的地；內網例外由 `WEBHOOK_ALLOW_PRIVATE_HOSTS` 明確開啟。
- AI 預設使用 `AI_MODE=live`；需要 Gemini key。`stub` 僅允許在 `ENVIRONMENT=dev` 使用。

## 排程與 API 規格

應用不內建排程器；外部 cron 呼叫管理員 job 端點，執行每日到期掃描、每週及每月報表。Compose 已移除未使用的 worker 與 Redis。排程設定見[排程與到期提醒](scheduling.md)。

FastAPI 僅在 dev 預設提供 `/api/docs`、`/api/redoc` 與 `/api/openapi.json`，`API_DOCS_ENABLED` 可覆寫；直接呼叫 `app.openapi()` 不受影響。`make gen-types` 先執行 API 的 OpenAPI 匯出程式，再產生 `packages/api-types/src/index.ts`；Web image 建置前必須完成這一步。

v1（Flask／Jinja2）已從目前工作樹下線，歷史快照保留於 `v1-final` tag。開發流程見[開發指南](DEVELOPMENT.md)，部署見[部署指南](../Deployment_Guide_zh-TW.md)。

## 部署與可觀測

- `/api/health` 為 liveness；`/api/health/ready` 對 DB 執行 `SELECT 1`，以 200／503 表示 ready／unavailable，不洩漏例外。Compose 的 Web／nginx 等待 API healthy。
- `LOG_FORMAT=json|text`（dev 預設 text，其餘 json）、`LOG_LEVEL=INFO`；標準 logging handler 可重複設定，保留宿主與 pytest handler。
- 純 ASGI middleware 以 contextvars 傳遞 request id 並回傳 `X-Request-ID`，不緩衝串流；access log 不含 query string 與本文，略過 `/api/health*`。uvicorn 關閉自身 access log。
- nginx 統一送出 CSP、Permissions-Policy 與既有安全標頭，僅 `X-Forwarded-Proto: https` 回傳 HSTS；前置 TLS 代理必須覆寫該 header。CSP 允許同源與必要 inline script／style，access token 依 D12 保留 localStorage。
- CI API gate 包含 ruff（F＋E9）、pytest、golden eval、PostgreSQL migration 升降版；e2e job 以完整 Compose 驗證 chromium 與 ai-stub，失敗保存 trace 與服務日誌。實際 CI／部署驗證狀態見 [本輪進度](progress-2026-11-14-b.md)。
