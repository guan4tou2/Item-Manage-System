# Phase 24 — 排程自動化＋到期提醒 Implementation Plan

> 對應 `docs/plans/2026-10-15-next-iteration-roadmap.md` §六 Phase 24（L325–371）＋ §5.1 行動卡（24 遵循）、§5.2 設定 IA（通知與提醒群組新增頁）、§5.4 狀態契約。
> 執行者（Claude／Codex／任何 agent）：逐 task 執行；每 task **先寫失敗測試（RED）→ 最小實作（GREEN）→ 勾選 checklist**。
> 完成任一 task 即 commit（Conventional Commits，`feat(api): …`／`feat(web): …`／`test(web): …`）。

**Goal：** 建立可重複使用的「外部 cron ＋ 冪等 job 端點」機制（Phase 31 `report.monthly` 重用）；第一個 job＝`expiry-scan`：每日掃描批次到期（30 天前／7 天前／當天／過期後每日至 14 天），每用戶每類型每日最多一則**摘要**通知（尊重 Phase 23 偏好）；設定頁新增「提醒排程」（唯讀＋停跑警示）；儀表板到期卡疊加「今天已彙總提醒」註記；移除 `apscheduler` 遺留依賴。

**Architecture：** 外部 cron（管理員 PAT）→ `POST /api/jobs/{job_name}/run` → job registry（`expiry-scan`）→ 掃描（`clock.today_taipei()` 唯一「今天」來源）→ `expiry_alerts` 冪等寫入（UNIQUE 為最後防線）→ 摘要 `emit()`（Phase 23 偏好自動過濾）→ `job_runs` 記錄（設定頁顯示／停跑觀測）。失敗語義：per-user 隔離、部分成功保留、可安全重跑補差額。

**Tech Stack：** FastAPI、SQLAlchemy async、Alembic（migration `0018`）、pytest（SQLite in-memory：`tests/conftest.py` create_all）、React Query、next-intl、shadcn/ui、Vitest、Playwright。**不新增依賴**（時間注入用既有 `clock.py` 參數；移除 `apscheduler`）。

**關鍵既有資產（重用，勿重造）：**
- 外部 cron 模式：`POST /api/webhooks/process-retries`（`apps/api/app/routes/webhooks.py:84`）＋ `process_due_retries`（`services/webhook_service.py`）——job 端點語義比照
- 管理員守衛：`get_current_admin`（`app/auth/dependencies.py`，`routes/admin.py:7` 使用）；PAT 走 `get_current_user` 同一認證鏈
- `clock.py`：`today_taipei()`／`days_left()`／`EXPIRING_SOON_DAYS=7`（L1–55，全站「今天」唯一來源）
- 通知扇出：`notifications_service.emit()`（已支援 `type=` 偏好過濾，Phase 23）＋ `notification_prefs` 常數（`expiring_soon`／`expired` 已就位、預設站內＋推播）
- `JSONType`（`app/models/favorite_audit_token.py`；PG JSONB／SQLite JSON 兩用，`customization.py` 已有先例）
- 到期聚合：`stats_repository.expiry()`（`apps/api/app/repositories/stats_repository.py:410`，owner／未刪除條件比照）；`ExpiryStats`（`app/schemas/stats.py:62`）
- 儀表板到期卡：`apps/web/components/dashboard/expiry-card.tsx`（既有 deep link `/items?expiry=…&sort=expiry_asc`、`data-testid="expiry-card-note"`）
- 設定 IA：`apps/web/components/settings/settings-nav.ts`（四群組靜態表）；子頁外殼 `settings-page-shell.tsx`
- 清單 deep link：`/items?sort=expiry_asc`（`items-list-client.tsx:105` `expiryView` 判定，已存在）
- e2e 慣例：zh-TW locale、`request.post("/api/auth/register")`、bootstrap admin（`POST /api/auth/bootstrap-admin`）

