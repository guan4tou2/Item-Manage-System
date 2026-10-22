# Phase 39 — 稽核查詢 UI（篩選、分頁、詳情、CSV 匯出）

- **日期**：2026-10-23
- **狀態**：計畫中（TDD 任務與驗證見下文；Final Verification 收尾時填實測）
- **依據**：`docs/v2-roadmap.md` 下一輪候選 #1（「稽核查詢 UI：後端 audit 資料已在，只缺查詢／篩選頁」）
- **規模**：S–M（API：查詢服務擴充＋列舉值＋CSV；Web：查詢台；e2e：1 spec）
- **契約變更**：`GET /api/admin/audit-logs` 由 `list[AuditLogRead]` 改為**分頁信封**（見 D1）

---

## 目標

`/settings/audit` 目前只是一張「最近 200 筆」的唯讀表：不能篩選、不能翻頁、不知道總數、看不出是誰（只顯示 UUID 前 8 碼）、`meta` 被截斷。本 phase 把它做成**可用的稽核查詢台**：

- 篩選：動作、資源類型、使用者、關鍵字（action／resource_type／resource_id／meta）、日期區間
- 分頁：總數＋上下頁（每頁 50，可到 500）
- 詳情：列內展開 `meta`（格式化 JSON）
- 匯出：以當前篩選條件下載 CSV（UTF-8 BOM，Excel 可直接開）
- 使用者：顯示 email（已刪除帳號 → 明確標示），不再只給 UUID

---

## 範圍

### API

- `GET /api/admin/audit-logs`：新增篩選參數、回傳分頁信封＋列舉值（facets）、`user_email`
- `GET /api/admin/audit-logs/export.csv`：同篩選條件的 CSV 匯出（上限 10,000 列）
- `audit_service`：查詢／計數／列舉值／匯出查詢（皆 admin-only）

### Web

- `components/settings/audit-log-panel.tsx` 改為查詢台（桌機表格＋行動卡片）
- 篩選列（關鍵字 debounce 300ms、動作／資源下拉、日期起訖、清除）
- 分頁列（總數、頁碼、上／下頁）、列展開 `meta`、CSV 匯出
- i18n（zh-TW／en）

### 明確不在本期範圍

- **不擴充稽核覆蓋**：目前僅 5 種 action（`group.member_added`／`group.member_role_changed`／`group.member_removed`／`admin.user.set_active`／`backup.import`）。補登入失敗／物品刪除／權杖建立撤銷／密碼變更列為候選 #4（Phase 40），避免本 phase 同時動 4 個服務與其測試
- 不做「即時 tail」（輪詢／SSE）：手動重整與翻頁已足夠，`staleTime` 30 秒沿用
- 不做儲存查詢／告警規則／匯出排程
- 不改 `audit_logs` 表結構 → **無 migration**
- 不新增 audit 明細頁（用列內展開）

---

## 關鍵設計決策

### D1 列表改為分頁信封（有意的契約變更）

```json
{
  "items": [AuditLogRead...],
  "total": 1234,
  "limit": 50,
  "offset": 0,
  "facets": { "actions": [{"value": "...", "count": 7}], "resource_types": [...] }
}
```

- 理由：分頁 UI 需要 `total`；`list` 無法承載。用 `X-Total-Count` 會讓型別客戶端與快取都變難處理
- 唯一消費者是本倉庫的稽核面板（`audit-log-panel.tsx`）＋既有測試 → 一併改；api-types 會出現**刪除行**，於 CHANGELOG 明確標示
- 替代方案（新增 `/page` 端點保留舊 list）被否決：兩個近似端點長期只會增加維護面

### D2 關鍵字 `q` 的搜尋範圍

- 比對 `action`／`resource_type`／`resource_id`／`meta`（JSON 轉文字），一律 `ILIKE`（SQLite 由 SQLAlchemy 轉 `lower(...) LIKE lower(...)`）
- `meta` 以 `cast(AuditLog.meta, Text)` 比對：SQLite（JSON 存 TEXT）與 PostgreSQL（`jsonb::text`）皆可用 → e2e 在 PG 上會實際驗證
- `q` 長度上限 200，前後空白去除；空字串視同未提供
- 不做全文索引：資料量級（單一家庭／小團隊）不需要；若日後需要再上 GIN/tsvector

### D3 日期區間語意

- 參數 `created_from`／`created_to`：**ISO 8601 datetime**（可帶時區），條件為 `created_at >= from` 且 `created_at < to`
- 由 Web 端把「使用者選的當地日期」換算成 UTC 邊界（`to` 取隔日 00:00 當地 → UTC），避免 UTC 日界造成「今天看不到今天」的錯覺
- `from >= to` → `422 {"detail": "invalid_date_range"}`

### D4 facets 為全域（不受篩選影響）

