# Phase 42 — 定期報表（週報）

- **日期**：2026-10-23
- **狀態**：✅ 完成（2026-10-23）
- **依據**：`docs/v2-roadmap.md` 下一輪候選 #1（「週報：重用月報 job 與 payload 渲染（`report.weekly`）」）
- **前置**：Phase 24（job registry／外部 cron）、Phase 27（估值）、Phase 31（月報）
- **規模**：M（API：migration＋job＋渲染＋per-job stale；Web：清單／詳情／設定／空狀態；e2e：1 情境）
- **契約變更**：`ReportRead` 新增 `kind`；`reports.period` 由 7 放寬到 10；`ReportPayload` 新增 `kind`（預設 `monthly`，舊資料相容）；偏好新增 `report_weekly_enabled`（預設 **false**）

---

## 目標

Phase 31 已有完整的月報：每月 1 日生成上一個完整月，站內通知＋雙語 Email，`/reports` 清單／詳情與開關。本 phase 新增**週報**，重用同一份 payload、同一個通知型別與同一套 UI，不再複製一套報表系統：

- 新增 job **`report.weekly`**：每週一生成**上一個完整 ISO 週**（週一 00:00 至週日 24:00，Asia/Taipei）
- 週報與月報共用 `reports` 資料表、`ReportPayload`、`/api/reports`、`/reports` UI、`report_ready` 通知與 Email 管線
- `/reports` 清單同時顯示月報與週報，以 `kind` 區分（徽章、週期範圍、週報用語）
- `/settings/reports` 新增「每週摘要」開關，**預設關閉**（避免未經同意每週寄信）
- 修正既有 job 停跑判定：月報 job 目前用固定 26 小時判斷 stale，導致每月 2 日起永遠顯示「停跑」；改為 **per-job stale 門檻**

---

## 範圍

### API

- **Migration 0026**
  - `reports.period`：`varchar(7)` → `varchar(10)`（容納 `2026-W42`）
  - 新增 `reports.kind`：`varchar(8) NOT NULL DEFAULT 'monthly'`（`monthly`／`weekly`）
  - 既有列自動為 `monthly`；`UNIQUE(user_id, period)` 不變（兩種 key 格式不重疊）
  - downgrade 先刪除 `kind='weekly'` 的列，再把 `period` 縮回 7（destructive，文件註明）
- `app/models/report.py`：`kind` 欄位（預設 `monthly`）、`period` 長度 10
- `app/schemas/reports.py`
  - `ReportPayload` 新增 `kind: Literal["monthly","weekly"] = "monthly"`（舊 payload 自動補預設）
  - `ReportRead` 新增 `kind`
- `app/services/reports_service.py`
  - `Period` 文件改為通用「期間」；新增 `previous_week(today)`（ISO 週）
  - `build_payload(..., kind)`；月報／週報共用 `build_payload`
  - `generate_weekly(session, today)` 與 `generate_monthly` 共用內部 `_generate(...)`
  - 資格：`is_active` ＋ `preferences.report_weekly_enabled` ＋ 至少 1 件可見物品
  - 空週仍建列（`has_activity=false`）、不通知；同 `(user_id, period)` 冪等；逐使用者 commit／錯誤隔離
- `app/services/report_render.py`
  - 依 `payload.kind` 選字庫：`本週動態`／`到期狀態（週末）`／`週初`／`週末`／`本週無動態`
  - 週報標題／Email subject／期間標籤改用 `period_start`／`period_end`（`2026 年 10 月 12–18 日`）
  - HTML 結構、escape、Email 管線不變
- `app/services/jobs_service.py`
  - `JobSpec` 新增 `stale_after_hours`（預設 26）；`is_stale(last, hours)`
  - `expiry-scan` 維持 26h；`report.monthly` 770h（約 32 天）；`report.weekly` 170h（7 天＋2 小時）
- `app/routes/jobs.py`：status 回傳該 job 的 `stale_after_hours` 並用它判斷 stale
- `app/schemas/preferences.py`：`report_weekly_enabled: bool = False`（Update 為 `bool | None`）
- `app/repositories/reports_repository.py`：清單改以 `generated_at DESC`（同時間再以 id 穩定排序）；混合週／月 key 不再用 `period` 排序
- `app/routes/reports.py`：`ReportRead.kind` 由資料列帶出