**盤點定案（2026-10-16，實作前一覽）：**
1. **端點權限**：`POST /api/jobs/{job_name}/run`＝admin（匿名 401、非 admin 403、未知 job 404）；`GET /api/jobs/{job_name}/status`＝任何登入者（唯讀觀測，無 payload 外洩）。cron 範例使用管理員 PAT。
2. **級別觸發語義**（每批）：
   - `d30`：`0 ≤ days_left ≤ 30` 且該批從未發過 `d30` → 發（**補發語義**：上線初期既有批次一次補齊）；`d7`：`0 ≤ days_left ≤ 7` 同規則；`d0`：`days_left == 0` 同規則。
   - `expired`：`days_left < 0` 且 `days_left ≥ -14`（即過期 14 天內）**每日**一則；`days_left < -15`（-15 起）停止推播——物品仍留在站內列表／篩選（「站內保留」）；既有通知不刪。
   - 說明：d30/d7/d0 各為「首次跨入」一次性提醒，同日重跑不重發；同一批同日跨多級（補發情境）只計入摘要**一次**（distinct batch）。
3. **摘要規則**：每用戶每日每**類型**最多一則（非逐批轟炸）；`d30/d7/d0 → expiring_soon`、`expired → expired`；計數＝當日新 alert 的 distinct batch。文案（zh-TW，比照 `low_stock` 伺服器端慣例）：
   - `expiring_soon`：title `「N 件物品即將到期」`、body `「最急：{name}（剩 d 天／今天到期）」`、link `/items?sort=expiry_asc`
   - `expired`：title `「N 件物品已過期」`、body `「最急：{name}（已過期 d 天）」`、link `/items?expiry=expired&sort=expiry_asc`
4. **冪等**：`expiry_alerts` UNIQUE(`batch_id`,`level`,`sent_on`) 為最後防線；服務層先查（一次性查全部候選）再插；並發衝突以 savepoint 吸收視為已送出；摘要「有新 alert 才發」故天然冪等。
5. **失敗語義**：逐用戶 try/except＋`session.commit()`（部分成功保留）；錯誤收進 `job_runs.result.errors`，任何錯誤 → `status=failed`；`job_runs` 開列（`running`）即 commit、收尾再 commit。重跑依 dedupe 只補差額。
6. `run` 回傳 `{job, processed, emitted}`：`processed`＝新建 `expiry_alerts` 列數；`emitted`＝摘要 `emit()` 呼叫數（通道過濾在此層之下，屬偏好語義）。
7. **停跑判定**：`status` 端點回 `stale`：從未執行或最近一次執行開始時間逾 **26 小時** → 警示。門檻隨回應附帶（設定頁顯示用）。
8. **提醒排程頁**：`/settings/reminders`（群組「通知與提醒」第三頁，順序 channels → notifications → reminders；群組 ≤6 上限不變）——唯讀：目前門檻、上次執行（時間＋狀態）、停跑警示（含 cron 設定片段＋`docs/scheduling.md` 連結＋建立 PAT 連結）。
9. **儀表板註記**：`GET /api/stats/expiry` 新增 `reminded_today: bool`（該 owner 今天有無任何 `expiry_alerts`）；卡片角落 muted 小字＋鈴鐺 icon（不改變排序與尺寸，§5.1）。
10. **apscheduler**：`pyproject.toml` 移除（L21）＋`uv lock` 重生成；確認無程式引用。
11. **job registry 介面**（Phase 31 掛載點）：`JOBS: dict[str, JobSpec]`、`JobSpec(name, run)`；`run(session, today) -> JobResult{processed, emitted, errors}`。
12. 摘要送出即可（`emitted` 為 dispatch 數）；「全部通道關閉時跳過 emit」不實作（偏好面板語義已明確，屬未來優化）。

