# Phase 46：部署強化與可觀測

- **狀態**：🚧 進行中
- **日期**：2026-11-14
- **基線**：Phase 45 完成後的 `main`；API 測試 1425、Web 805（135 檔）、e2e 30 spec／96 情境、Migration `0028 (head)`
- **來源**：2026-11-14 專案分析 P1（部署設定鬆散、CI 缺口）與 P2（無可觀測性）

---

## 目標

不加使用者功能，讓「跑在正式環境」這件事站得住：

1. **Image 可重現且最小權限**：依 `uv.lock` 安裝、非 root 執行、final image 不含編譯工具。
2. **服務狀態看得到**：readiness 端點、容器 healthcheck、結構化日誌與 request id。
3. **瀏覽器端基本防線**：CSP、HSTS（TLS 下）、Permissions-Policy；正式環境關閉 API 文件頁。
4. **CI 涵蓋實際會壞的東西**：lint、golden eval、migration up/down、e2e。
5. **清掉死設定與未使用依賴**。

---

## 設計決策

### Image 與 compose

- **D1 API image 多階段**：builder 階段用 `uv sync --frozen --no-dev` 依 `uv.lock` 建 venv；runtime 階段只複製 venv 與程式，建立非 root 使用者（固定 uid 10001）執行；移除 `build-essential`（依賴皆有 wheel；若建置證明需要才留在 builder）。`/app/media` 需可寫（volume 掛載點在 image 內先建立並 chown）。
- **D2 Web image 非 root**：runner 階段改用內建的 `node` 使用者。
- **D3 compose 清理**：移除指向不存在模組的 `worker` 服務；移除未使用的 `redis` 服務、`redisdata` volume 與 `REDIS_URL`。`api` 加 healthcheck（打 readiness），`web`／`nginx` 以 `service_healthy` 等待。
- **D4 未使用依賴**：`pyproject.toml` 移除 `slowapi`、`redis`、`structlog`（程式碼零引用；登入節流已於 Phase 43 以資料表實作）；`config.py` 移除 `redis_url`。

### 可觀測

- **D5 健康檢查分兩種**：`GET /api/health` 維持 liveness（不碰 DB，契約不變）；新增 `GET /api/health/ready`——對 DB 執行 `SELECT 1`，成功 `200 {"status":"ready"}`，失敗 `503 {"status":"unavailable"}`（不回傳例外內容）。
- **D6 結構化日誌用標準函式庫**：不引入日誌套件。`LOG_FORMAT=json|text`（預設 `json`；`ENVIRONMENT=dev` 預設 `text`）、`LOG_LEVEL`（預設 `INFO`）。JSON 欄位：`ts`、`level`、`logger`、`msg`、`request_id`，例外時加 `exc`。
- **D7 Request id 與 access log**：純 ASGI middleware（不用 `BaseHTTPMiddleware`，避免影響串流回應）。沿用傳入的 `X-Request-ID`（限 `[A-Za-z0-9._-]{1,64}`，不合格就重新產生）；以 `contextvars` 帶進該請求的所有 log；回應加 `X-Request-ID`。每個請求一行 access log：`method`、`path`（不含 query string，避免 token／搜尋字串入 log）、`status`、`duration_ms`。`/api/health*` 不記 access log。uvicorn 自己的 access log 關閉（`--no-access-log`），避免重複。
- **D8 不記敏感資料**：不記 request／response body、`Authorization`、cookie、query string。

### 瀏覽器端防線

- **D9 CSP 由 nginx 統一加**：
  `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'`
  - Next.js App Router 需要 inline script，嚴格的 nonce 式 CSP 會讓全站改為動態渲染；本期先不做。
  - 這份 CSP 的實際價值在 **`connect-src`／`img-src`／`form-action` 限制外送**：即使發生 XSS，也無法把 token 傳到第三方主機。
  - `/api/docs`、`/api/redoc` 會載入 CDN 資源，與此 CSP 衝突——見 D11（正式環境本來就關閉）。
- **D10 其他標頭**：`Strict-Transport-Security` 僅在 `X-Forwarded-Proto: https` 時送出（TLS 由前置反向代理終結；見部署文件）；`Permissions-Policy: camera=(self), microphone=(), geolocation=()`（掃碼需要相機）。既有的 `X-Frame-Options`、`X-Content-Type-Options`、`Referrer-Policy` 保留。
- **D11 正式環境關閉 API 文件頁**：`ENVIRONMENT != dev` 時 `docs_url`／`redoc_url`／`openapi_url` 設為 `None`；`API_DOCS_ENABLED=true` 可強制開啟。`scripts/export_openapi.py` 直接呼叫 `app.openapi()`，不受影響（需確認並以測試固定）。
- **D12 access token 留在 `localStorage`（決定不搬）**：refresh token 是 httpOnly cookie，頁面內的 XSS 不論 access token 放哪裡都能直接呼叫 `/api/auth/refresh` 取得新 token；把 access token 改成只放記憶體並不能擋住頁面內的 XSS，卻要改寫整個啟動流程與 e2e。有效的緩解是 D9 的外送限制與既有的 15 分鐘效期。此項自候選清單移除。

### CI

- **D13 `api` job**：加 `ruff check`（先只開 `F`＋`E9`：未使用 import／變數、語法錯誤；不開風格規則，避免一次性大改）；加 `pytest evals/ -q`；加 migration 檢查——對 job 內的 PostgreSQL 執行 `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`。
- **D14 新增 `e2e` job**（`needs: [api, web]`）：以 `.env.example` 產生 `.env`（設 `ENABLE_DEV_ROUTES=1`、隨機 `JWT_SECRET`）→ 匯出 OpenAPI 與 api-types → `docker compose up -d --build` → 等 readiness → 安裝 Playwright Chromium → `chromium` 專案（`--workers=1`）→ 以 `AI_MODE=stub` 重啟 api 後跑 `ai-stub` 專案；失敗時上傳 trace 與 compose logs。
- **D15 `datetime.utcnow()`**：全部改為 timezone-aware 的 `datetime.now(timezone.utc)`（輸出格式維持不變），消除測試中的棄用警告。

---

## 明確不在本期範圍

- nonce 式嚴格 CSP、access token 移出 `localStorage`（見 D9、D12）
- TLS 憑證管理（由前置反向代理／平台處理；部署文件說明）
- metrics（Prometheus）／tracing（OpenTelemetry）／錯誤追蹤服務
- `next lint` → ESLint CLI 遷移、清理 30 個 lint 警告、Next 16 升級
- `next-intl` 4.x 升級（2 個 moderate advisory）

---

## 驗證

- API：`pytest -q`、`pytest evals/ -q`、`ruff check`；新增 readiness／request id／日誌格式／文件頁開關的測試
- Migration：PostgreSQL 容器 `upgrade head → downgrade -1 → upgrade head`
- Image：兩個 image 可建置；`docker compose up` 後容器內 `id -u` 非 0、healthcheck 轉為 healthy、上傳圖片可寫入 media volume
- 標頭：`curl -I` 檢查 CSP／Permissions-Policy；帶 `X-Forwarded-Proto: https` 時才有 HSTS
- e2e：live stack `chromium`＋`ai-stub` 全跑（CSP 下相機掃碼頁、圖片、PWA 註冊不得壞）
- CI：push 後確認 `api`／`web`／`audit`／`docker`／`e2e` 的實際結果

## 實作結果

（完成後填寫）