### Web

- `lib/format/period.ts` 新增 `formatPeriodRange(start, end, locale)`（UTC 中午建日期，永不拋錯）
- `components/reports/report-card.tsx`：`週報`／`月報` 徽章；週報標題用日期範圍；無動態文案分流
- `components/reports/report-summary.tsx`：依 `payload.kind` 切換「本週動態／到期狀態（週末）／週初／週末」
- `app/(app)/reports/[id]/page.tsx`：週報 heading／breadcrumb 用日期範圍
- `app/(app)/reports/page.tsx`＋`components/reports/reports-empty.tsx`
  - 空狀態依 `report_monthly_enabled`／`report_weekly_enabled` 顯示：
    - 兩者皆關 → 「報表已關閉」＋設定連結
    - 只開週報 → 「第一份週報將於下週一生成」
    - 其餘 → 「第一份月報將於次月 1 日生成」
- `components/settings/monthly-report-panel.tsx` → 更名 `reports-panel.tsx`
  - 「每月報表」開關（既有）＋「每週摘要」開關（預設關）
  - 排程說明：月報每月 1 日、週報每週一；各自 PUT 對應 key
- i18n（zh-TW／en）：`reports.kind.*`、`reports.noActivityWeekly`、`reports.detail.*Weekly`、`reports.empty.weeklyFirst`、`settings.reports.weekly*`、設定頁標題改「定期報表」
- 週報與月報共用 `useReports`／`useReport`；下載、篩選、分頁不做

### 測試

- **API**
  - `previous_week`：週一執行、週日執行、跨月、跨 ISO 年（`2026-01-01` → `2025-W52`）
  - 週報生成：`kind=weekly`、`period=2026-W42`、`period_start/end`、`payload.kind`、通知／Email 標題
  - 冪等重跑、空週建列不通知、無物品跳過、逐使用者錯誤隔離
  - 開關：預設 false、開啟後生成、關閉後跳過
  - 月報回歸：既有 9 月 payload／標題不變、舊 payload 無 `kind` 仍驗證為 monthly
  - `report_render`：zh／en 週報標題、日期範圍、`本週無動態`、HTML escape
  - jobs：`report.weekly` 註冊；per-job `stale_after_hours`（expiry 26／weekly 170／monthly 770）；`is_stale` 邊界
  - API：清單 `kind`、以 `generated_at` 新到舊、詳情 kind；舊資料預設 monthly
  - preferences：schema 預設 false、PUT true／false、GET 回傳
- **Web**
  - `formatPeriodRange`：同月、跨月、跨年、非法輸入
  - 清單卡：週報徽章＋日期範圍＋無動態文案
  - 詳情：週報 heading、`本週動態`、`週初／週末`
  - 設定：兩個開關、預設狀態、PUT 對應 key、toast
  - 空狀態：兩關／只開週報／月報預設
- **e2e**
  - 使用者開啟週報 → 回填物品 `created_at` 到上週 → 管理員跑 `report.weekly` → `/reports` 見週報卡（徽章＋範圍）→ 詳情見「本週動態」→ 通知 deep link → 重跑冪等
  - 既有月報 e2e 回歸（清單排序、空狀態文案、每月開關）

### 文件

- `docs/scheduling.md`：新增週報 cron（`0 9 * * 1`）、job 清單、`report.weekly` 行為語義、per-job stale 門檻、troubleshooting
- `CHANGELOG.md` alpha.42、`FEATURES.md` 報表章節、`docs/v2-roadmap.md`（Phase 42 完成列、候選重編號、測試規模）
- `docs/progress-2026-10-23.md` 更新為 Phase 40–42（或新增同日段落）
- 本計畫 `實作結果`／`Final Verification`／測試基線

### 明確不在本期範圍

- 自訂期間、日報、補跑指定週／月（backfill）
- 週報專屬指標口徑（例如只看到期 7 天）；週報沿用月報口徑，到期視窗仍為期末後 30 天
- CSV／PDF 匯出、報表刪除、已讀狀態、管理員讀他人報表
- 報表清單的週／月篩選 tabs（先以徽章區分；資料量不大）
- 新增通知管道或調整 `report_ready` 預設值
- 使用者時區偏好（全站固定 Asia/Taipei）

