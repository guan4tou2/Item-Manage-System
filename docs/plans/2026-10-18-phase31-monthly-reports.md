# Phase 31 — 定期報表（月報）

> 依據：`docs/plans/2026-10-15-next-iteration-roadmap.md` §Phase 31、§5.2、§5.3、§5.4、§5.6
> 分支：`claude/phase31-monthly-reports`／worktree：`.claude/worktrees/phase31-monthly-reports`
> 前置：Phase 24（job 機制）、Phase 27（估值）、Phase 30（viewer 唯讀）

## 目標

每月 1 日（Asia/Taipei）自動彙整「上月」物品動態，以站內通知＋Email HTML 交付；
`/reports` 提供月報歷史清單與詳情；設定可開關（預設開）；導覽新增「分析」群組
（桌面統計 dropdown、行動 drawer 二層展開）。

## 範圍

- **機制**：重用 Phase 24 job registry，新增 `report.monthly`
- **內容**：庫存現況、新增／刪除、消耗（批次＋數量調整）、借出／歸還／逾期、
  過期與 30 天內到期、庫存估值變化、熱門分類／位置
- **DB**：`reports`（`user_id`、`period`、`payload`、`generated_at`，`UNIQUE(user_id, period)`）
- **API**：`GET /api/reports`（自己的清單）、`GET /api/reports/{id}`（自己的詳情）
- **交付**：站內通知 `report_ready`＋Email HTML（雙語、plain-text fallback）；
  站內詳情與 Email 共用同一 payload
- **Web**：`/reports` 清單、`/reports/[id]` 詳情、`/settings/reports` 開關、
  桌面統計 dropdown、行動 drawer 二層分組
- **文件**：`docs/scheduling.md` 新增月報 cron、CHANGELOG、v2-roadmap

### 明確不在本期範圍

- 週報、自訂期間、歷史回補（backfill）
- CSV 附件（roadmap 標為 stretch；檔名 i18n 一併延後）
- PDF 匯出、報表寄送對象自訂（僅寄給使用者本人）
- 管理員讀取他人報表
- 月報「已讀」狀態、報表刪除

## 關鍵設計決策

### D1 期間與時區（固定 Asia/Taipei）

- `period = "YYYY-MM"`；`period_start`＝該月 1 日、`period_end`＝該月最後一日
- 時間欄位比較一律用半開區間
  `[period_start 00:00 TPE, 次月 1 日 00:00 TPE)`，轉為 UTC aware 後下 SQL
- job 於「次月 1 日以後」任何時間執行都生成**上一個完整月**（以 `today_taipei()` 推算）；
  重跑冪等（見 D3）
- 測試 fixture 的 datetime 一律以 **UTC aware** 建構，避免 SQLite 忽略 tzinfo 造成
  邊界失真；測試需含 `09-30 15:59 UTC`（＝09-30 23:59 TPE，屬於 9 月）與
  `09-30 16:00 UTC`（＝10-01 00:00 TPE，屬於 10 月）兩筆

### D2 使用者可見範圍

- 沿用 `visibility_service.visible_item_owner_ids()`：本人＋同群組成員
- 報表只納入該使用者「現在可見」的物品（含群組共用）；不查詢、不輸出他人私人資料
  （本系統物品可見性以 owner 為單位，無更細的 per-item 隱私旗標）
- viewer（唯讀帳號）同樣會收到自己的月報；報表頁本身無寫入操作

### D3 資格、空月語義、冪等

- **資格**：`users.is_active` ＋ `preferences.report_monthly_enabled`（預設 true）
  ＋ 至少 1 件可見且未刪除物品
- **空動態月**：仍建立 `reports` 列，`payload.has_activity=false`
  → `/reports` 顯示「本月無動態」留痕（不缺席）
- **空動態不發**：`has_activity=false` 時**不**建立站內通知、**不**寄 Email
  （對應驗收「空資料用戶跳過不發」）
- **無可見物品**：不建列、不寄（避免零物品帳號每月收到空報表）
- **冪等**：`UNIQUE(user_id, period)`＋執行前查詢；已存在→跳過生成與發送。
  `JobResult.processed`＝本次新建列數、`emitted`＝本次實際通知到的使用者數
- **錯誤隔離**：每位使用者獨立 commit；單一使用者失敗→rollback＋記入 `errors`，
  不阻斷其他人；有 errors → job `failed`（其他使用者仍已落地）

### D4 指標定義（固定口徑，測試對帳）

期間一律 `[start_utc, end_utc)`；「月底狀態」以 `period_end` 為基準日。

