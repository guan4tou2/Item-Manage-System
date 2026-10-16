# 排程與到期提醒

IMS v2 的排程採「**外部 cron ＋ 冪等 job 端點**」：應用本身不內建排程器（`apscheduler` 已於 Phase 24 移除），由你既有的排程工具（crontab／systemd timer／GitHub Actions／任何能發 HTTP 的機制）每日呼叫一次端點即可。

- **冪等**：同日重跑不會重複發送提醒；補跑、手動觸發、排程器重試都安全
- **可觀測**：每次執行寫入 `job_runs`；設定頁「提醒排程」（`/settings/reminders`）顯示上次執行與停跑警示
- **第一號 job**：`expiry-scan`（批次到期掃描與摘要提醒）；Phase 31 的月報表會沿用同一機制

> 目前僅 `expiry-scan` 一個 job；`{job_name}` 換成未知名稱一律 404。

---

## 三分鐘上手

### 1. 建立管理員 PAT

`POST /api/jobs/{job_name}/run` 需要**管理員**身分。以管理員帳號登入後：

1. 前往 **設定 → API Tokens**（`/settings/tokens`）
2. 輸入名稱（例如 `cron-expiry`）→「建立 Token」
3. **立即複製 Token**（只會顯示這一次）

### 2. 設定環境變數

```bash
export IMS_BASE_URL="https://ims.example.com"   # 你的站台網址
export IMS_PAT="ims_pat_xxxxxxxxxxxxxxxx"       # 步驟 1 的 Token
```

### 3. 設定 cron（每日台北時間 09:00）

```cron
0 9 * * * curl -fsS -X POST "$IMS_BASE_URL/api/jobs/expiry-scan/run" -H "Authorization: Bearer $IMS_PAT"
```

（crontab 的時區依主機設定；請確認主機時區為 Asia/Taipei，或改用下方 systemd／GitHub Actions 範例。）

### 4. 驗證

```bash
# 立即手動觸發一次（補跑安全）
curl -fsS -X POST "$IMS_BASE_URL/api/jobs/expiry-scan/run" -H "Authorization: Bearer $IMS_PAT"

# 查詢狀態（任何登入者皆可）
curl -fsS "$IMS_BASE_URL/api/jobs/expiry-scan/status" -H "Authorization: Bearer $IMS_PAT"
```

也可以直接在 UI 檢查：**設定 → 通知與提醒 → 提醒排程**。剛觸發過應顯示「成功」＋時間；超過 26 小時未執行會出現停跑警示與 cron 片段。

---

## 排程範例

### crontab

```cron
# 每日台北時間 09:00 執行到期掃描
0 9 * * * curl -fsS -X POST "$IMS_BASE_URL/api/jobs/expiry-scan/run" -H "Authorization: Bearer $IMS_PAT"
```

### systemd timer

`/etc/ims/scheduling.env`（權限建議 `600`）：

```bash
IMS_BASE_URL=https://ims.example.com
IMS_PAT=ims_pat_xxxxxxxxxxxxxxxx
```

`/etc/systemd/system/ims-expiry-scan.service`：

```ini
[Unit]
Description=IMS 到期掃描（expiry-scan）
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/ims/scheduling.env
ExecStart=/bin/sh -c 'curl -fsS -X POST "$IMS_BASE_URL/api/jobs/expiry-scan/run" -H "Authorization: Bearer $IMS_PAT"'
```

`/etc/systemd/system/ims-expiry-scan.timer`：

```ini
[Unit]
Description=每日執行 IMS 到期掃描

[Timer]
OnCalendar=*-*-* 09:00:00 Asia/Taipei
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ims-expiry-scan.timer
systemctl list-timers ims-expiry-scan.timer   # 確認下次執行時間
```

### GitHub Actions

```yaml
name: ims-expiry-scan
on:
  schedule:
    - cron: "0 1 * * *" # UTC 01:00＝台北 09:00；GitHub 排程以 UTC 計
  workflow_dispatch: {} # 可手動補跑（端點冪等，安全）
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: 觸發到期掃描
        run: |
          curl -fsS -X POST "${{ secrets.IMS_BASE_URL }}/api/jobs/expiry-scan/run" \
            -H "Authorization: Bearer ${{ secrets.IMS_PAT }}"
```