---

## 關鍵設計決策

### D1 期間：ISO 週（週一至週日，Asia/Taipei）

- 週報 key：`YYYY-Www`（以**週一**的 ISO week-year／week 計算，避免跨年歧義）
- `period_start`＝上一個完整週的週一、`period_end`＝該週週日
- 時間查詢一律半開區間 `[週一 00:00 TPE, 下週一 00:00 TPE)`，轉 UTC aware 後下 SQL
- job 無論在週一或補跑日執行，都生成**上一個完整 ISO 週**：
  - 週一 2026-10-19 執行 → `2026-10-12`～`2026-10-18`、`2026-W42`
  - 週日 2026-10-18 執行 → `2026-10-05`～`2026-10-11`、`2026-W41`（當週尚未結束）
  - 2026-01-01（四）執行 → `2025-12-22`～`2025-12-28`、`2025-W52`
- 測試必含 `2026-10-18 15:59 UTC`（＝10-18 23:59 TPE，屬上週）與 `2026-10-18 16:00 UTC`（＝10-19 00:00 TPE，屬新週）兩筆邊界

### D2 資料模型：同一張表＋`kind`，period 放寬

- 週報與月報共用 `reports`；`kind` 是人類可讀的類型，也是 API／UI 的分流依據
- `period` 放寬到 10：`2026-09`（7）與 `2026-W42`（8）並存；`UNIQUE(user_id, period)` 仍能保證冪等
- 既有列以 server default `monthly` 補值，不需改寫 payload
- **清單排序改 `generated_at DESC`**：混合 `YYYY-MM` 與 `YYYY-Www` 的字典序不是時間序（同一年 `2026-W42` 會排在 `2026-09` 後），改以「產生時間新到舊」最符合使用者預期；同時間以 id 穩定排序
- `ReportPayload` 加 `kind`（預設 monthly）：舊快照驗證時自動補值；Email／詳情不必再從資料列猜類型
- **payload version 維持 1**：`kind` 是向後相容的 additive 欄位，既有消費者（Web）不受影響；不為了單一欄位改版

### D3 資格、空週、冪等

- **資格**：`users.is_active` ＋ `report_weekly_enabled=true` ＋ 至少 1 件可見未刪除物品
- **預設關閉**：`report_weekly_enabled=False`。週報是新的主動寄送，預設開啟會對所有既有使用者每週寄信；改為 opt-in，設定頁明示「預設關閉」
- **空週**：仍建立列，`has_activity=false`，`/reports` 可見（留痕），但**不通知、不寄信**
- **無可見物品**：不建列、不寄
- **冪等**：`UNIQUE(user_id, period)`＋執行前查詢；重跑不新增、不重發。`processed`＝新建列數、`emitted`＝實際通知數
- **錯誤隔離**：每位使用者獨立 commit；單一失敗 rollback＋記入 `errors`，不阻斷其他人
- 月報與週報各自獨立開關；同時開啟會各收到一份，互不影響

### D4 指標口徑：完全重用 `build_payload`

- 週報使用與月報相同的 `build_payload`，只換 `Period`；不新增指標、不改 repository 聚合口徑
- 估值「期初」仍由目前存活物品與期間內 `quantity_logs`／建立／刪除反推，因此週期間也成立
- 到期視窗沿用期末後 **30 天**（`EXPIRING_HORIZON_DAYS=30`）；週報頻率較高，但口徑一致、避免兩套解釋
- 「目前庫存」是**生成當下**的快照（既有月報語義），不是週日 24:00 的歷史快照；文件維持此說明

### D5 交付與渲染：payload 自我描述

- 通知型別維持 `report_ready`；deep link 仍為 `/reports/{id}`
- `report_render` 依 `payload.kind` 選字庫，函式簽名不用新增 `kind` 參數：
  - zh：`週報：{range}`／`週報已生成：{range}`／`本週動態`／`到期狀態（週末）`／`週初`／`週末`／`本週無動態`
  - en：`Weekly report: {range}`／`Weekly report ready: {range}`／`This week`／`Expiry at week end`／`Start of week`／`End of week`／`No activity this week`
