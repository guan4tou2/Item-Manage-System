# Phase 45：v1 下線與發佈管線

- **狀態**：✅ 完成
- **日期**：2026-11-14
- **基線**：`main` `beca48f`（Phase 44）；API 1425 passed、Web 805 passed（135 檔）、e2e 30 spec／96 情境、Migration `0028 (head)`
- **來源**：2026-11-14 專案分析 P1（release 管線會發佈 v1）與 P2（v1 殘留、文件失真）

---

## 目標

讓 repo 只剩 v2，且「打 tag」會發佈正確的東西：

1. **保留 v1 快照**：annotated tag `v1-final` 指向 `beca48f`（最後一個含 v1 的 commit）。
2. **移除 v1 程式與工具鏈**：Flask 應用、模板、靜態檔、v1 測試與 migration、v1 的執行／部署腳本。
3. **Release 管線改發 v2**：`v*.*.*` tag → 建置並推送 `apps/api` 與 `apps/web` 兩個 image。
4. **開發工具對齊 v2**：Makefile、pre-commit 不再指向 pipenv／Flask／`app/`。
5. **文件只描述現況**：刪除純 v1 文件，改寫混雜的文件，修正 README 的過時數字。

---

## 設計決策

- **D1 tag 而非分支**：`v1-final` 為 annotated tag；`release.yml` 只匹配 `v*.*.*`，不會被此 tag 觸發。
- **D2 移除清單（整個目錄）**：`app/`、`templates/`、`static/`、`tests/`（根目錄，v1 測試）、`migrations/`、`translations/`、`scripts/`、`.devcontainer/`（指向 Flask／Mongo）、`skills/`（v1 時期的操作文件，確認內容後處理）。
- **D3 移除清單（根目錄檔案）**：`app.py`、`run.py`、`run_worker.py`、`run_tests.py`、`run_tests.sh`、`run_tests_uv.sh`、`start.sh`、`verify_test_setup.sh`、`verification_output.txt`、`test_login.py`、`test_notifications.py`、`test_system.py`、`requirements.txt`、`pyproject.toml`（v1；v2 的在 `apps/api/`）、`pytest.ini`、`alembic.ini`（v1；v2 的在 `apps/api/`）、`babel.cfg`、`uv.lock`（v1）、`Dockerfile`、`Dockerfile.test`、`docker-compose.dev.yml`、`docker-compose.test.yml`、`package-lock.json`（npm 殘留；本專案用 pnpm）、`.test-files-checklist.md`。
- **D4 不動的東西**：`.agent/`、`.agents/`、`.continue/`、`.claude/`（各代理工具的 skills，屬使用者工具設定）、`skills-lock.json`、`mitm_mcp_traffic.db`（未追蹤的本機檔）、`docker-compose.yml` 的 `worker` 死設定（Phase 46 一併清）。
- **D5 Release 管線**：
  - 觸發：`v*.*.*` tag。
  - 兩個 image：`ghcr.io/<owner>/<repo>-api`（context `apps/api`）與 `ghcr.io/<owner>/<repo>-web`（context repo 根目錄、`apps/web/Dockerfile`；建置前需先匯出 OpenAPI 並產生 api-types，做法比照 `ci.yml` 的 `docker` job）。
  - tag 規則：semver 完整版＋`major.minor`；**含 `-` 的預發佈版（如 `v2.0.0-alpha.45`）不打 `latest`**，GitHub Release 標為 prerelease。
  - GitHub Release 用 `gh release create --generate-notes`（`actions/create-release@v1` 已封存）。
  - 移除 PyPI 發佈 job 與空的 notify job。SBOM 保留（兩個 image 各一份）。