| 欄位 | 定義 |
|------|------|
| `totals.item_count` / `totals.quantity` | 生成當下可見、未刪除物品數／Σ quantity |
| `activity.items_created` | 可見範圍內 `created_at ∈ 期間` 的物品數（含建立後刪除） |
| `activity.items_deleted` | 可見範圍內 `is_deleted=true` 且 `updated_at ∈ 期間`（軟刪除以 `updated_at` 為刪除時間近似；刪除後不再更新） |
| `activity.quantity_in` | 期間內 `quantity_logs` 正 delta 總和（手動調整／盤點增量；建立物品不寫 log） |
| `activity.quantity_out` | 期間內 `quantity_logs` 負 delta 絕對值總和（批次消耗／盤點減量） |
| `activity.loans_out` | 可見物品的 `item_loans.lent_at ∈ 期間` 筆數 |
| `activity.loans_returned` | 可見物品的 `returned_at ∈ 期間` 筆數 |
| `activity.loans_overdue` | 期末仍未還且 `expected_return < period_end`（日期比較） |
| `expiry.expiring_soon` | 期末未耗盡批次、`period_end < expiry_date ≤ period_end + 30 天` |
| `expiry.expired` | 期末未耗盡批次、`expiry_date ≤ period_end` |
| `valuation.end` | 生成當下：Σ(`cost × quantity`)，未刪除、`cost` 非 null |
| `valuation.start` | 重建：`end − created_value + deleted_value − Σ(期間 log delta × cost)`（詳見下） |
| `valuation.delta` | `end − start` |
| `valuation.unpriced_items` | 未刪除、`cost` 為 null 的物品數 |
| `top_categories` / `top_locations` | 生成當下未刪除物品的分布，取前 3 名；分類名稱／位置樹路徑；null → 未分類／未指定 |

**估值重建公式**（`created_value`、`deleted_value` 僅計 `cost` 非 null）：

```
end   = Σ alive 物品 cost×qty
created_value = Σ alive 且 created_at ∈ 期間 的 cost×qty
deleted_value = Σ deleted 且 updated_at ∈ 期間 的 cost×qty
log_delta_value = Σ (new−old)×cost
                  over quantity_logs ∈ 期間，且 item.created_at < 期間起點
start = end − created_value + deleted_value − log_delta_value
```

- 期間內「建立後又刪除」的物品：不計入 `created_value`／`deleted_value`，
  其 log 也排除（對 start 的淨影響為 0）
- 已知近似：若歷史上存在未寫 `quantity_logs` 的數量變更（目前所有入口皆經
  `item_history_service.log_quantity_change`），重建值可能漂移；payload 記錄
  `version=1`，未來若需精確歷史改以快照實作
- 金額以 Decimal 計算、量化 2 位，payload 內以字串輸出；幣別取使用者偏好

### D5 交付：站內＋Email

- **總開關**：`preferences.report_monthly_enabled`（預設 true）控制
  「是否生成報表列＋是否交付」；關閉→job 完全不處理該使用者
- **管道**：站內通知沿用 `report_ready` 類型與 Phase 23 偏好矩陣
  （in_app／line／telegram／web_push）
- **Email**：`report_ready` × `email` 偏好開啟且使用者有 email 時寄送
  **HTML 月報**；同一封信含 plain-text alternative
  （fastapi-mail：`subtype=plain`＋`alternative_body=html`＋`multipart_subtype=alternative`）
- **避免重複信**：`emit()` 新增 `exclude_channels`，月報 job 呼叫
  `emit(..., exclude_channels={"email"})`，Email 由 job 單獨以 HTML 版本寄出
- **語言**：伺服器端 `report_render` 提供 zh-TW／en 兩套 subject／text／HTML，
  依使用者 `preferences.language`（next-intl 不參與 Email 渲染）
- **連結**：`{public_web_url}/reports/{id}`（Email 絕對 URL；站內通知 `/reports/{id}`）
- **fail-soft**：SMTP 未設定或寄送失敗只記 log／回傳 False，不中斷 job、
  不列入 `errors`（符合驗收 Email fail-soft）
- **HTML 安全**：所有使用者可控字串（分類／位置名稱）經 `html.escape`
- **CSV 檔名 i18n**：本期不做（CSV 附件為 stretch），已在範圍外註明

### D6 API 契約

```
GET /api/reports?limit=20&offset=0
→ 200 {items: ReportRead[], total: int, limit: int, offset: int}
   排序：period DESC（字串 YYYY-MM 可字典序排序）

GET /api/reports/{report_id}
→ 200 ReportRead｜404（不存在或非本人）
```