- `facets.actions`／`facets.resource_types` 以**整表** `GROUP BY` 計算（各取前 50，依 count 遞減、value 遞增）
- 理由：下拉選單要不斷變動才不會「選了 A 之後 B 消失」；代價是每次請求多 2 個聚合查詢（此資料量可接受）
- 動作清單**不寫死**：action 是自由字串，未來新增覆蓋率時 UI 自動長出來

### D5 CSV 匯出

- 欄位：`created_at,user_email,user_id,action,resource_type,resource_id,meta`
- UTF-8 **BOM**（Excel 繁中不亂碼）、`text/csv; charset=utf-8`、`Content-Disposition: attachment; filename="audit-logs-YYYYMMDD.csv"`
- 以標準 `csv` 模組寫入（正確處理逗號／引號／換行）；`meta` 以緊湊 JSON 字串輸出
- 上限 **10,000 列**（`ORDER BY created_at DESC`）；超過即截斷（檔名不變，於計畫與文件註明）
- 僅 admin；未帶篩選＝全表（受上限）

### D6 `user_email` 以 LEFT JOIN 取得

- `AuditLog.user_id` 為 `ON DELETE SET NULL` → 帳號刪除後為 `null`；仍在但查不到（理論上不會）亦為 `null`
- 只回 email，不外洩其他欄位；Web 端 `user_email ?? user_id 前 8 碼`，並以 `t("settings.audit.deletedUser")` 標示 `user_id=null` 的歷史列？→ **不標示**（`user_id=null` 也可能本來就是系統事件），僅顯示「—」
- 實作：`outerjoin(User, User.id == AuditLog.user_id)`，select `(AuditLog, User.email)`

### D7 權限與輸入驗證

- 沿用 `get_current_admin`（非 admin → 403，既有測試已鎖）
- `limit` 1–500（預設 50）、`offset >= 0`、`q <= 200`、`user_id` 需 UUID
- 匯出端點同樣 admin-only；CSV 內容為**伺服器端**產生，不做 HTML 注入處理（純文字下載）

### D8 前端狀態

- React Query：`queryKey: ["admin","audit-logs", filters, offset]`；`placeholderData: keepPreviousData` 避免翻頁白屏
- 篩選變更 → `offset` 歸零；`q` debounce 300ms（本地 `useEffect` ＋ `setTimeout`，不引入新依賴）
- 匯出：`apiFetch(path)` → `blob()` → `URL.createObjectURL` → 觸發下載 → `revokeObjectURL`
- 錯誤：`role="alert"` ＋ 重試按鈕；空結果區分「尚無紀錄」與「篩選無結果」

---

## API 範例

### 列表

```
GET /api/admin/audit-logs?limit=50&offset=0&action=group.member_added
    &resource_type=group&q=alice&created_from=2026-10-01T00:00:00Z&created_to=2026-10-24T00:00:00Z
```

```json
{
  "items": [
    {
      "id": "…",
      "user_id": "…",
      "user_email": "owner@example.com",
      "action": "group.member_added",
      "resource_type": "group",
      "resource_id": "…",
      "meta": {"role": "editor"},
      "created_at": "2026-10-22T08:11:03Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "facets": {
    "actions": [{"value": "admin.user.set_active", "count": 4}],
    "resource_types": [{"value": "user", "count": 4}]
  }
}
```

### 匯出

```
GET /api/admin/audit-logs/export.csv?action=admin.user.set_active
```

```
created_at,user_email,user_id,action,resource_type,resource_id,meta
2026-10-22T08:11:03Z,admin@example.com,…,admin.user.set_active,user,…,{"is_active": false}
```

---

## 資料模型

**無 migration**：沿用 `audit_logs` 既有欄位與索引（`action`／`resource_type`／`resource_id`／`user_id`／`created_at` 皆有索引）。

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：查詢服務（篩選／排序／總數／facets）

- RED：`tests/test_audit_query.py`
  - 篩選 action／resource_type／user_id／q（含 **meta** 命中）／日期區間（含頭不含尾）
  - 排序 `created_at DESC`；`total` 為**篩選後**總數；limit/offset 切片正確
  - facets 為全域（不受篩選影響）且排序為 count desc → value asc
  - `user_email` 隨 JOIN 回傳；`user_id` 為 null → `user_email` null
- GREEN：`audit_service.query_logs`／`audit_service.facets`／`audit_service.list_logs`（保留給內部呼叫或改為薄包裝）

### T1.2 API：列表端點改為信封＋驗證

- RED：`tests/test_audit_log.py` 追加
  - 回傳鍵為 `items/total/limit/offset/facets`；既有「停用帳號」測試改讀 `items`
  - `from >= to` → 422 `invalid_date_range`
  - `limit=0`／`limit=501` → 422；`q` 過長 → 422
  - 非 admin → 403（既有測試保留）
