# 部署指南（v2）

目前部署入口為根目錄 `docker-compose.yml`：nginx、Next.js Web、FastAPI API、PostgreSQL 16 與 Redis 7。nginx 對外開放 HTTP port 80；`/api/` 轉送 API，其餘路徑轉送 Web。

## 建置與啟動

主機需有 Docker Compose；目前 Web Dockerfile 要求主機先產生 api-types，因此也需要 Python 3.13、uv、Node.js 22 與 pnpm 9.12.0。

```bash
# 在 repo 根目錄
cp .env.example .env
# 依下表編輯 .env，勿直接使用範例密碼與 secret
make install
make up
# http://localhost/
docker compose ps
```

`make up` 先匯出 OpenAPI、產生 TypeScript 型別，再執行 `docker compose up -d --build`。API 容器會先執行 `alembic upgrade head`（目前到 `0028`），成功後才啟動 uvicorn。首次使用至 `/signup` 註冊；首位使用者可於設定頁啟用管理員。

## 環境設定

| 變數 | 部署時的設定 |
|------|--------------|
| `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` | PostgreSQL 建庫設定；請替換範例密碼 |
| `DATABASE_URL` | `postgresql+asyncpg://帳號:密碼@postgres:5432/資料庫`；與上述設定一致 |
| `REDIS_URL` | Compose 內為 `redis://redis:6379/0` |
| `JWT_SECRET` | 以 `openssl rand -hex 32` 產生並保密，勿使用範例值 |
| `ENVIRONMENT` | 正式部署設為 `production` |
| `CORS_ORIGINS` | JSON 陣列，例如 `["https://ims.example.com"]` |
| `PUBLIC_WEB_URL` | 實際對外網址，用於 QR 與通知信連結 |
| `AI_MODE` | 正式環境使用 `live`；`stub` 僅允許 dev，非 dev 會拒絕啟動 |
| `GEMINI_API_KEY` | 選填；live AI 辨識需要此 key |
| `WEBHOOK_ALLOW_PRIVATE_HOSTS` | 預設 `false`；只有需要 LAN webhook 時才設為 `true`，仍限制 http／https 且不跟隨 redirect |

API 的 `MEDIA_DIR` 由 Compose 設為 `/app/media` 並掛載 `media` volume。Web 在 Compose 使用相對 API base `/api`；開發展示路由預設關閉，正式部署不要啟用 `ENABLE_DEV_ROUTES`。

選用通知整合另需設定 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_FROM`；LINE 使用 `LINE_CHANNEL_ACCESS_TOKEN`，Telegram 使用 `TELEGRAM_BOT_TOKEN`，Web Push 使用 `VAPID_PUBLIC_KEY`、`VAPID_PRIVATE_KEY`、`VAPID_EMAIL`。使用者仍需在設定頁綁定通道與啟用通知偏好。設定的權威來源是 `apps/api/app/config.py`；[環境範例](.env.example) 並未列出所有選用設定。

## TLS 與 proxy

目前 repo 的 nginx 設定僅監聽 HTTP 80，沒有 TLS 終止與憑證管理。正式站台應由前置反向代理處理 HTTPS，並依部署拓樸確認 forwarded headers；目前 nginx 會以自身 `$scheme` 設定 `X-Forwarded-Proto`。API 的 uvicorn 信任 proxy headers，請維持內部網路隔離，不直接公開 API port。

## 外部排程

應用沒有內建排程器。請用管理員 PAT 呼叫 `POST /api/jobs/{job_name}/run`：

| Job | 頻率 |
|-----|------|
| `expiry-scan` | 每日 |
| `report.weekly` | 每週一 |
| `report.monthly` | 每月 1 日 |

例如在已設定 `IMS_BASE_URL` 與 `IMS_PAT` 的排程環境中：

```bash
curl -fsS -X POST "$IMS_BASE_URL/api/jobs/expiry-scan/run" \
  -H "Authorization: Bearer $IMS_PAT"
```

請檢查 job 的回應與設定頁的執行狀態；詳細 cron、時區與補跑語義見[排程文件](docs/scheduling.md)。Compose 的 `worker` profile 是待 Phase 46 清理的死設定，請勿啟用。

## 驗證與資料保存

- 透過站台註冊／登入並完成物品操作，確認 API 與圖片讀寫；API 規格為 `/api/docs`，schema 為 `/api/openapi.json`。
- 以 `make logs` 檢查服務日誌；`make down` 停止服務並保留 volumes。
- `pgdata` 保存資料庫、`media` 保存圖片、`redisdata` 保存 Redis 資料。備份需涵蓋資料庫與圖片；不要使用 `docker compose down -v`，除非確定要刪除資料。

## Release images

`release.yml` 在 `v*.*.*` tag 推送時建置並推送 `ghcr.io/<owner>/<repo>-api` 與 `ghcr.io/<owner>/<repo>-web`，各自產生 SBOM artifact。Image tags 包含完整版本與 `major.minor`；只有不含 `-` 的正式版加上 `latest`。預發佈版的 GitHub Release 標為 prerelease。

現有 Compose 使用本機 `build`，不會自動改用 GHCR image；上方部署流程仍從原始碼建置。v1 歷史快照請查 `v1-final` tag。