- **D6 Makefile**：重寫為 v2 入口（`install`、`dev`、`up`／`down`／`logs`、`migrate`、`gen-types`、`test`／`test-api`／`test-web`、`typecheck`、`lint`、`e2e`、`audit`），每個 target 有 `##` 說明並保留 `help`。
- **D7 pre-commit**：只留與語言無關的 `pre-commit-hooks`（trailing-whitespace 等）；移除 black／isort／flake8／bandit（指向 `app/`、Python 3.12）與 `pipenv run pytest`。Python lint 待 Phase 46 引入 ruff 時再加。
- **D8 文件**：
  - **刪除**（純 v1）：`DOCKER_POSTGRES_GUIDE.md`、`GUIDE_ZH-TW.md`、`QUICK_START.md`、`SETUP.md`、`TESTING.md`、`TESTING_QUICK_START.md`、`TEST_SETUP_SUMMARY.md`、`UNIT_TEST_COMPLETE.md`、`MCP_SKILLS_SETUP.md`、`docs/API.md`（v1 端點；v2 以 `/api/docs` 的 OpenAPI 為準）。
  - **改寫為 v2**：`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT.md`（依實際程式碼精簡重寫，不沿用 v1 內容）、`Deployment_Guide_zh-TW.md`（compose 部署、必要環境變數、外部 cron、`WEBHOOK_ALLOW_PRIVATE_HOSTS`、TLS 由前置反向代理處理的說明）、`DOCS_INDEX.md`（短索引）。
  - **修正**：`README.md`／`README_EN.md`（測試數字、移除「v1 保留於 `app/`」敘述、專案結構圖、指向已刪文件的連結）；`CHANGELOG.md` 開頭的 v1 說明改指向 `v1-final` tag；`docs/v2-roadmap.md`「與 v1 的關係」。
  - 其餘文件只修斷掉的連結。
- **D9 `.dockerignore`／`.gitignore`**：移除只對 v1 有意義的項目（`mongo_data`、`static/uploads` 等），不動 v2 需要的規則。

---

## 明確不在本期範圍

- `docker-compose.yml` 死設定、未使用依賴、非 root image、TLS／CSP、CI 補強（→ Phase 46）
- 版本號從 `2.0.0-alpha` 升級或實際打 release tag
- 各代理工具 skills 目錄的去重

---

## 驗證

- `git grep` 不再有指向已刪路徑的引用（文件歷史敘述如 CHANGELOG 舊條目除外）
- 文件內的相對連結全部可解析
- API／Web 測試數字不變（1425／805）；`pnpm typecheck`、`pnpm lint`、`next build` 通過
- `docker compose config` 通過；`apps/api` 與 `apps/web` 兩個 image 可建置
- workflow YAML 可解析；`release.yml` 的 tag 邏輯以 dry-run 腳本驗證（不實際打 tag）

## 實作結果（完成後填寫）

### 移除範圍

共移除 **9 個目錄中的 232 個追蹤檔案**，另移除 **24 個根目錄程式／工具檔案**與 **10 份純 v1 文件**，合計 **266 個追蹤檔案**。9 個目錄皆已從工作樹移除。

| 目錄 | 移除檔案數 |
|------|------------|
| `app/` | 105 |
| `templates/` | 56 |
| `static/` | 17 |
| 根目錄 `tests/` | 17 |
| `migrations/` | 12 |
| `translations/` | 5 |
| `scripts/` | 8 |
| `.devcontainer/` | 1 |
| `skills/` | 11 |
| **目錄內合計** | **232** |

根目錄 24 個檔案與純 v1 文件 10 份均依 D3、D8 清單移除，沒有擴充刪除清單。`skills/` 經內容確認，README 與操作文件仍以 Flask、MongoDB、舊靜態資源為背景，因此依 D2 全數移除；`skills-lock.json` 保留。

### 改寫與修正摘要

| 檔案 | 實作摘要 |
|------|----------|
| `.github/workflows/release.yml` | 以 API／Web matrix 建置並推送兩個 multi-platform images；Web 的 OpenAPI 匯出與 api-types 產生步驟逐項比對 CI 的 docker job；完整版本與 major.minor tags，預發佈版不含 latest；兩個 image 各以 digest 產生 SBOM artifact；images 成功後以 gh 建立自動說明的 Release，預發佈版加上 prerelease；移除 PyPI 與 notify jobs。 |
| `Makefile` | 改為 v2 的 install、Web dev、Compose、migration、型別產生、測試、typecheck、lint、e2e 與 audit 入口；16 個 targets 全有說明，up 先產生型別再建置。 |
| `.pre-commit-config.yaml` | 僅保留語言無關的 pre-commit-hooks；移除 Python 專屬 hooks（含 debug-statements）與舊 pytest hook。 |
| `.dockerignore` | 僅移除 mongo_data 規則。 |
| `.gitignore` | 僅移除 mongo_data 與 static/uploads 專屬規則。 |
| `docs/ARCHITECTURE.md` | 依實際 monorepo、nginx、API Settings 與 Compose 重寫元件責任、資料流、認證、型別同步與外部排程。 |
| `docs/DEVELOPMENT.md` | 重寫 lockfile 安裝、本機 API／Web 環境、型別同步、migration 與驗證入口，明示根目錄 .env 不會自動套用至本機 API。 |
| `Deployment_Guide_zh-TW.md` | 重寫 Compose 建置、必要設定、選用通知整合、前置 TLS proxy、外部 cron、資料保存與 release images；明示目前 Compose 仍從原始碼建置。 |
| `DOCS_INDEX.md` | 收斂為現有文件短索引，API 規格改指向執行中的 OpenAPI 與 repo 匯出檔。 |
| `README.md` | 更新 v1 下線說明、實際 FastAPI 版本、Node.js 需求、Compose 啟動步驟、結構圖、API 文件網址、migration 0028 與測試基線，移除已刪 API 文件連結。 |
| `README_EN.md` | 同步修正下線狀態、啟動方式、版本／結構／API 網址與測試基線；本次新增說明採臺灣繁體中文。 |
| `CHANGELOG.md` | 僅修正開頭的 v1 說明，改指向 v1-final tag；歷史條目未變更。 |
| `docs/v2-roadmap.md` | 僅修正「與 v1 的關係」，說明已下線、tag 快照與 v2 維護／資料匯入入口。 |
| 本計畫文件 | 填寫移除數量、實作摘要、差異、驗證與未驗證事項；狀態維持 🚧 進行中。 |

