# 部署指南（v2）

目前部署入口為根目錄 `docker-compose.yml`：nginx、Next.js Web、FastAPI API、PostgreSQL 16。nginx 對外開放 HTTP port 80；`/api/` 轉送 API，其餘路徑轉送 Web。

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

`make up` 先匯出 OpenAPI、產生 TypeScript 型別，再執行 `docker compose up -d --build`。API 容器會先執行 `alembic upgrade head`（目前到 `0033`），成功後才啟動 uvicorn。首次使用至 `/signup` 註冊；首位使用者可於設定頁啟用管理員。

## 環境設定

| 變數 | 部署時的設定 |
|------|--------------|
| `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` | PostgreSQL 建庫設定；請替換範例密碼 |
| `DATABASE_URL` | `postgresql+asyncpg://帳號:密碼@postgres:5432/資料庫`；與上述設定一致 |
| `JWT_SECRET` | 以 `openssl rand -hex 32` 產生並保密，勿使用範例值 |
| `ENVIRONMENT` | 正式部署設為 `production` |
| `LOG_FORMAT`、`LOG_LEVEL` | 格式為 `json`／`text`；dev 預設 text，其餘 json；層級預設 INFO |
| `API_DOCS_ENABLED` | 留空依環境決定：僅 dev 開啟；true／false 明確覆寫文件頁與 schema 路由 |
| `CORS_ORIGINS` | JSON 陣列，例如 `["https://ims.example.com"]` |
| `PUBLIC_WEB_URL` | 實際對外網址，用於 QR 與通知信連結 |
| `AI_MODE` | 正式環境使用 `live`；`stub` 僅允許 dev，非 dev 會拒絕啟動 |
| `GEMINI_API_KEY` | 選填；live AI 辨識需要此 key |
| `WEBHOOK_ALLOW_PRIVATE_HOSTS` | 預設 `false`；只有需要 LAN webhook 時才設為 `true`，仍限制 http／https 且不跟隨 redirect |

API 的 `MEDIA_DIR` 由 Compose 設為 `/app/media` 並掛載 `media` volume。Web 在 Compose 使用相對 API base `/api`；開發展示路由預設關閉，正式部署不要啟用 `ENABLE_DEV_ROUTES`。

選用通知整合另需設定 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_FROM`；LINE 使用 `LINE_CHANNEL_ACCESS_TOKEN`，Telegram 使用 `TELEGRAM_BOT_TOKEN`，Web Push 使用 `VAPID_PUBLIC_KEY`、`VAPID_PRIVATE_KEY`、`VAPID_EMAIL`。使用者仍需在設定頁綁定通道與啟用通知偏好。設定的權威來源是 `apps/api/app/config.py`；[環境範例](.env.example) 並未列出所有選用設定。

## TLS 與 proxy

目前 repo 的 nginx 設定僅監聽 HTTP 80，沒有 TLS 終止與憑證管理。正式站台應由前置反向代理處理 HTTPS，並依部署拓樸確認 forwarded headers；目前 nginx 會以自身 `$scheme` 設定 `X-Forwarded-Proto`。API 的 uvicorn 信任 proxy headers，請維持內部網路隔離，不直接公開 API port。

nginx 統一附加 CSP、`Permissions-Policy: camera=(self), microphone=(), geolocation=()` 與既有安全標頭。CSP 限制外送目的地為同源，Next.js 需要的 inline script／style 仍允許；不採 nonce。`/api/docs`／`/api/redoc` 使用的 CDN 與 CSP 不相容，正式站台建議保持關閉。

HSTS 僅在前置代理傳入 `X-Forwarded-Proto: https` 時送出，HTTP 不送出；前置代理必須覆寫用戶傳入的該 header，且後端入口應限制只允許可信代理。nginx 向 API 仍轉送自身 `$scheme`，如需 API 感知外部 HTTPS，須另外依可信代理拓樸調整。

## Image、健康檢查與日誌

API image 依 `uv.lock` 以 `uv sync --frozen --no-dev` 多階段建置；runtime 不含 uv 與編譯工具，以 uid 10001 執行 migration／uvicorn，包含 scripts、Alembic 與內附字型。`/app/media` 預先建立並賦予寫入權限；若使用既有或 bind mount 的 media，需自行確認 uid 10001 可寫。Web runner 使用 `node` 使用者。

`GET /api/health` 為不碰 DB 的 liveness；`GET /api/health/ready` 執行 `SELECT 1`，成功回 200 `{"status":"ready"}`，失敗回 503 `{"status":"unavailable"}`。Compose API healthcheck 使用 Python 標準函式庫，Web 與 nginx 等待 API healthy。

API 日誌寫至 stderr；JSON 包含 `ts`、`level`、`logger`、`msg`、`request_id`，例外加 `exc`。純 ASGI middleware 為每個請求附加 `X-Request-ID`；合法的傳入值（`[A-Za-z0-9._-]{1,64}`）會沿用，其餘重新產生。Access log 另含 `method`、`path`、`status`、`duration_ms`；不記 query string、body、Authorization 或 cookie，`/api/health*` 不記 access log。uvicorn access log 已關閉，nginx 自身的 access log 設定維持既有行為；營運時亦需管理 nginx 日誌的存取權限與保存期限。

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

請檢查 job 的回應與設定頁的執行狀態；詳細 cron、時區與補跑語義見[排程文件](docs/scheduling.md)。Compose 已移除未使用的 worker 與 Redis。

## 驗證與資料保存

- 透過站台註冊／登入並完成物品操作，確認 API 與圖片讀寫；開發環境 API 規格為 `/api/docs`，schema 為 `/api/openapi.json`；非 dev 預設關閉（含 `/api/redoc`）。離線匯出 `app.openapi()` 不受開關影響。
- 以 `make logs` 檢查服務日誌；`make down` 停止服務並保留 volumes。
- `pgdata` 保存資料庫、`media` 保存圖片。備份需涵蓋資料庫與圖片；不要使用 `docker compose down -v`，除非確定要刪除資料。

## Release images

`release.yml` 在 `v*.*.*` tag 推送時建置並推送 `ghcr.io/<owner>/<repo>-api` 與 `ghcr.io/<owner>/<repo>-web`，各自產生 SBOM artifact。Image tags 包含完整版本與 `major.minor`；只有不含 `-` 的正式版加上 `latest`。預發佈版的 GitHub Release 標為 prerelease。

現有 Compose 使用本機 `build`，不會自動改用 GHCR image；上方部署流程仍從原始碼建置。v1 歷史快照請查 `v1-final` tag。

## 升級注意（Phase 46）

- **API 改以非 root（uid 10001）執行**。Compose 的一次性 `media-init` 服務會在每次啟動時把 `media` volume 的擁有者修正為 10001，舊版建立的 volume 不需手動處理。若改用 bind mount 或其他編排工具，請自行確保 `/app/media` 對 uid 10001 可寫。
- **來源 IP**：nginx 以實際連線位址覆寫 `X-Forwarded-For`。若 nginx 前方還有反向代理（例如負責 TLS），請依 `nginx/default.conf` 內的說明加上 `set_real_ip_from`／`real_ip_header`，否則登入節流看到的會是該代理的位址。
- **Redis 已移除**（程式從未使用）；舊的 `redisdata` volume 可自行刪除。