- 日期範圍由 `period_start`／`period_end` 產生：
  - 同月 zh：`2026 年 10 月 12–18 日`
  - 跨月 zh：`2026 年 9 月 28 日–10 月 4 日`
  - en：`Oct 12–18, 2026`（跨月／跨年完整標示）
- HTML 結構、escape、Email prefs、fail-soft 全部不動

### D6 Job 停跑門檻改為 per-job

- 現行 `is_stale()` 固定 26 小時，對月報是錯的：每月 2 日起就顯示停跑；週報也會在一週內大部分時間顯示停跑
- `JobSpec` 新增 `stale_after_hours`（預設 26）；`/status` 回傳對應值並用它判斷：
  - `expiry-scan`：26h
  - `report.weekly`：170h（7 天＋2 小時）
  - `report.monthly`：770h（約 32 天）
- 這是本 phase 的附帶修正，不動 job 執行語義；設定頁目前只顯示 expiry-scan，無 UI 改動

### D7 API：不新增端點

- `GET /api/reports`：`items[].kind`＋以 `generated_at` 新到舊；`limit`／`offset`／`total` 不變
- `GET /api/reports/{id}`：多回 `kind`；他人／不存在仍 404
- 不新增 `?kind=` 篩選；Web 一次顯示全部（目前資料量小），未來需要再加

### D8 Web：同一套報表頁容納兩種週期

- 清單卡以 `payload.kind` 顯示徽章與標題：
  - 月報：`2026年9月`（既有）
  - 週報：`2026年10月12日 – 2026年10月18日`（`formatPeriodRange`）
- 無動態徽章／詳情動態卡／估值期初期末字樣依 `kind` 分流；其餘版面完全重用
- 詳情頁 heading：月報 `{period}月報`、週報 `{range} 週報`（en 對應）
- 設定頁改名「定期報表」，兩個獨立開關；「每月報表」保留既有字串，e2e 既有步驟只需改空狀態文案
- 空狀態規則見「範圍 → Web」；`ReportsEmpty` 接受兩個 bool，不再只吃 `disabled`

### D9 e2e：用真實 job 產生週報

- 以 API 開啟 `report_weekly_enabled`、把物品 `created_at` 回填到上週（測試前置，非受測行為；API 無此欄位寫入面）
- 管理員觸發 `POST /api/jobs/report.weekly/run`，斷言 `status=succeeded`、`processed>=1`
- UI：`/reports` 卡片含「週報」徽章與日期範圍 → 詳情「本週動態」→ 通知標題含「週報已生成」→ deep link
- 重跑 job → 該使用者 `total` 不變、通知不重複

### D10 依賴與相容性

- 無新增依賴；`zoneinfo`／`datetime.isocalendar()` 皆為標準庫
- Migration 以 `batch_alter_table` 同時支援 SQLite（測試）與 PostgreSQL（live）
- 舊 API 消費者：`ReportRead` 新增欄位、`period` 放寬皆為 additive；Web 同批更新
- 舊 payload 沒有 `kind`：Pydantic 預設 monthly，詳情／Email 行為與現在一致
- e2e 既有月報測試需同步更新：空狀態文案、清單排序（若同使用者同時有兩種報表）

---

## 資料模型（migration 0026）

```text
reports
  id            UUID PK
  user_id       UUID FK users(id) ON DELETE CASCADE, index
  period        varchar(10)  -- "2026-09" / "2026-W42"
  kind          varchar(8)   -- "monthly" / "weekly"，default 'monthly'
  payload       JSON/JSONB
  generated_at  timestamptz
  UNIQUE (user_id, period)
```

升級：

1. `period` 7 → 10
2. 新增 `kind`，`NOT NULL DEFAULT 'monthly'`
3. 既有列自動 monthly，無需資料搬移

降級：

1. 刪除 `kind='weekly'` 的列（週報 key 放不進 7）
2. 移除 `kind`
3. `period` 10 → 7

---

## API payload 範例（週報）