User Manual、FEATURES、DESIGN、AI、排程與驗收文件經相對連結檢查，沒有因本次刪檔產生斷鏈，因此未修改。其他 plans、progress 與 superpowers 歷史紀錄未修改。

### 與計畫的差異

- 已嘗試 `git rm -r`，但沙箱禁止建立 `.git/index.lock`（Operation not permitted）。因此以相同清單刪除工作樹檔案，266 個刪除均為未暫存狀態；未修改 Git index。
- D1 的既有 tag 不再處理；沒有 commit、push、tag 或分支操作。
- 未執行需要安裝套件、網路、寫入禁止路徑或啟動／重建完整服務的驗證；本次以離線靜態檢查與 workflow shell dry-run 驗證。既有測試數字只作基線，沒有宣稱本次重跑通過。

### 已執行的驗證

- `git status --short` 與刪除清單核對：266 個追蹤刪除，9 個目錄均不存在；本次變更皆在授權範圍。
- 對禁止路徑（含起始時他人已修改的檔案）與 skills-lock.json 記錄 SHA-256 快照，再比對檔案內容：無差異。
- 執行指定 `git grep -nE`（排除歷史文件）：剩餘 13 列為有效的 v2 item-templates 路由／型別／測試、既有 TypeScript cache，以及 roadmap 先前的 Phase 45 規劃敘述；沒有待修正的已刪檔案引用。
- 本次改寫／修正 Markdown 的 55 個相對檔案連結均存在；CHANGELOG 僅檢查修改的開頭，歷史條目依指示保留。本計畫新增內容無相對檔案連結。
- 其他現行根目錄／docs Markdown 的相對檔案連結亦檢查通過（歷史文件與代理工具設定除外）。
- 使用既有 API 虛擬環境的 PyYAML 解析 release.yml 與 pre-commit 設定，兩者皆為合法 YAML；無安裝套件。
- 程式比對 release 與 CI docker job 的 OpenAPI／api-types `run`、working-directory：完全一致；未修改 CI。
- 對 workflow 所有 run 區塊執行 `bash -n`；正式版 v2.0.0／v10.12.3 與預發佈版 v2.0.0-alpha.45／v10.12.3-rc.1，各測試 API／Web tags、latest 與 gh prerelease 參數；以 mock gh 執行 dry-run，全數通過。非版本 tag 的防呆亦通過，沒有實際推送或建立 Release。
- `make help` 正常列出全部 16 個 targets；相關 targets 的 `make -n` 檢查通過。
- `docker compose config --quiet` 通過。
- `git diff --check` 通過。

### 未驗證與限制

- 本次未重跑 API／Web 單元測試、e2e、pnpm typecheck／lint 或 next build，未重新執行 migration；1425／805（135 檔）、30 spec／96 情境與 0028 為既有基線。
- 未建置 Docker images、推送 GHCR、實跑 GitHub Actions／SBOM 產生或建立 GitHub Release；需要正式 CI 執行確認外部 actions、registry 權限與 multi-platform 建置。Next.js 使用 next/font/google，完整建置也可能需要網路。
- 未實際執行 make install／up／audit、Compose 啟動、登入／物品操作、TLS 或 cron 通知流程；文件已依現有程式與設定核對，端到端行為仍待部署環境驗證。
- Compose worker 死設定、TLS／proxy headers 強化及其他 D4／Phase 46 項目維持原狀；預發佈版依 D5 仍會更新 major.minor image tag，但不會更新 latest。
