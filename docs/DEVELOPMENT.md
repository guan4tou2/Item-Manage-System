# 開發指南（v2）

## 環境與依賴

使用 Python 3.13、uv、Node.js 22、pnpm 9.12.0；整合環境使用 Docker Compose。Python 與 workspace 依賴分別以 `apps/api/uv.lock` 與根目錄 `pnpm-lock.yaml` 為準。

在 repo 根目錄執行：

```bash
make install
cp .env.example .env
# 編輯 .env：資料庫密碼、JWT_SECRET 與所需整合設定
make up
# http://localhost/；API 規格：http://localhost/api/docs
```

`make up` 會先匯出 OpenAPI、產生 api-types，再建置並啟動 Compose。API 容器啟動時自動遷移至 head（目前 `0028`）。首次使用到 `/signup` 註冊，首位使用者可於設定頁啟用管理員。停止服務用 `make down`，日誌用 `make logs`。

## 本機 API 與 Web

本機開發需另外提供可連線的 PostgreSQL 16；Compose 的資料庫沒有對主機發佈 port，不能直接把 `.env.example` 的 `postgres` hostname 當成本機連線。以下假設本機資料庫已建立，請換成實際帳密。

```bash
# 終端一：repo 根目錄
export DATABASE_URL='postgresql+asyncpg://ims:your-password@localhost:5432/ims'
export JWT_SECRET='replace-with-a-random-secret-at-least-32-bytes'
export ENVIRONMENT=dev
export MEDIA_DIR="$PWD/media"
export CORS_ORIGINS='["http://localhost:3000"]'
make migrate
cd apps/api
.venv/bin/uvicorn app.main:app --reload --port 8000 --no-access-log
```

API 的 Settings 讀取執行目錄下的 `.env`，不會自動載入 repo 根目錄的 `.env`；上述 shell 環境變數可直接傳給 API。其他整合設定以 `apps/api/app/config.py` 為準。

```bash
# 終端二：repo 根目錄
make gen-types
NEXT_PUBLIC_API_BASE=http://localhost:8000/api make dev
# http://localhost:3000/
```

`make dev` 啟動 Web；API 需在另一個終端執行。API 文件在 `http://localhost:8000/api/docs`。

## Schema 與型別同步

API schema 異動後，在 repo 根目錄執行 `make gen-types`。此指令使用 `apps/api/.venv/bin/python` 匯出 OpenAPI，再執行 `pnpm --filter @ims/api-types gen:types`。資料庫異動需在 `apps/api/alembic/versions/` 新增 migration，並驗證升降版；`make migrate` 對目前 `DATABASE_URL` 執行 `alembic upgrade head`。

## 驗證入口

```bash
make test-api
make test-web
make typecheck
make lint
pnpm --filter @ims/web build
make e2e
make audit
```

- `make test` 串接 API 與 Web 單元測試。API 測試使用每個 test 獨立的 in-memory SQLite，不需正式資料庫。
- 既有基線：API **1524 passed**；Web **926 passed（148 檔）**；Playwright e2e：Phase 47 為 **31 spec／99 情境**（含 ai-stub；1 個位置樹情境依賴舊 fixture 而 skip），Phase 48–50 新增的情境由 CI 執行。這些數字是既有基線，不代表每次執行的結果。
- e2e 需要已啟動的完整服務與 Playwright 瀏覽器；預設網址為 `http://localhost`，可透過 `E2E_BASE_URL` 覆寫。AI 成功情境另需 dev API 使用 `AI_MODE=stub`，再執行 `E2E_AI_STUB=1 pnpm --filter @ims/web test:e2e --project=ai-stub`。
- `make audit` 會稽核 Python lockfile 與 Node 正式依賴，需要網路；`make lint` 同時執行 API ruff（F＋E9）與 Web ESLint。
- pre-commit 僅保留空白、檔尾、YAML／JSON／TOML、merge conflict、大檔案與換行格式檢查。

完整 targets 見 `make help`。架構見[系統架構](ARCHITECTURE.md)，排程見[排程與到期提醒](scheduling.md)。

## 部署設定與 CI

Compose 已移除 Redis／worker，API runtime 以非 root 執行，Web 與 nginx 等待 `/api/health/ready` 的 DB 探針通過；`/api/health` 保留純 liveness。API 文件頁與 schema 路由僅在 dev 預設開啟，可用 `API_DOCS_ENABLED=true|false` 覆寫；`make gen-types` 直接匯出 schema，不受關閉影響。

`LOG_FORMAT` 留空時 dev 用 text、非 dev 用 JSON，`LOG_LEVEL` 預設 INFO。請求以 `X-Request-ID` 串接日誌；只接受 `[A-Za-z0-9._-]{1,64}`，不合格重新產生。Access log 不記 query string、body、認證 header 或 cookie，並略過 health 探針。nginx 的 CSP 限制同源外送，Permissions-Policy 允許同源相機；HSTS 僅在前置代理帶入 HTTPS header 時回傳，詳見[部署指南](../Deployment_Guide_zh-TW.md)。

API CI 以 `uv sync --frozen --extra test` 安裝，執行 ruff、pytest、`pytest evals/ -q`，並用 `DATABASE_URL` 指向 job 的 PostgreSQL，跑 `upgrade head → downgrade -1 → upgrade head`。新增 e2e job 在完整 Compose 跑 chromium（單 worker），再以 `AI_MODE=stub` 重啟 API、`E2E_AI_STUB=1` 跑 ai-stub；失敗保存 test-results 與 compose logs。這些部署流程本輪尚未實跑，不能以 YAML 靜態檢查代替驗證。