**執行前置：**
- worktree：`.claude/worktrees/phase24-jobs-expiry`（branch `claude/phase24-jobs-expiry`）
- alembic head＝`0017`；T1.1 後以 `docker compose cp`＋`alembic upgrade head` 對真實 PG 驗證（比照 0017）
- Phase 3（e2e）前 `docker compose up -d --build api web`；worktree `.env` 需 `ENABLE_DEV_ROUTES=1`（`/__dev/*` 展示頁為 theme spec 所需，比照 Phase 23）
- 指令：API `cd apps/api && uv run --extra test pytest -q`；Web `pnpm -F @ims/web test`／`pnpm -F @ims/web typecheck`；型別 `pnpm -F @ims/api-types gen:types`

**Execution Order**
1. API：models＋migration 0018 → repositories＋jobs_service（registry／runner）→ expiry_scan 核心（時間旅行×冪等×偏好×失敗）
2. API：routes＋schemas＋api-types → stats/expiry `reminded_today` → apscheduler 移除
3. Web：stats 型別＋卡片註記 → jobs client／hook → `/settings/reminders` 頁＋nav＋i18n
4. e2e＋文件（scheduling.md）→ CHANGELOG／roadmap／勾選

---

## Phase 1: API — Job 機制與到期掃描

### Task 1.1: `job_runs`＋`expiry_alerts` model＋migration `0018`

**Files:**
- Create: `apps/api/app/models/job_run.py`
- Create: `apps/api/app/models/expiry_alert.py`
- Modify: `apps/api/app/models/__init__.py`（註冊）
- Create: `apps/api/alembic/versions/0018_jobs_expiry_alerts.py`
- Test: `apps/api/tests/test_job_models_smoke.py`

**TODO:**
- [x] `JobRun`：`id`(UUID pk)、`job_name`(String(50), nullable=False, index)、`status`(String(20), nullable=False)、`started_at`(DateTime, nullable=False, default `_utcnow`)、`finished_at`(DateTime, nullable=True)、`result`(`JSONType`, nullable=True)
- [x] `ExpiryAlert`：`id`(UUID pk)、`batch_id`(GUID FK `item_batches.id` ondelete=CASCADE, nullable=False, index)、`level`(String(10), nullable=False)、`sent_on`(Date, nullable=False)、`created_at`(`_utcnow`)；`UniqueConstraint("batch_id","level","sent_on", name="uq_expiry_alerts_batch_level_day")`、`Index("ix_expiry_alerts_sent_on", "sent_on")`
- [x] migration 0018：`revision="0018"`、`down_revision="0017"`；upgrade＝建兩表＋unique＋index；downgrade 對稱（比照 `0017_notification_preferences.py` 風格）
- [x] smoke：建 run／alert；同 `(batch_id, level, sent_on)` 重複→unique 違反；刪 batch→cascade 清 alerts
- [x] 真實 PG 驗證：`docker compose cp`＋`alembic upgrade head`→`alembic current`＝0018

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_job_models_smoke.py`
- `cd apps/api && uv run alembic upgrade head`

### Task 1.2: repositories＋`jobs_service`（registry／runner／job_runs 記錄）

**Files:**
- Create: `apps/api/app/repositories/job_runs_repository.py`
- Create: `apps/api/app/repositories/expiry_alerts_repository.py`
- Create: `apps/api/app/services/jobs_service.py`
- Test: `apps/api/tests/test_jobs_service.py`

**TODO:**
- [x] `job_runs_repository`：`create_running(session, job_name)`（flush 後回列）、`finish(session, row, *, status, result)`（設 `finished_at`）、`latest(session, job_name)`（`started_at` desc 首筆）
- [x] `expiry_alerts_repository`：`advance_levels_for(session, batch_ids)`→`set[(batch_id, level)]`（level in d30/d7/d0，不限日期）；`expired_on(session, batch_ids, on)`→`set[batch_id]`；`create(session, *, batch_id, level, sent_on)`（`session.begin_nested()` savepoint＋`IntegrityError`→回 `None` 表已存在）
- [x] `jobs_service`：`JobSpec` dataclass、`JobResult{processed, emitted, errors}`、`JOBS: dict[str, JobSpec]`（先註冊 `expiry-scan`）、`run_job(session, name) -> JobRun`：
  - 未知 job → `UnknownJobError`（route 轉 404）
  - 開列 `running`＋commit → 執行 spec（`today=today_taipei()`）→ 任何例外→`status=failed`＋result.error；有 errors→failed → 收尾＋commit
- [x] 測試：run 成功→`succeeded`＋finished_at 有值＋result 正確；spec 抛例外→`failed`＋error 摘要；未知 job→`UnknownJobError`；`latest()` 取最近

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_jobs_service.py`

