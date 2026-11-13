# 進度整理（2026-11-14，續）

本輪整理 **Phase 45：v1 下線與發佈管線**、同日 CI 修正，並實作 **Phase 46：部署強化與可觀測**。前次 Phase 44 記錄見 [進度文件](progress-2026-11-14.md)。

---

## 一、目前狀態

- 工作目錄為 `Item-Manage-System`、分支 `main`；本輪只寫工作樹，沒有 commit、push、tag、分支或 Git index 操作。
- Phase 45 實作結果以[計畫](plans/2026-11-14-phase45-v1-sunset-release.md)為準；既有 `v1-final` 保存 v1 快照，現行工作樹使用 v2。
- Phase 46 實作完成；[計畫](plans/2026-11-14-phase46-deploy-hardening-observability.md)狀態維持 🚧 進行中，部署與 CI 實際驗證尚待完成。
- Migration 維持 `0028 (head)`，本輪不新增或修改 migration；依賴清單／uv.lock 為使用者已同步的前置，本輪未重做。

---

## 二、完成清單（Phase 45＋46）

| 主題 | 內容 |
|------|------|
| Phase 45 v1 下線 | 移除 v1 程式、模板、靜態檔、測試、migration、腳本與純 v1 文件；Makefile／pre-commit／文件改為 v2 |
| Phase 45 Release | API／Web multi-platform images、GHCR、各 image SBOM；預發佈版不更新 latest；gh release 建立自動說明 |
| 同日 Web CI 修正 | ESLint 補 next/core-web-vitals＋next/typescript；zod 4.6.7、Playwright 1.65.0、postcss 8.5.32、react-hook-form 7.92.0、resolvers 5.9.2 與 overrides；Node 22 labels.test.ts 修正 |
| 同日 API CI 修正 | FastAPI 0.162.6／Starlette 1.x、python-multipart 0.0.31、Pydantic 2.12.5、httpx 0.28.1、fastapi-mail 1.6.8、pytest 9.0.3、pytest-asyncio 1.5.0 與傳遞依賴下限；uv.lock 稽核與 Dependabot uv 生態系 |
| Phase 46 images | API uv.lock 多階段建置、uid 10001、可寫 media、runtime 含 Alembic／scripts／字型，無編譯工具；API .dockerignore；Web node 使用者 |
| Compose | 移除 Redis／worker／redisdata；DB readiness healthcheck，Web／nginx 等待 healthy；保留單行 uvicorn proxy flags，關閉 uvicorn access log |
| API 可觀測 | readiness SELECT 1；標準 logging JSON／text、INFO 預設、冪等設定；純 ASGI request id 與 access log，contextvars 串接，不緩衝串流 |
| 瀏覽器與文件頁 | nginx CSP／Permissions-Policy／HTTPS header 才回 HSTS，保留既有安全標頭；非 dev 預設關閉 docs／redoc／schema 路由，API_DOCS_ENABLED 可覆寫 |
| API 清理 | 移除 redis_url、修正 F401／F841 並保留副作用／斷言；UTC aware 時間來源，備份輸出仍維持 Z 字尾 |
| CI | API 加 ruff／golden eval／migration up-down-up；e2e job 跑 chromium＋ai-stub，失敗上傳 test-results／Compose logs |
| 工具與文件 | make lint 加 ruff；忽略 tsbuildinfo；更新部署／架構／開發／README／FEATURES／roadmap／CHANGELOG |

---

## 三、驗證基線與本輪結果