> GitHub 的 `schedule` 可能延遲數分鐘至數十分鐘；到期提醒以「日」為粒度，延遲無妨。需要精準時間請用 crontab／systemd timer。

---

## 端點參考

### `POST /api/jobs/{job_name}/run`（管理員）

觸發一次執行；回傳本次結果。

```json
{ "job": "expiry-scan", "status": "succeeded", "processed": 3, "emitted": 2 }
```

- `status`：`succeeded`／`failed`（部分使用者失敗時為 `failed`，詳見 `GET status` 的 `result.errors`）
- `processed`：本次新建的到期標記（`expiry_alerts`）列數
- `emitted`：本次發出的用戶摘要數（通道過濾在偏好層處理，見下）

| 狀態碼 | 情境 |
|--------|------|
| 401 | 未帶 Token／Token 無效 |
| 403 | 已登入但非管理員 |
| 404 | 未知 `job_name` |

### `GET /api/jobs/{job_name}/status`（任何登入者）

```json
{
  "job": "expiry-scan",
  "thresholds": { "stale_after_hours": 26, "advance_days": [30, 7, 0], "expired_stop_days": 14 },
  "last_run": {
    "status": "succeeded",
    "started_at": "2026-10-16T01:00:03Z",
    "finished_at": "2026-10-16T01:00:05Z",
    "result": { "processed": 3, "emitted": 2, "errors": [] }
  },
  "stale": false
}
```

- `stale`：從未執行，或最近一次執行開始時間已逾 `stale_after_hours`（26 小時）→ `true`（設定頁據此顯示停跑警示）
- `last_run`：`null` 表示從未執行過

---

## 行為語義（`expiry-scan`）

- **時區**：所有門檻判斷以 **Asia/Taipei 的「今天」** 為準（與全站到期顯示一致）
- **門檻與級別**（每批次）：
  - `d30`／`d7`／`d0`：剩餘天數首次落入 `≤30`／`≤7`／`==0` 時各提醒**一次**（上線初期既有批次會一次補齊；之後不重發）
  - `expired`：過期後**每日**一則，至過期 14 天（`days_left ≥ -14`）止；之後停止推播，物品仍留在站內列表與篩選
- **冪等**：每個（批次 × 級別 × 日期）只記錄一次；同日重跑不重發。重跑僅補「先前失敗而未送出」的差額
- **摘要制**：每位使用者每日每類型最多一則彙總（例如「3 件物品即將到期」＋最急的品名與天數），不會逐批轟炸；通知附 deep link 直達到期檢視
- **偏好過濾**：尊重「設定 → 通知偏好」的設定（Phase 23）；`expiring_soon` 與 `expired` 的 **Email／LINE／Telegram 預設為關**，需要時請至 `/settings/notifications` 開啟（站內與瀏覽器推播預設開）
- **失敗語義**：逐使用者隔離——某位使用者的提醒失敗不影響其他人；`status=failed` 時已寫入的提醒保留，直接重跑即可補齊
- **停跑觀測**：排程器未設定或連續失敗時，`stale` 於 26 小時後轉 `true`，設定頁出現警示

---

## 疑難排解

| 症狀 | 可能原因 | 處置 |
|------|----------|------|
| `401` | Token 無效、被刪除或未帶 `Authorization` | 於 `/settings/tokens` 重新建立 |
| `403` | Token 所屬帳號不是管理員 | 以管理員帳號建立 Token（系統首位註冊者可於 `/settings` 取得管理員） |
| `404` | `job_name` 拼錯 | 目前僅 `expiry-scan` |
| 站內完全沒有提醒 | 使用者關閉了站內偏好；或該使用者沒有符合門檻的批次 | 檢查 `/settings/notifications` 與物品到期日 |
| 站內有、Email 沒有 | `expiring_soon`／`expired` 的 Email 預設為關 | 於 `/settings/notifications` 開啟 |
| Email／LINE／Telegram／推播沒收到 | 管道未綁定 | 於 `/settings/channels` 完成綁定 |
| 設定頁出現停跑警示 | cron 未設定、主機時區錯誤或排程器失敗 | 依上方範例設定，並以手動觸發驗證 |
| 提醒重複 | 幾乎不會：同（批次 × 級別 × 日期）有唯一鍵防護 | 若仍發生請回報，附 `GET status` 的 `last_run.result` |