### Task 1.3: `expiry_scan` 核心（時間旅行×冪等×偏好×失敗語義）

**Files:**
- Create: `apps/api/app/services/expiry_scan.py`
- Test: `apps/api/tests/test_expiry_scan.py`

**TODO:**
- [x] 常數：`ADVANCE_LEVELS = {"d30": 30, "d7": 7, "d0": 0}`、`EXPIRED_LEVEL = "expired"`、`EXPIRED_STOP_DAYS = 14`、`STALE_AFTER_HOURS = 26`、`LEVEL_TYPE = {d30/d7/d0: "expiring_soon", expired: "expired"}`
- [x] `scan(session, *, today=None) -> JobResult`：單一候選查詢（join items，`is_depleted=false`、`expiry_date is not null`、owner／未刪除條件比照 `stats_repository.expiry()`，取 batch_id／owner_id／item name／expiry_date）→ Python 端判級＋查已發 set → 逐用戶：新 alert 列＋摘要 `emit(type=…)`＋`commit()`（per-user try/except 收 errors 續跑）
- [x] 摘要計數＝distinct batch；body 最急取該組 `expiry_date` 最小者；link／title／body 依〈盤點定案 3〉
- [x] 測試（注入 `today`）：
  - 空：無批次／無到期日／全部已耗盡 → `processed=0 emitted=0 errors=[]`
  - 門檻：31 天前無、30 天含 d30；8 天只 d30；7 天 d30+d7；0 天 d30+d7+d0；-1 天只 expired；-14 天仍發、-15 天停
  - 冪等：同日重跑 processed 不變、emit 次數不變；隔日 d30/d7/d0 不重發；expired 隔日再發（sent_on 不同）
  - distinct 計數：同批同日跨三級 → 摘要「1 件」
  - 偏好：`expiring_soon`×in_app 關 → 無站內列（external 依預設）；`expired` 全通道關 → 零輸出；多用戶隔離（A 關、B 開）
  - 失敗：monkeypatch 某用戶插入抛錯 → 該用戶 errors 記錄、其他用戶列保留；重跑只補該用戶
  - `emitted` 語義＝emit 呼叫數；`processed`＝alert 列數

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_expiry_scan.py`

### Task 1.4: `routes/jobs.py`＋schemas＋api-types

**Files:**
- Create: `apps/api/app/routes/jobs.py`、`apps/api/app/schemas/jobs.py`
- Modify: `apps/api/app/main.py`（`include_router(jobs.router)`）
- Modify: `packages/api-types/`（重生成）
- Test: `apps/api/tests/test_jobs_routes.py`

**TODO:**
- [x] `POST /api/jobs/{job_name}/run`（`get_current_admin`）→ 200 `{job, status, processed, emitted}`；未知 → 404；非 admin → 403；匿名 → 401；**admin PAT 可觸發**
- [x] `GET /api/jobs/{job_name}/status`（`get_current_user`）→ 200 `{job, thresholds: {advance_days:[30,7,0], expired_stop_days, stale_after_hours}, last_run: {status, started_at, finished_at, result}|null, stale}`；未知 → 404
- [x] `stale`＝無 last_run 或 `now - started_at > 26h`（`clock.today_taipei` 無關；用 UTC now）
- [x] `pnpm -F @ims/api-types gen:types`（export_openapi 流程比照 Phase 23）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q tests/test_jobs_routes.py`
- `cd apps/api && uv run python scripts/export_openapi.py > ../../packages/api-types/openapi.json && pnpm --filter @ims/api-types gen:types`