| 項目 | 結果與範圍 |
|------|------------|
| API pytest | **1440 passed**；本輪使用既有 `.venv/bin/python -m pytest -q -p no:cacheprovider` |
| golden eval | **28 passed／1 skipped**；本輪使用既有 `.venv/bin/python -m pytest evals/ -q -p no:cacheprovider` |
| ruff | 零違規（`All checks passed!`）；本輪 `.venv/bin/ruff check .`，F＋E9 |
| 新增 API 測試 | 15 個（`tests/test_observability.py`）；readiness、request id、access log 隱私、JSON、文件頁開關與 production schema 匯出 |
| OpenAPI 匯出 | 本輪以 production＋明確 JWT_SECRET 執行 scripts/export_openapi.py，確認 JSON 可輸出，文件端點開關不影響匯出 |
| YAML／shell／差異 | 本輪解析 CI／Compose YAML、檢查 workflow shell 語法與 git diff；既有 web／audit／docker jobs 保持內容不變 |
| Web | vitest 805 passed（135 檔；Node 22 與 24 皆通過）、typecheck 0 error、lint 0 error／30 warning、`next build` 成功 |
| E2E（新 image＋CSP） | chromium **91 passed／1 skipped**、ai-stub **4 passed**（`--workers=1`） |
| Image／compose 實測 | 兩個 image 可建置；API uid 10001、Web `node`；healthcheck 轉 healthy；非 root 執行 `alembic upgrade head`；`media-init` 修正舊 volume 後可寫 |
| nginx 實測 | `nginx -t` 通過；CSP／Permissions-Policy 送出；HSTS 僅在 `X-Forwarded-Proto: https` 時出現；request id 沿用合法值、拒絕不合法值；access log 不含 query string |
| 來源 IP 偽造 | 12 個不同的偽造 `X-Forwarded-For` 連續登入失敗 → 第 11 次起 `429`（修正前可繞過 IP 節流） |
| 依賴稽核 | `pip-audit` 對 `uv.lock` 歸零；`pnpm audit --prod` 剩 `next-intl` 的 2 個 moderate（不擋 gate） |

---

## 四、設計決策摘要與差異

- D1–D15 照計畫實作；未引入額外日誌依賴、未使用 BaseHTTPMiddleware。
- 依使用者指示保留已準備的依賴清單與 uv.lock，沒有重新 lock 或變更套件版本；OpenAPI 匯出另處理讀取端提早關閉 pipe 的 BrokenPipe，避免指定 head 檢查產生 traceback。
- D12 決定保留 access token 於 localStorage；不再列為候選。CSP 仍允許 Next.js 所需 inline script／style，沒有採 nonce。
- `*.tsbuildinfo` 僅加忽略規則，已追蹤檔留待使用者移除索引；工作開始前該檔已有變更，本輪保留。
- 實作（codex）階段無網路且不能使用 Docker；live stack／image／nginx／e2e 的驗證由主代理事後補做，結果見上表。審查時另補兩項：compose 的 `media-init`（舊 volume 擁有者）與 nginx 的 `X-Forwarded-For` 覆寫（來源 IP 偽造）。

---

## 五、未驗證與已知限制

- **GitHub Actions 已確認：`main` 上 `api`（含 ruff／golden eval／migration 升降版）、`web`、`audit`、`docker`、`e2e` 五個 job 全數通過（run 43481596981）**；這是 Phase 22 之後 CI 第一次在 `main` 全綠。
- **Release／GHCR／SBOM 未驗證**：未實際打 `v*.*.*` tag；只做過 workflow 的靜態檢查與版本邏輯 dry-run。
- **前置 TLS 代理的拓樸未驗證**：HSTS 與 `set_real_ip_from` 的說明依設計撰寫，未在真實的雙層代理環境測過。
- **CSP 下未以真實相機掃碼**：e2e 走的是掃碼頁的手動輸入與圖片路徑；`Permissions-Policy: camera=(self)` 與 CSP 對實機相機的影響未實測。
- **`next-intl` 2 個 moderate advisory** 需跨 major（3 → 4）才有修補；Web lint 的 30 個 warning 保留。
- **Dependabot 啟用後開了 20 多個升級 PR**，其中多數已被本輪的手動升級涵蓋，需人工關閉或等它自行重整。
- API 測試剩餘的 warning 為既有 httpx per-request cookies 棄用警告，並非 datetime.utcnow。
- API 日誌只記必要請求欄位；nginx 自身 access log 維持既有行為，營運時須另管理其存取權限與保存期限。

---

## 六、後續候選（未排程）

功能候選維持 [roadmap](v2-roadmap.md)：收據人工核對、批次成本、分享唯讀連結、樓層平面圖互動、Background Sync、AuthImage blob 快取。Phase 46 的部署驗證是現有工作的未完成驗證，未新增為產品功能候選。

---

## 七、快速重啟與驗證指令

```bash
cd /Users/guantou/Desktop/Item-Manage-System
# 具備 Docker 與網路的環境再執行
make up
docker compose ps
curl -fsS http://localhost/api/health/ready

cd apps/api
.venv/bin/ruff check .
.venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/python -m pytest evals/ -q -p no:cacheprovider
```
