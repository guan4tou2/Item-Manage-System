# Phase 40 — 稽核覆蓋擴充（登入、物品刪除、權杖、密碼）

- **日期**：2026-10-23
- **狀態**：✅ 已完成（2026-10-23；實測見 Final Verification）
- **依據**：`docs/v2-roadmap.md` 下一輪候選 #3（「稽核覆蓋擴充：目前僅 5 種 action」）
- **規模**：S–M（API：7 個新 action＋1 個節流輔助；**無 migration、無 Web 改動**；e2e：既有 spec 加 1 個斷言）
- **契約變更**：無（純新增寫入事件；`GET /api/admin/audit-logs` 契約不變，facets 會自然多出新值）

---

## 目標

Phase 39 把稽核查詢台做完了，但資料庫只記得到 **5 種 action**（群組成員 ×3、停用帳號、備份匯入），查詢台再強也看不到「誰登入、誰刪了東西、誰發了權杖、誰改了密碼」。本 phase 把**安全相關、事後追查有價值**的事件補進 `audit_logs`：

| 新 action | 觸發點 | resource_type | meta |
|---|---|---|---|
| `auth.login` | 密碼登入成功 | `user` | 無 |
| `auth.login_failed` | 密碼登入失敗（**僅既有帳號、10 分鐘去重**） | `user` | `{"username": ...}` |
| `item.deleted` | 單筆軟刪 | `item` | `{"name": ...}` |
| `item.bulk_deleted` | 批次軟刪 | `item` | `{"count": n, "item_ids": [...]}` |
| `token.created` | 建立 PAT | `api_token` | `{"name": ...}` |
| `token.deleted` | 撤銷 PAT | `api_token` | `{"name": ...}` |
| `user.password_changed` | 本人變更密碼 | `user` | 無 |

完成後共 **12 種 action**。UI **零改動**：Phase 39 的動作／資源下拉由 facets 動態產生，新事件自動出現；`auth.login` 這類高頻事件也會讓查詢台馬上有真實資料可看。

---

## 範圍

### API

- `audit_service`：新增 `log_login_failure()`（含時間窗去重）與常數 `LOGIN_FAILURE_DEDUP_WINDOW`；既有 `log()` 介面不變
- `routes/auth.py`：登入成功／失敗各記一筆
- `services/auth_service.py`：新增 `get_user_by_username()`（失敗時判斷帳號是否存在）
- `services/items_service.py`：`delete_item`／`bulk_delete_items`
- `services/api_tokens_service.py`：`create_token`／`delete_token`（刪除前先取 `name`）
- `services/profile_service.py`：`change_password`

### 測試

- 新增 `apps/api/tests/test_audit_coverage.py`（每個 action 的正向／反向案例＋敏感值禁記＋登入失敗節流）
- 既有稽核測試（Phase 39）確認不受 `auth.login` 新資料影響（測試皆以 `action=` 篩選，預期不需改）
- e2e：`apps/web/tests/audit-query.spec.ts` 增加 1 個斷言，確認 `auth.login` 自動出現在動作下拉（證明「零 UI 改動」成立）

### 文件

- `FEATURES.md`：稽核章節由「5 種 action」改為 12 種並分組
- `CHANGELOG.md`：`2.0.0-alpha.40`
- `docs/v2-roadmap.md`：完成表新增 Phase 40、候選清單移除 #3 並重編號
- `docs/progress-2026-10-23.md`：新增本日進度（基線、決策、已知限制）

### 明確不在本期範圍

- **不改 `audit_logs` 表結構**（不加 IP／User-Agent／severity 欄位）→ **無 migration**
- **不加 Web UI**：facets 動態已足夠；不做事件圖表／告警／即時 tail
- **不做登入 rate limit**（帳號鎖定／CAPTCHA／Redis 滑動視窗）：那是獨立的認證強化，本 phase 只做「稽核寫入不成為新的洪水面」
- **不記 `backup.export`**（理由見 D7）
- 不補「物品建立／更新」「清單／標籤／位置」等 CRUD 事件：數量暴增、追查價值低於上述 7 種，留待有需求再開
- 不記 `item.*` webhook 的既有事件（那是 webhook，不是稽核）