### Task 1.5: `stats/expiry` 加 `reminded_today`

**Files:**
- Modify: `apps/api/app/repositories/stats_repository.py`（`expiry()` 增 EXISTS 查詢）
- Modify: `apps/api/app/schemas/stats.py`（`ExpiryStats.reminded_today: bool`）
- Modify: `packages/api-types/`（重生成）
- Test: `apps/api/tests/test_stats_expiry_reminded.py`

**TODO:**
- [x] `reminded_today`＝該 owner 的批次今日（`today_taipei()`）有任一 `expiry_alerts`（EXISTS；常數查詢數，不隨列數成長）
- [x] 測試：今日有 alert→true；僅昨日→false；他用戶 alert 不影響
- [x] 既有 `test_stats_*` 零回歸（回應新增欄位）

**Commands:**
- `cd apps/api && uv run --extra test pytest -q`

### Task 1.6: 移除 `apscheduler`＋lock 重生成

**Files:**
- Modify: `apps/api/pyproject.toml`（L21 移除）
- Modify: `apps/api/uv.lock`（`uv lock`）

**TODO:**
- [x] `grep -rn apscheduler apps/api/app` 零引用確認
- [x] `cd apps/api && uv lock`（＋`uv run` 驗證環境）
- [x] 全套 API 測試零回歸

**Commands:**
- `cd apps/api && uv lock && uv run --extra test pytest -q`

---

## Phase 2: Web — 提醒排程頁與儀表板註記

### Task 2.1: stats 型別＋卡片註記＋jobs client／hook

**Files:**
- Modify: `apps/web/lib/api/stats.ts`（`ExpiryStats.reminded_today`）
- Modify: `apps/web/components/dashboard/expiry-card.tsx`（＋`.test.tsx`）
- Create: `apps/web/lib/api/jobs.ts`（`getJobStatus(name)`）
- Create: `apps/web/lib/hooks/use-job-status.ts`（React Query）
- Modify: `apps/web/messages/zh-TW.json`、`en.json`（`dashboard.expiry.remindedToday`）

**TODO:**
- [x] 卡片：`reminded_today===true` → muted 小字＋`Bell` icon（`data-testid="expiry-card-reminded"`；§5.1 不改變排序與尺寸）；false／undefined 不渲染
- [x] 測試：true 顯示（含鈴鐺 aria-hidden）、false 不顯示；既有卡片測試零回歸
- [x] `useJobStatus("expiry-scan")`：key `["job-status", name]`；`getJobStatus` 打 `GET /api/jobs/{name}/status`（型別取 `@ims/api-types`）

**Commands:**
- `pnpm -F @ims/web test && pnpm -F @ims/web typecheck`

### Task 2.2: `/settings/reminders`「提醒排程」頁＋nav＋i18n

**Files:**
- Create: `apps/web/app/(app)/settings/reminders/page.tsx`（＋`page.test.tsx`）
- Create: `apps/web/components/settings/reminders-panel.tsx`（＋`.test.tsx`）
- Modify: `apps/web/components/settings/settings-nav.ts`（群組 notifications 加 `reminders`，順序 channels→notifications→reminders）
- Modify: `apps/web/app/(app)/settings/page.test.tsx`（頁數更新）
- Modify: `apps/web/messages/zh-TW.json`、`en.json`（`settings.reminders.*`＋`settings.index.pages.reminders.*`）