```json
{
  "version": 1,
  "kind": "weekly",
  "period": "2026-W42",
  "timezone": "Asia/Taipei",
  "period_start": "2026-10-12",
  "period_end": "2026-10-18",
  "generated_at": "2026-10-19T01:00:00Z",
  "currency": "TWD",
  "totals": { "item_count": 42, "quantity": 57 },
  "activity": {
    "items_created": 2,
    "items_deleted": 0,
    "quantity_in": 5,
    "quantity_out": 1,
    "loans_out": 1,
    "loans_returned": 0,
    "loans_overdue": 0
  },
  "expiry": { "expiring_soon": 1, "expired": 0 },
  "valuation": { "start": "1000.00", "end": "1200.00", "delta": "200.00", "unpriced_items": 0 },
  "top_categories": [{ "label": "食品", "count": 3 }],
  "top_locations": [{ "label": "儲藏室", "count": 2 }],
  "has_activity": true
}
```

`GET /api/reports` 的 `items[]` 額外含 `kind`；其餘欄位不變。

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：migration 0026＋model／schema

- `reports.period` 放寬、`kind` 欄位、model／migration
- `ReportPayload.kind`（預設 monthly）、`ReportRead.kind`
- 測試：SQLite `create_all` 可寫入 8 字元 period；舊 payload（無 kind）驗證為 monthly；migration up/down 在 SQLite 與 PG 實測

### T1.2 API：週期間與 payload

- `previous_week()`／`build_payload(kind=...)`
- 測試：三個日期邊界、跨月、跨 ISO 年；`period_start/end`、`kind`、`has_activity`
- 月報既有 payload 測試不得改期望（除了新增 kind 預設）

### T1.3 API：`report.weekly` job＋偏好

- `_generate()` 共用流程；`generate_weekly()`；註冊 `report.weekly`
- `report_weekly_enabled` schema／預設 false
- 測試：生成、冪等、空週、無物品、開關、錯誤隔離、通知／Email 文案、job 執行

### T1.4 API：渲染

- `report_render` 依 payload.kind 選字庫與日期範圍
- 測試：zh／en 週報 title／subject／body／HTML、跨月範圍、HTML escape；月報輸出零變化

### T1.5 API：per-job stale

- `JobSpec.stale_after_hours`、`is_stale(last, hours)`、`/status`
- 測試：三個 job 的 status thresholds；`is_stale` 在邊界前後

### T1.6 API：清單排序與 `kind`

- repository 排序改 `generated_at DESC, id`；route 帶出 kind
- 測試：同使用者月報＋週報混合、順序、分頁 total 不變、舊資料預設 monthly

### T2.1 Web：期間格式與清單卡

- `formatPeriodRange`＋測試（同月／跨月／跨年／非法）
- `ReportCard` 徽章、週報標題、無動態文案

### T2.2 Web：詳情頁

- 週報 heading／breadcrumb、`本週動態`、`週初／週末`
- 測試：以 weekly payload 渲染

### T2.3 Web：設定雙開關

- `reports-panel.tsx`（由 monthly 更名）、兩個 switch、PUT key、toast
- 頁面標題改「定期報表」；i18n
- 測試：預設值、點擊 monthly／weekly 各自送出正確 payload、失敗 toast

### T2.4 Web：空狀態

- `ReportsEmpty` 接 monthly／weekly 兩個 bool；`/reports` 傳入 prefs
- 測試：兩關、只開週報、預設月報；既有月報 e2e 文案同步

### T3.1 e2e

- `reports-weekly.spec.ts`（或併入 `reports.spec.ts`）：開啟週報、回填上週、跑 job、清單／詳情／通知／冪等
- 既有 `reports.spec.ts` 月報流程回歸

### T3.2 文件

- `docs/scheduling.md`、`CHANGELOG.md` alpha.42、`FEATURES.md`、`docs/v2-roadmap.md`、進度文件、本計畫 Final Verification

---

## 測試清單（RED 先寫）