---

## 關鍵設計決策

### D1 事件命名與 resource_type

沿用既有 `動詞.受詞` 風格（`admin.user.set_active`、`backup.import`）：

- `auth.login`／`auth.login_failed` → `resource_type="user"`、`resource_id=str(user.id)`
- `item.deleted`／`item.bulk_deleted` → `"item"`、單筆為 item id，批次為 `null`（詳見 D6）
- `token.created`／`token.deleted` → `"api_token"`、token id
- `user.password_changed` → `"user"`、本人 id

`action` 欄位長度上限 80、`resource_type` 40，全部遠低於上限。`user_id` 一律是**行為人**：登入事件是本人；管理員操作他人時是管理員（沿用既有 `admin.user.set_active` 語意）。

### D2 敏感值禁記（硬規則）

`meta` **永遠不得**包含：密碼（明文／雜湊）、PAT 原文、PAT 雜湊、refresh token、任何 `*_hash` 欄位。本 phase 的 meta 只有：

- 物品 `name`（刪除後就查不到，必須留在稽核）
- 權杖 `name`（人類可讀標籤，非憑證）
- 批次刪除的 `count`／`item_ids`

測試會把整個 row 序列化成字串，斷言原始 token 字串、`password`、`secret`、`token_hash` 皆不出現；權杖建立測試會拿回應中的 `token` 原文去比對稽核內容。

### D3 登入失敗：只記既有帳號＋10 分鐘去重（防洪水）

`POST /api/auth/login` **目前沒有任何 rate limit**，而且 `AuthService.authenticate` 對「帳號不存在」與「密碼錯誤」都丟同一個 `InvalidCredentials`（不明確區分，這是正確的對外行為）。若照直覺「每次失敗都寫一筆」：

- 匿名攻擊者可用隨機帳號灌爆 `audit_logs`（無上限寫入 → 儲存體 DoS），且每一筆都無追查價值
- 對既有帳號的暴力破解也會產生大量列，把真正的事件淹掉

對策（本 phase 定案）：

1. **只記既有帳號**：登入失敗後以 `get_user_by_username()` 查一次；查不到 → **完全不寫**（不記錄陌生帳號，同時降低帳號列舉的旁路訊號）
2. **同一帳號 10 分鐘內只記第一筆**：`log_login_failure()` 先查 `action="auth.login_failed" AND resource_id=<user.id> AND created_at >= now-10min`，有就跳過
3. 去重查詢失敗時**寧可不寫**（fail-soft，不影響登入回應）
4. 對外回應完全不變：一律 `401 invalid credentials`

代價：每次「既有帳號的失敗登入」多 1 次 SELECT（bcrypt 驗證本來就是主要成本），且**不會**因為攻擊而線性增加資料列；極端情況下每個帳號每小時最多 6 列。成功登入不節流（需有效憑證，無法匿名濫用）。

> 為何不用 Redis／記憶體計數器：本專案執行多 worker，記憶體計數不共享；引入 Redis 只為了一個稽核節流不划算。DB 去重查詢已足夠，且與稽核資料同源（重啟不歸零）。

### D4 成功登入也記（`auth.login`）

- 價值：補上「帳號被使用」的時間線；與 `auth.login_failed` 成對，能看出「先失敗多次、後來成功」
- 噪音：只有真正打密碼的登入才會記；`/api/auth/refresh` **不記**（access token 過期會自動續，記了會變成每 15 分鐘一列）
- 不記 IP／User-Agent：表沒有欄位，且會牽涉隱私與 proxy 信任問題；列為未來候選
- 成功登入失敗（`log()` 例外）不影響登入：`log()` 本來就是 fail-soft