**TODO:**
- [x] 面板（唯讀）：目前門檻（30 天前／7 天前／當天／過期後每日至 14 天，由 `thresholds` 渲染）；上次執行（時間＋狀態 badge：成功／失敗／未執行）
- [x] 停跑警示（`stale` 或 `last_run===null`）：warning 樣式文案＋cron 片段（`<code>` 每日 curl 範例，含佔位 `$PAT`）＋`docs/scheduling.md` 連結＋`/settings/tokens` 連結
- [x] 狀態契約（§5.4）：loading＝skeleton；error＝卡內 compact 錯誤＋重試；stale／failed／never 三態文案；a11y（`role="status"`／文字標籤非僅顏色）
- [x] 測試：loading／never-run（警示）／stale（警示）／failed（badge 紅）／success（時間＋無警示）；nav 出 3 頁；i18n zh/en 全鍵對齊

**Commands:**
- `pnpm -F @ims/web test && pnpm -F @ims/web typecheck`

---

## Phase 3: e2e＋文件

### Task 3.1: e2e — 掃描→摘要→落點、權限、設定頁

**Files:**
- Create: `apps/web/tests/reminders.spec.ts`

**TODO:**
- [x] 情境 1（主流程）：register 專屬用戶 → admin 前置階梯（已是 admin → bootstrap → 已有他管理員時 SQL 預置；e2e DB 長期沿用）→ API 建 item＋批次（`expiry=today+3`，落 d30＋d7 補發窗）→ admin token `POST /api/jobs/expiry-scan/run`＝`status: succeeded`、`processed ≥ 2`、`emitted ≥ 1`（共用 DB 有其他用戶殘留批次，故用 ≥）→ UI 通知中心**恰好一則**「1 件物品即將到期」→ 點擊→`/items?sort=expiry_asc` 載入（見「剩 3 天」）→ 同日重跑不重發（本用戶仍恰好一則）→ `/dashboard` 到期卡見「今天已彙總提醒」
- [x] 情境 2（權限）：非 admin run → 403；未知 job → 404；匿名 → 401；狀態任何登入者可讀（200）
- [x] 情境 3（設定頁）：由設定索引 IA 入口抵達 `/settings/reminders`；門檻四列、上次執行成功、無停跑警示
- [x] 全套 e2e 零回歸（15 spec；既有 items-crud 平行 flaky 另註）

**Commands:**
- `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web` → `cd apps/web && pnpm exec playwright test`

### Task 3.2: 文件收尾

**Files:**
- Create: `docs/scheduling.md`（crontab／systemd timer／GitHub Actions 範例＋PAT 步驟＋curl 範例）
- Modify: `CHANGELOG.md`（`[2.0.0-alpha.24]`）
- Modify: `docs/v2-roadmap.md`（Phase 24 列＋測試規模）
- Modify: `docs/plans/2026-10-15-next-iteration-roadmap.md`（§5.4 加「提醒排程（24）」列）
- Modify: 本計畫（勾選＋Final Verification 環境註記）

**TODO:**
- [x] CHANGELOG：job 機制＋`expiry-scan`＋冪等／失敗語義＋設定頁＋卡片註記＋apscheduler 移除＋測試規模
- [x] `docs/scheduling.md`：三分鐘上手（建 PAT→cron 一行→驗證狀態）
- [x] `git diff --check`；視覺走查（提醒排程頁：正常／停跑警示／行動 390；深色）
- [x] 計畫全勾；跑 Final Verification

**Commands:**
- `git diff --check`

---

## API 契約（定案）

**POST `/api/jobs/{job_name}/run`**（admin）

```json
// 200
{ "job": "expiry-scan", "status": "succeeded", "processed": 3, "emitted": 2 }
// 404 未知 job；403 非 admin；401 匿名
```

> `status`（`succeeded`／`failed`）為本計畫對 roadmap 契約 `{job, processed, emitted}` 的 additive 補充：部分使用者失敗時仍回 200，由 `status`＋`GET status` 的 `result.errors` 觀測；未知 job 才是 404。

**GET `/api/jobs/{job_name}/status`**（登入即可）