- 兩端點皆需登入；**只回傳自己的報表**（管理員亦不可讀他人）
- `ReportRead = {id, period, generated_at, payload: ReportPayload}`
- 不提供建立端點；僅 job（管理員 PAT／cron）生成

### D7 設定頁

- 新增 `/settings/reports`（設定 → 通知與提醒群組的第 4 頁，仍在每群組 ≤6 頁內）
- 內容：月報總開關（Switch）＋排程說明（每月 1 日、Asia/Taipei）＋
  「查看報表歷史」連結；關閉說明「不再生成與寄送」
- 未樂觀更新：以偏好查詢結果為準，成功後 toast；失敗 toast＋維持原值
- 讀寫沿用 `GET/PUT /api/users/me/preferences` 與既有
  `usePreferences`／`useUpdatePreferences`

### D8 導覽（roadmap §5.3）

- **首層項目維持 11**：`NAV_ITEMS` 不新增報表
- **桌面**：`統計` 改為 dropdown，含「統計」「報表」；路徑 `/statistics` 或
  `/reports` 時 trigger 呈現 active
- **行動**：drawer 改為「群組標題＋二層展開」新元件（`NavGroup`），
  4 個群組：
  - 物品：儀表板、物品、掃碼、盤點、分類、位置
  - 分析：統計、報表
  - 協作：清單、協作、通知
  - 系統：設定
- 群組預設展開；點標題收合／展開（`aria-expanded`＋`aria-controls`）；
  點項目導航並關閉 drawer
- 新增 `nav.groups.*`、`nav.reports` i18n

### D9 報表頁互動狀態（roadmap §5.4）

| 介面 | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|------|---------|-------|-------|---------|---------|
| `/reports` 清單 | 3 張卡 skeleton | 首月→「第一份月報將於次月 1 日生成」；月報關閉→「月報已關閉」＋前往設定連結 | 錯誤說明＋重試 | 週期卡（期間、生成時間、摘要數字；無動態顯示「本月無動態」） | — |
| `/reports/[id]` 詳情 | 區塊 skeleton | 不適用（404 走 ERROR） | 載入失敗＋重試＋返回清單 | 現況／動態／到期／估值／熱門分類與位置；`has_activity=false` 頂部註記「本月無動態」 | 未設定成本→估值旁註記；無分類／位置→「—」 |
| `/settings/reports` | 卡內 skeleton | 偏好載入失敗→錯誤卡＋重試 | 切換失敗 toast＋維持原值 | 開關成功 toast | — |

- 所有空狀態附下一步動作（`.impeccable.md`）
- 行動版（390px）：清單卡縱向堆疊、詳情 2 欄 grid、設定卡不溢出

## 資料模型（migration 0023）

```python
class Report(Base):
    __tablename__ = "reports"
    id: UUID (pk)
    user_id: UUID FK users ON DELETE CASCADE, index
    period: String(7)              # YYYY-MM（Asia/Taipei）
    payload: JSONType              # ReportPayload（version=1）
    generated_at: DateTime(tz)     # default _utcnow
    __table_args__ = (UniqueConstraint("user_id", "period", name="uq_reports_user_period"),)
```

- migration `0023_reports.py`（down_revision `0022`）：建表＋unique 約束＋
  `ix_reports_user_id`；downgrade drop table
- 偏好欄位不需 migration（`users.preferences` JSON）

## API payload 範例

```json
{
  "version": 1,
  "period": "2026-09",
  "timezone": "Asia/Taipei",
  "period_start": "2026-09-01",
  "period_end": "2026-09-30",
  "generated_at": "2026-10-01T00:05:00Z",
  "currency": "TWD",
  "totals": {"item_count": 42, "quantity": 123},
  "activity": {
    "items_created": 3,
    "items_deleted": 1,
    "quantity_in": 10,
    "quantity_out": 4,
    "loans_out": 2,
    "loans_returned": 1,
    "loans_overdue": 1
  },
  "expiry": {"expiring_soon": 3, "expired": 2},
  "valuation": {
    "start": "1200.00",
    "end": "1500.00",
    "delta": "300.00",
    "unpriced_items": 2
  },
  "top_categories": [{"label": "食品", "count": 12}],
  "top_locations": [{"label": "儲藏室 / 上層", "count": 8}],
  "has_activity": true
}
```

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 DB：Report model＋migration 0023

- RED：`tests/test_reports_models.py` — 建兩筆同 `(user_id, period)` → `IntegrityError`；
  payload JSON 往返；預設 `generated_at`