| # | 測試 | 期望 |
|---|---|---|
| 1 | `previous_week` 週一 | 上週一～上週日、正確 key |
| 2 | `previous_week` 週日 | 再上一週（當週未結束） |
| 3 | `previous_week` 跨 ISO 年 | `2026-01-01` → `2025-W52` |
| 4 | 週報生成 | `kind=weekly`、`period=2026-W42`、payload kind |
| 5 | 週報冪等 | 重跑不新增列、不重發 |
| 6 | 空週 | 建列、`has_activity=false`、無通知／Email |
| 7 | 無可見物品 | 不建列 |
| 8 | 週報開關預設 | false；關閉不生成、開啟生成 |
| 9 | 週報通知 zh | 標題含「週報已生成」與日期範圍 |
| 10 | 週報 Email en | subject／HTML 為週報用語 |
| 11 | 月報回歸 | 標題仍為「月報」、期間不變 |
| 12 | 舊 payload | 無 `kind` → monthly |
| 13 | per-job stale | expiry 26／weekly 170／monthly 770 |
| 14 | `is_stale` 邊界 | 170h 前後各一 |
| 15 | API 清單混合 | 新到舊、`kind` 正確、total 不變 |
| 16 | API 詳情 | `kind` 正確；他人 404 不變 |
| 17 | Web 週期格式 | 同月／跨月／跨年 |
| 18 | Web 清單卡 | 週報徽章＋範圍＋無動態 |
| 19 | Web 詳情 | 週報 heading＋本週動態＋週初／週末 |
| 20 | Web 設定 | 兩開關各自 PUT 正確 key |
| 21 | Web 空狀態 | 兩關／只開週報／月報預設 |
| 22 | e2e | 週報生成到通知 deep link＋冪等 |
| 23 | e2e 月報回歸 | 既有流程仍綠 |

---

## 風險與對策

| 風險 | 影響 | 對策 |
|---|---|---|
| 預設開啟週報造成未預期寄信 | 使用者反彈／退訂 | `report_weekly_enabled` 預設 **false**；設定頁明示 opt-in |
| 混合週／月 key 排序錯亂 | 清單順序不直覺 | 改用 `generated_at DESC`；測試混合資料 |
| Migration 在 SQLite／PG 行為不同 | 部署失敗 | `batch_alter_table`；兩邊實際 up/down；downgrade 刪週報列並註明 |
| 舊 payload 缺 `kind` | 詳情／Email 顯示成月報 | Pydantic 預設 monthly；測試舊 payload |
| 月報 job 被誤判停跑（既有 bug） | 設定頁／監控誤報 | per-job stale 門檻；補測試與文件 |
| 週報 email 太吵 | 使用者關閉 | 預設關＋獨立開關＋沿用 Email 偏好 |
| 跨年 ISO 週 key 錯 | 週報落錯期間／重複 | 以週一的 `isocalendar()` 計算；邊界測試 |
| 週報與月報同一天生成 | 清單順序／通知混淆 | `kind` 徽章與標題清楚區分；排序用 generated_at |
| e2e 依賴 `created_at` 回填 | 測試脆弱 | 沿用月報 e2e 的 psql 前置模式；只回填測試資料 |
| 既有月報 e2e 文案變更 | 假紅 | 同批更新空狀態斷言；其餘步驟不動 |

---

## 實作結果（與計畫差異）

**已完成**：

- **Migration 0026**：`reports.period` 7 → 10、新增 `reports.kind`（`varchar(8) NOT NULL DEFAULT 'monthly'`）；`UNIQUE(user_id, period)` 不變。downgrade 先刪 `kind='weekly'` 再縮回 7。
- **API**：`ReportKind`／`previous_week`／`week_period`／`build_payload(kind=...)`／`generate_weekly`／`report.weekly` job；`report_weekly_enabled` 偏好（預設 false）；`report_render` 依 `payload.kind` 選字庫與日期範圍；`JobSpec.stale_after_hours`（expiry 26／weekly 170／monthly 770）；清單改 `generated_at DESC`、回傳 `kind`。
- **Web**：`formatPeriodRange`、`ReportCard` 週報徽章＋範圍、`ReportSummary` 週報文案、詳情頁 heading／breadcrumb、`reports-panel.tsx` 雙開關、空狀態三分支、zh-TW／en i18n。
- **測試**：API 1248 passed、Web 787 passed（132 檔）、typecheck 0 error、e2e 89 passed（`--workers=1`）。
- **文件**：`CHANGELOG.md` alpha.42、`FEATURES.md`、`docs/scheduling.md`、`docs/v2-roadmap.md`、`docs/progress-2026-10-23.md` 與本計畫。

**與計畫的差異**：