- GREEN：`schemas/audit.py` 新增 `AuditLogPage`／`AuditFacet`／`AuditFacets`；`routes/admin.py` 串接

### T1.3 API：CSV 匯出

- RED：`tests/test_audit_export.py`
  - `content-type` 含 `text/csv`；BOM 開頭；表頭欄位順序
  - 逗號／引號／換行的 `meta` 正確轉義（round-trip 以 `csv.reader` 驗證）
  - 篩選條件生效；上限截斷（以 monkeypatch 小上限驗證）
  - 非 admin → 403
- GREEN：`audit_service.iter_export_rows`＋`routes/admin.py` 的 `export.csv`

### T1.4 api-types 重生成

- 確認新增 `AuditLogPage`／facets，並**明確記錄**列表回應的破壞性變更（api-types 會刪除舊 list 型別關聯）

### T2.1 Web：查詢台元件

- RED：`components/settings/audit-log-panel.test.tsx`（改寫既有）
  - 首次載入帶預設參數（`limit=50&offset=0`）並渲染列（email／動作／資源）
  - 選動作 → 重新請求帶 `action=` 且 `offset=0`；輸入關鍵字 → debounce 後才請求（fake timers）
  - 分頁：下一頁帶 `offset=50`；總數顯示；首／末頁按鈕停用
  - 展開列顯示格式化 JSON；`meta=null` → 「—」
  - 匯出：點擊後以當前篩選請求 `export.csv` 並觸發下載（mock `URL.createObjectURL`）
  - 空結果（有篩選）／尚無資料（無篩選）文案不同；錯誤 → `role="alert"`
  - 行動版卡片存在（`data-testid="audit-card"`）
- GREEN：`audit-log-panel.tsx` 改寫（沿用 `Table`／`Select`／`Input`／`Button`／`Skeleton`）

### T2.2 Web：i18n

- RED：`lib/i18n/messages.test.ts` 追加 Phase 39 鍵清單＋未使用鍵檢查（`settings.audit.*`）
- GREEN：zh-TW／en 逐鍵插入（**用精準編輯，不用 JSON 重寫**——Phase 38 教訓：重寫會破壞單行物件格式）

### T3.1 e2e

- `tests/audit-query.spec.ts`（chromium）
  1. 管理員：建立群組＋變更成員角色 → 開 `/settings/audit` → 看得到 `group.member_role_changed` → 以動作篩選後只剩該動作 → 匯出 CSV 觸發下載
  2. 非管理員：看不到稽核面板（`AdminOnly` 提示），直接打 API 得 403
- 不新增 `ai-stub` 情境（與 AI 無關）

### T3.2 文件

- `docs/` 補稽核查詢章節（`docs/settings.md` 或既有對應文件；先確認落點）
- `CHANGELOG.md`：`alpha.39`
- `docs/v2-roadmap.md`／`docs/progress-2026-10-22.md`：更新
- 本計畫 Final Verification 填實測

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| 契約變更讓舊消費端壞掉 | 唯一消費者在repo內，同 commit 改；CHANGELOG 標示破壞性變更；api-types 重生成後全庫 typecheck |
| `cast(meta, Text)` 在 SQLite／PG 行為不同 | 兩邊都測：pytest（SQLite）＋ e2e（PG）各驗一次 meta 命中 |
| 匯出大量資料拖垮 API | 上限 10,000 列＋`ORDER BY created_at DESC`（走索引）；不使用串流（單次 `Response` 即可） |
| 每次請求多 2 個 facets 聚合 | 資料量小；必要時再加快取（本 phase 不做） |
| debounce 造成測試不穩 | 測試用 fake timers；元件內 debounce 僅作用於 `q`，下拉／日期立即生效 |
| 日期時區錯位 | 前端以當地日界換算 UTC，後端只做 `>= / <` 比較；測試涵蓋跨日邊界 |
| 稽核事件太少，頁面看起來空 | 已知並記錄：覆蓋擴充為候選 #4；本期 UI 以 facets 動態呈現現有事件 |

---

## Final Verification（收尾時填實測）

- [ ] API：`uv run pytest -q` → 實測
- [ ] Web：`pnpm vitest run` ＋ `pnpm typecheck` → 實測
- [ ] api-types 重生成 → 差異僅預期項目（新增 Page／facets；列表回應變更）
- [ ] e2e（chromium）→ 實測
- [ ] 視覺走查（1440×900＋390×844）：篩選列、表格、展開 meta、分頁、行動卡片
- [ ] `git status` 乾淨；ff merge main；worktree／分支／stack 清理

---

## 測試基線（main，Phase 38 完成）

- API：1161 passed
- Web：752 passed（132 檔）
- E2E：28 spec／89 情境（chromium 85＋ai-stub 4）