- GREEN：`app/models/report.py`、`app/models/__init__.py` 註冊、
  `alembic/versions/0023_reports.py`
- 驗證：pytest 該檔；`alembic upgrade head` / `downgrade 0022` 演練

### T1.2 報表 payload：期間、現況、動態、熱門分類／位置

- RED：`tests/test_reports_payload.py`
  - 期間推算（月初邊界、TPE↔UTC：15:59/16:00 UTC 兩筆）
  - totals／created／deleted／quantity_in／quantity_out 對帳
  - 群組可見範圍（同組成員納入、非成員排除）
  - top_categories／top_locations（前 3、null 標籤、位置路徑）
- GREEN：`app/schemas/reports.py`（payload models）、
  `app/repositories/reports_repository.py`（聚合查詢）、
  `app/services/reports_service.py::build_payload`

### T1.3 報表 payload：估值、到期、借還

- RED：擴充 `tests/test_reports_payload.py`
  - 估值重建：月初已有、期間新增／刪除、期間 log 增減、未設定成本
  - 建立後刪除（淨影響 0）、期間前 log 不計
  - expiring_soon（30 天）／expired（期末）
  - loans_out／returned／overdue（期末逾期）
- GREEN：repository 查詢＋`build_payload` 完成

### T1.4 API：清單／詳情

- RED：`tests/test_reports_routes.py`
  - 401；空清單；排序（period DESC）；limit/offset；total
  - 詳情 200；他人報表 404；不存在 404
- GREEN：`app/routes/reports.py`、`app/main.py` 註冊、
  `report_read`／`report_list` helpers

### T1.5 伺服器端雙語渲染（站內通知文字＋Email text/HTML）

- RED：`tests/test_report_render.py`
  - zh-TW／en 的 period label、subject、text、HTML
  - HTML 含關鍵數字；使用者字串 `<script>` 被 escape
  - plain-text 含完整摘要與絕對連結
- GREEN：`app/services/report_render.py`
  （`period_label`、`money`、`notification_text`、`render_text`、`render_html`）

### T1.6 Email HTML 與管道排除

- RED：
  - `tests/test_external_notifications.py` 新增：`deliver_email(..., html=...)`
    使用 `alternative_body`＋`multipart_subtype=alternative`（monkeypatch `FastMail`）
  - `tests/test_notifications_emit.py`（或既有檔）新增：`emit(exclude_channels={"email"})`
    不呼叫 email、其他管道照常；預設行為不變
- GREEN：`external_notifications.deliver_email` 增加 `html` 參數、
  `deliver_all(..., exclude=...)`；`notifications_service.emit` 轉傳

### T1.7 偏好＋`report.monthly` job＋交付

- RED：`tests/test_report_job.py`
  - 註冊 `report.monthly`；生成上月；`processed`／`emitted`
  - 重跑冪等（不新增列、不重發）
  - 空動態月：建列、不通知、不寄信
  - `report_monthly_enabled=false`：不建列
  - 無可見物品：不建列
  - 有動態：站內 `report_ready`＋連結；HTML email 寄出（monkeypatch）
  - `report_ready`×email 關閉→不寄；email 失敗→job 仍 succeeded（fail-soft）
  - 單一使用者失敗→其他使用者仍生成、errors 記錄
- GREEN：
  - `app/schemas/preferences.py` 增加 `report_monthly_enabled`（預設 true）
  - `app/services/reports_service.py::generate_monthly`＋job 註冊
  - `app/routes/jobs.py` import `reports_service`（觸發註冊）

### T2.1 Web API client＋hooks

- RED：`lib/api/reports.test.ts`（URL／query／error）、`lib/hooks/use-reports.test.tsx`
- GREEN：`lib/api/reports.ts`（api-types 型別）、`lib/hooks/use-reports.ts`

### T2.2 `/reports` 清單頁

- RED：`app/(app)/reports/page.test.tsx`／`components/reports/*.test.tsx`
  - loading skeleton、首月 empty、月報關閉 empty＋設定連結
  - 成功：週期標題（zh-TW／en）、摘要、無動態「本月無動態」
  - error＋重試（refetch 呼叫）
- GREEN：`app/(app)/reports/page.tsx`、`components/reports/report-card.tsx`、
  i18n `reports.*`

### T2.3 `/reports/[id]` 詳情頁

- RED：詳情頁測試—區塊數字、估值正負、未設定成本註記、
  無動態註記、404/error 返回、行動版 class
- GREEN：`app/(app)/reports/[id]/page.tsx`、`components/reports/report-summary.tsx`、
  i18n

### T2.4 `/settings/reports` 開關頁