1. **Migration 的 SQLite 驗證改成 PG-only**：計畫原寫「migration up/down 在 SQLite 與 PG 實測」，但既有 migration 0021 的 constraint ALTER 在 SQLite 直接 `NotImplementedError`，無法只為 0026 繞過。改以獨立 PostgreSQL 容器實測 `0025 → 0026 → 0025 → 0026`；SQLite 測試仍以 `create_all` 覆蓋新 schema（可寫入 8 字元 period、`kind` 預設 monthly），但不硬跑 0026 migration。此限制已寫入 CHANGELOG／進度文件。
2. **i18n key 名稱與計畫草稿不同**：實際使用 `reports.weeklyBadge`、`reports.noActivityWeekly`、`reports.empty.weeklyOnly`／`weeklyOnlyHint`、`reports.detail.headingWeekly`／`activityWeekly`／`expiryWeekly`／`startWeekly`／`endWeekly`、`settings.reports.weeklyTitle`／`weeklyDescription`／`weeklyScheduleNote`／`monthlySavedOn`／`monthlySavedOff`／`weeklySavedOn`／`weeklySavedOff`。語意與計畫一致，只是鍵名更貼近現有 `reports.*` 結構。
3. **月報不另顯示「月報」徽章**：只有週報加徽章，避免既有月報卡片多一個視覺噪音；月報仍以 `YYYY年M月` 標題區分。計畫原寫「週報／月報徽章」。
4. **e2e 併入 `tests/reports.spec.ts`**：沒有另開 `reports-weekly.spec.ts`；在同一個 spec 內重用註冊、登入、管理員與 psql 前置，對照月報／週報兩種流程。
5. **e2e 由 UI 開關啟用週報**：計畫 D9 寫「以 API 開啟」，實際從 `/settings/reports` 點「每週摘要」並斷言 toast，順便覆蓋新設定面板；job 仍由管理員端點真實觸發。
6. **空狀態連結**：兩者皆關與「只開週報」都提供「前往報表設定」連結；月報預設（含週報也開）維持「第一份月報將於次月 1 日生成」且不顯示連結。計畫只要求分流，未細分連結。
7. **`ReportPayload.kind` 在 OpenAPI 為 required**：雖有 Pydantic 預設值，產生出的 TypeScript 仍是必填；所有 Web fixture 已同步補 `kind`，typecheck 0 error。

**未做（與計畫一致）**：自訂期間、日報、指定週 backfill、週報專屬指標、CSV／PDF、報表刪除／已讀、`?kind=` 篩選、新通知管道、使用者時區偏好。

---

## Final Verification

- **API 全套**：`cd apps/api && uv run pytest -q` → **1248 passed**（227.75s）
- **API golden eval**：`cd apps/api && uv run pytest evals/ -q` → **28 passed／1 skipped**
- **Web 全套**：`cd apps/web && pnpm vitest run` → **787 passed（132 檔）**
- **Web 型別**：`pnpm typecheck` → **0 error**
- **E2E**：`pnpm exec playwright test --project=chromium --workers=1` → **89 passed**；其中 `tests/reports.spec.ts` 4/4（月報生成／月報開關／週報／導覽）
- **Migration 0026（live stack）**：API 容器啟動時自動 `0025 → 0026`；`alembic current` 為 `0026 (head)`
- **Migration 0026（獨立 PG 容器）**：空庫 `upgrade head` → `downgrade 0025`（週報列刪除、`period` 縮回 7、`kind` 移除）→ `upgrade head`，全程成功
- **api-types**：重新產生 `openapi.json` 與 `src/index.ts`；新增 `ReportRead.kind`、`ReportPayload.kind`、`report_weekly_enabled`，無新增 path
- **Live 驗證**：週報 e2e 以 nginx → API → PostgreSQL 真實路徑完成；月報既有流程與空狀態文案同步回歸

---

## 測試基線（main，Phase 42 完成）

- API：**1248 passed**；golden eval **28 passed／1 skipped**
- Web：**787 passed（132 檔）**；typecheck 0 error
- e2e：chromium **89 passed**（`--workers=1`）；ai-stub 4
- Migration：`0026 (head)`
- Phase 42 新增：`report.weekly` job、`reports.kind`、`ReportRead.kind`／`ReportPayload.kind`、`report_weekly_enabled`；無新增 API path