```json
{
  "job": "expiry-scan",
  "thresholds": { "advance_days": [30, 7, 0], "expired_stop_days": 14, "stale_after_hours": 26 },
  "last_run": {
    "status": "succeeded",
    "started_at": "2026-10-16T01:00:03Z",
    "finished_at": "2026-10-16T01:00:05Z",
    "result": { "processed": 3, "emitted": 2, "errors": [] }
  },
  "stale": false
}
```

**GET `/api/stats/expiry`**（既有）新增 `"reminded_today": true`

---

## §5.4 狀態表（本 phase 介面，T3.2 併入 roadmap）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| 提醒排程頁（24） | 卡內 skeleton | 從未執行 → 「排程尚未執行」警示＋cron 設定片段 | 卡內 compact 錯誤＋重試 | 上次執行時間＋成功 badge；門檻清單 | 上次執行 failed → 紅 badge＋error 摘要（其餘照常顯示） |
| 到期卡「今天已彙總提醒」註記（24） | 隨卡片 skeleton | 未發送 → 不渲染（不佔位） | 隨卡片錯誤態 | 鈴鐺＋muted 小字 | — |

---

## 驗收對照（roadmap §六 → 本計畫）

- 時間旅行測試（freeze date 驗各門檻觸發）→ T1.3（`today` 注入：30/7/0/-1/-14/-15 邊界）
- 冪等：同日重跑 emit 次數不變 → T1.3；e2e 情境 1
- 偏好過濾（關閉 → 不外送、站內也不建立）→ T1.3（多用戶隔離）
- 無批次／無到期批次 → 正常結束零輸出 → T1.3
- 停跑警示：`job_runs` 空或過舊 → 設定頁警示態 → T2.2（vitest 三態）＋T1.4（stale 計算）
- 中途失敗 → `failed`；重跑只補未送 → T1.3
- 端到端：進貨→掃描→emit→過濾→deep link 落點存在 → T3.1
- 權限：非 admin → 403；未知 job → 404 → T1.4＋T3.1
- apscheduler 移除 → T1.6
- §5.4 逐介面填寫 → 本計畫＋T3.2 併入 roadmap

## Final Verification

- [x] `cd apps/api && uv run --extra test pytest -q`：**602 passed**（560 → 602，零回歸）
- [x] `pnpm -F @ims/web test`：**269 passed／64 檔**；`pnpm -F @ims/web typecheck` 零錯誤
- [x] `ENABLE_DEV_ROUTES=1 docker compose up -d --build api web` → `pnpm exec playwright test`：**38 passed**（15 spec，含新增 reminders 3 情境）
- [x] `pnpm -F @ims/api-types gen:types` 後無未預期 diff（openapi 匯出＋型別重生成零 diff）
- [x] 視覺走查：提醒排程（正常／停跑警示／深色／行動 390）、到期卡註記——截圖確認：停跑橫幅含 cron 片段與 PAT／文件連結、行動版片段換行正常、深色對比可讀、卡片註記不改變排序與尺寸
- [x] `git diff --check`；CHANGELOG／roadmap／本計畫勾選完成
- [x] 收尾：commit 齊、merge 回 main、`docker compose down`

**環境註記（Final Verification 實測）：**
- e2e 需 `ENABLE_DEV_ROUTES=1`（web build arg；`/__dev/*` 展示頁為 theme spec 所需，生產預設關）——首次全跑時 theme spec 因缺此變數 404 失敗，補上後全綠
- e2e 管理員前置：`bootstrap-admin` 僅在「系統無任何管理員」時成功；e2e DB 長期沿用（可能已有他管理員）→ `reminders.spec` 採階梯（已是 admin → bootstrap → SQL 預置固定帳號 `e2e_jobs_admin`，非受測行為）
- 既有平行 flaky：首輪全跑 `items-crud`（tag 篩選）1 失敗、單跑綠；次輪全跑 38 全綠——資料競爭，與本 phase 無關
- bundled chromium 正常運行（無需系統 Chrome）