- RED：`components/settings/monthly-report-panel.test.tsx`
  - 預設開；切換送 PUT `{report_monthly_enabled:false}`；成功 toast
  - 失敗 toast＋維持原值；loading skeleton；錯誤重試
- GREEN：`app/(app)/settings/reports/page.tsx`、
  `components/settings/monthly-report-panel.tsx`、`settings-nav.ts` 增加頁面、
  i18n `settings.index.pages.reports.*`／`settings.reports.*`

### T2.5 導覽：桌面統計 dropdown＋行動二層 drawer

- RED：
  - `components/shell/app-header.test.tsx`：dropdown 開啟→「統計」「報表」；
    `/reports` 時 trigger active
  - `components/shell/mobile-nav.test.tsx` 更新：4 群組標題、預設展開、
    點標題收合、點報表導航
- GREEN：`nav-items.ts` 增加 `NAV_GROUPS`、`app-header.tsx` dropdown、
  `components/shell/nav-group.tsx`、`mobile-nav.tsx`、i18n `nav.reports`／
  `nav.groups.*`

### T3.1 E2E `tests/reports.spec.ts`

- 建立使用者＋物品；admin 觸發 `report.monthly`
- `/reports` 顯示上月卡（空動態→「本月無動態」）→ 詳情可見各區塊
- 重跑：清單筆數不變（冪等）
- `/settings/reports` 關閉→以 API 驗證偏好；不同使用者關閉後重跑→不生成
- 桌面統計 dropdown 含報表；行動 drawer 群組收合／導航
- 截圖：桌機＋390（視覺走查另以臨時腳本）

### T3.2 文件收尾

- `docs/scheduling.md`：新增 `report.monthly` 每月 1 日 cron 範例與參數說明
- `CHANGELOG.md`：`alpha.31`（Added／Changed／Tests）
- `docs/v2-roadmap.md`：Phase 31 ✅＋測試規模更新
- 本計畫勾選與 Final Verification 實測記錄

## Final Verification（收尾時填實測）

- [x] API：`uv run pytest -q` → **912 passed**（3:22，含 1592 warnings）
- [x] Web：`pnpm vitest run` → **560 passed（111 檔，18.6s）**；`pnpm typecheck` → 0 error
- [x] api-types 重生成零 diff（`export_openapi.py` ＋ `gen:types` 後 `git status packages/api-types` 空）
- [x] Migration 0023 up／down 演練（Postgres 容器）：`upgrade 0022 → 0023`（`reports` 表建立）→ `downgrade 0023 → 0022` → `upgrade head`；`to_regclass('public.reports')` 有值
- [x] e2e：重建 image（`docker compose build web api && docker compose up -d`）後 `pnpm exec playwright test` → **22 spec／68 passed**（含新 `reports.spec.ts` 3 情境；`navigation.spec.ts` 物品入口改於群組容器內定位）
- [x] 視覺走查：桌機 1440×900＋行動 390×844 截圖人工檢視（`/reports` 週期卡、`/reports/[id]` 區塊卡與估值正負色、`/settings/reports` 開關、桌面「統計」下拉、行動 drawer 四群組展開／收合）——無遮擋或破版
- [x] `git status` 乾淨；ff merge main；worktree／分支移除；`ims-v2` stack 清理

### 收尾環境註記（2026-10-18 起填）

- worktree `.claude/worktrees/phase31-monthly-reports`（分支 `claude/phase31-monthly-reports`）；stack `ims-v2`（nginx :80、`ENABLE_DEV_ROUTES=1`）
- 全套驗證以重建 image 後的 production build 執行；migration 由 API 容器啟動時自動套用（`alembic upgrade head`）
- e2e 前置：月報只計「上一個完整月」的動態，`reports.spec.ts` 以 SQL 將測試物品 `created_at` 回填至該期間（API 無此欄位寫入面）；每次執行皆註冊新使用者，避免 `UNIQUE(user_id, period)` 造成假性跳過
- Email 未實寄（fail-soft）：`PUBLIC_WEB_URL` 未設時信件連結為 `http://localhost:3000`；站內通知與 API 契約以 unit／spec 覆蓋，部署時請於 `.env` 設定實際網址（已寫入 `docs/scheduling.md` 疑難排解）
- 視覺走查腳本為臨時檔（`apps/web/visual-walk.mjs`／`visual-walk2.mjs`），截圖存於暫存目錄，未入版控

## 測試基線（main，Phase 30 完成）

- API：864 passed
- Web：502 passed（99 檔）＋typecheck
- E2E：21 spec／65 情境