### D5 交易邊界：呼叫點一律放在主寫入 commit 之後

`audit_service.log()` 會 `session.commit()`。若插在主交易中間，會提前把其他未完成的變更一起提交（部分成功）。本 phase 的所有呼叫點都遵守：

1. `delete_item`：`soft_delete()`（內部 commit）→ 稽核 → webhook dispatch
2. `bulk_delete_items`：批次 commit → 稽核 → 逐筆 webhook dispatch
3. `create_token`：commit + refresh → 稽核
4. `delete_token`：刪除 commit → 稽核
5. `change_password`：commit → 稽核
6. `login`／`login_failed`：本身無寫入，直接記

稽核寫入失敗**不阻擋**主流程（既有 fail-soft 行為），但順序上要讓「主資料已落地」先成立。物品／權杖的稽核放在 webhook **之前**：webhook dispatch 可能涉及外部 HTTP，不能讓稽核等它。

### D6 批次刪除：一筆摘要列，不逐筆記

- 一次 API 呼叫只寫 **1 列** `item.bulk_deleted`：`meta={"count": n, "item_ids": [...]}`（schema 上限 100 筆，最壞約 3.7 KB，可接受）
- 不記 `names`：100 個長名稱會讓單列膨脹，且名稱可由 id 在刪除前的備份／匯出追溯
- 單筆刪除仍記 `{"name": ...}`：這是事後唯一還看得到名稱的地方
- 若 100 筆全部刪除，`count=100`；不做「逐筆 item.deleted + 一筆 bulk」的雙寫（會讓事件數翻倍、失去「這是一次操作」的語意）

### D7 `backup.export` 不納入本期

- `GET /api/backup/export` 是**本人匯出自己可見的資料**，不是跨使用者提權；每次匯出都是一份完整 JSON，記了會變成高頻噪音
- 真正需要追查的是「異常大量匯出」，那需要速率／量體基準，屬告警功能，不是單列事件能解決
- 若未來加入「管理員匯出他人資料」或分享連結，再以獨立 action 記錄

### D8 UI 零改動，但 facets 會變長

- 下拉選項來自資料庫 facets（每維度前 50），新 action 自動出現；`auth.login` 很快會成為 count 最高的值之一
- 既有 e2e 以 `admin.user.set_active` 篩選，不受影響；新增 1 個斷言確認 `auth.login` 出現在下拉
- `resource_types` 會多出 `item`／`api_token`，無需 i18n（目前顯示原始字串）

### D9 登入失敗的查詢位置

在 `routes/auth.py` 的 `except InvalidCredentials` 內查詢，而不是改 `authenticate()` 的回傳契約：

- `authenticate()` 維持「失敗就是同一種錯」，避免未來有人不小心把「帳號不存在」洩漏到 API
- 只有在失敗路徑才多查一次使用者，成功路徑零額外成本
- `get_user_by_username()` 只是 `UserRepository.get_by_username` 的薄包裝，供路由使用

---

## 資料流

```
POST /api/auth/login
  ├─ ok ──► issue tokens ──► audit.log(auth.login)  [fail-soft]
  └─ InvalidCredentials
        ├─ get_user_by_username(payload.username)
        ├─ 不存在 ──► 401（不寫稽核）
        └─ 存在 ──► log_login_failure(user.id)
                      ├─ 10 分鐘內已有 ──► 跳過
                      └─ 無 ──► audit.log(auth.login_failed)
                    ──► 401

DELETE /api/items/{id}
  └─ soft_delete(commit) ──► audit.log(item.deleted) ──► webhook item.deleted

POST /api/items/bulk-delete
  └─ 批次 commit ──► audit.log(item.bulk_deleted) ──► webhook ×n

POST /api/users/me/api-tokens
  └─ commit+refresh ──► audit.log(token.created)

DELETE /api/users/me/api-tokens/{id}
  └─ 取出 name（404 則結束）──► delete commit ──► audit.log(token.deleted)

POST /api/users/me/change-password
  └─ 驗舊密碼（錯 → 422，不記）──► 更新雜湊 commit ──► audit.log(user.password_changed)
```

---

## 任務（TDD：每項先 RED 再 GREEN）

### T1.1 API：稽核服務節流輔助

- `audit_service.LOGIN_FAILURE_DEDUP_WINDOW = timedelta(minutes=10)`
- `log_login_failure(session, *, user_id, username) -> bool`
- RED：時間窗內第二筆不寫、窗外（以種子列 `created_at=now-11min`）可再寫、查詢例外時不寫且不拋

### T1.2 API：登入成功／失敗

- `AuthService.get_user_by_username()`
- `routes/auth.py`：成功後 `auth.login`；失敗時僅既有帳號寫 `auth.login_failed`
- RED：成功 1 列（`resource_id` 為本人）、錯密碼 1 列且**第二次不增列**、陌生帳號 0 列、對外皆 401、停用帳號的失敗嘗試也只記 1 列且不登入

### T1.3 API：物品刪除

- `items_service.delete_item`／`bulk_delete_items`
- RED：單筆 meta 有 name、批次 meta 有 count 與 item_ids 且無 names、別人的物品 404 不寫、批次上限 100 仍只寫 1 列

### T1.4 API：權杖建立／撤銷

- `api_tokens_service.create_token`／`delete_token`（改為先取列、再刪）
- RED：建立記 `name` 且**不得**出現回應中的 token 原文或 `token_hash`、撤銷記 name、撤銷他人／不存在 → 404 且 0 列

### T1.5 API：密碼變更

- `profile_service.change_password`
- RED：成功 1 列、舊密碼錯誤 422 且 0 列、稽核內容不含任何密碼欄位

### T2.1 回歸：既有稽核測試

- 確認 Phase 39 測試（`test_audit_log.py`／`test_audit_query.py`／`test_audit_export.py`）不因登入事件改變結果（皆以 action 篩選；若有全域計數則改為相對比較）

### T3.1 e2e：新事件自動出現在下拉

- `apps/web/tests/audit-query.spec.ts`：開動作下拉時斷言 `auth.login` 存在（e2e 流程本身已登入，必有此列）

### T3.2 文件

- `FEATURES.md` 稽核章節：12 種 action 分組（認證／物品／權杖／群組／管理／備份）
- `CHANGELOG.md` alpha.40
- `docs/v2-roadmap.md`：完成表＋候選重編號
- `docs/progress-2026-10-23.md`
- 本計畫 Final Verification

---

## 測試清單（RED 先寫）

| # | 測試 | 期望 |
|---|---|---|
| 1 | 登入成功 | 1 列 `auth.login`，`user_id`＝本人 |
| 2 | 既有帳號錯密碼 ×2（同時窗） | 只有 1 列 `auth.login_failed`，對外皆 401 |
| 3 | 陌生帳號錯密碼 ×3 | 0 列稽核，對外皆 401 |
| 4 | 窗外再失敗一次 | 第 2 列出現（種子列 11 分鐘前） |
| 5 | 停用帳號錯密碼 | 1 列（行為人為該帳號）、不發 token |
| 6 | 單筆刪除 | `item.deleted`＋`meta.name` |
| 7 | 批次刪除 3 筆 | 1 列 `item.bulk_deleted`、`count=3`、`item_ids` 3 個、無 `names` |
| 8 | 刪他人物品 | 404、0 列 |
| 9 | 建立權杖 | `token.created`、meta.name、**無 token 原文／雜湊** |
| 10 | 撤銷權杖 | `token.deleted`、meta.name |
| 11 | 撤銷不存在權杖 | 404、0 列 |
| 12 | 變更密碼 | `user.password_changed`、無密碼欄位 |
| 13 | 舊密碼錯誤 | 422、0 列 |
| 14 | 整列序列化 | 不含 `password`／`secret`／`token_hash`／PAT 原文 |

---

## 風險與對策

| 風險 | 影響 | 對策 |
|---|---|---|
| 登入失敗遭匿名灌寫 | `audit_logs` 暴增、儲存體壓力 | 只記既有帳號＋10 分鐘去重（D3）；陌生帳號完全不寫 |
| 去重查詢拖慢登入 | 失敗登入延遲增加 | 單一 indexed 查詢（`action`／`resource_id`／`created_at` 皆有索引），且只在失敗路徑 |
| `log()` 的 commit 提前提交未完成變更 | 部分成功 | 所有呼叫點放在主寫入 commit 之後（D5） |
| 稽核寫入失敗阻擋主流程 | 刪除／改密碼失敗 | 沿用 `log()` fail-soft；測試以 monkeypatch 讓 insert 拋錯，確認主流程仍成功 |
| 敏感資料寫進 meta | 憑證外洩到稽核頁／CSV | D2 硬規則＋測試 9／12／14 序列化比對 |
| 時區比較錯誤（SQLite naive／PG aware） | 去重失效 | cut-off 一律用 `_utcnow()`（aware）；測試涵蓋 SQLite，PG 另做煙霧測試 |
| 既有測試因新事件計數改變 | 假紅 | T2.1 逐一確認；必要時改為相對比較 |
| e2e 對 facets 假設過強 | flake | 只斷言 `auth.login` 存在，不斷言排序／完整集合 |

---

## 實作結果（與計畫差異）

- **登入失敗的 meta 多了 `username`**（計畫原為「無」）：使用者日後改名時仍能回溯「當時嘗試的名稱」；非敏感值，且稽核頁僅管理員可見
- **`token.deleted` 由 bulk DELETE 改為「先 SELECT 取 name → ORM delete → commit」**：需要名稱才能記錄；不存在／非本人的 token 仍是 404 且不寫稽核
- **e2e 不新增 spec**：只在既有 `audit-query.spec.ts` 加 1 個斷言（`auth.login` 出現在動作下拉）；沒有新增檔案，chromium 情境數不變
- **測試數 14**（與測試清單一致）；新增 `test_audit_coverage.py`，其餘測試零修改
- **`audit_service` 新增 `LOGIN_FAILURE_DEDUP_WINDOW`／`log_login_failure()`**；`log()` 介面與 fail-soft 行為未變
- **無 migration、無 Web 改動、api-types 零 diff**（OpenAPI schema 未變）

---

## Final Verification（2026-10-23 實測）

| 項目 | 結果 |
|------|------|
| API 測試 | **1206 passed**（`uv run pytest -q`；含新增 14 個） |
| API golden eval | 28 passed／1 skipped |
| Web 測試 | **765 passed（132 檔）**（無改動，回歸確認） |
| Web typecheck | **0 error** |
| api-types | **零 diff**（`export_openapi.py` ＋ `gen:types`） |
| e2e chromium | **87 passed**（`--workers=1`） |
| e2e ai-stub | 4 passed（沿用） |
| Migration | `0025 (head)`；本 phase 無 migration |
| PostgreSQL 實測 | 去重 2 次失敗 → 1 列；`item.deleted`／`token.created`／`token.deleted`／`user.password_changed` meta 正確；token 原文未落地；`meta` 為 JSONB 物件 |
| fail-soft | 以壞掉的 `AuditLog` 建構子驗證：稽核失敗仍可刪除物品（204） |

---

## 測試基線（main，Phase 39 完成）

- API：**1192 passed**（pytest-asyncio／aiosqlite；golden eval 28 passed／1 skipped）
- Web：**765 passed**（132 檔；vitest＋Testing Library）
- typecheck：0 error
- e2e：chromium **87 passed**（`--workers=1`）；ai-stub 4 passed
- Migration：`0025 (head)`；本 phase **無 migration**
- 既有 audit action：5 種
