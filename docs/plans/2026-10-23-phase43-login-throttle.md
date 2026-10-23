# Phase 43：登入防暴力破解（帳號＋來源 IP 分級鎖定）

- **狀態**：🚧 進行中
- **日期**：2026-10-23
- **基線**：`main` `d9cc1a3`（Phase 42）；API 1248 passed、Web 787 passed（132 檔）、e2e 89 passed、Migration `0026 (head)`
- **依賴**：無新套件；使用既有 SQLAlchemy／PostgreSQL（測試為 SQLite）

---

## 目標

讓 `POST /api/auth/login` 在憑證錯誤時不再可以無限次嘗試：

1. **帳號分級鎖定**：同一帳號短時間內連續失敗 → 暫時拒絕登入；持續嘗試則鎖定時間拉長。
2. **來源 IP 分級鎖定**：同一來源大量失敗 → 暫時拒絕，降低跨帳號噴射（password spraying）。
3. **對外不揭露帳號是否存在**：存在／不存在、帳號被鎖／IP 被鎖都使用同一個 `429 too many login attempts`。
4. **不影響正常登入**：成功登入不計數，且會清除該帳號的失敗紀錄。
5. **可觀測、可測試**：`Retry-After` 標頭、Web 明確文案、完整單元／路由／e2e 測試。

---

## 範圍

### API

- 新增 `app/models/login_attempt.py`：
  - `login_attempts(id, kind, key_hash, created_at)`
  - `kind`：`account`／`ip`
  - `key_hash`：HMAC-SHA256（不存原始使用者名稱或 IP）
  - 索引：`(kind, key_hash, created_at)`、`created_at`
- 新增 `app/services/login_throttle_service.py`：
  - `check(session, username, ip) -> ThrottleStatus`
  - `record_failure(session, username, ip)`
  - `reset_account(session, username)`
  - 分級門檻、`Retry-After` 計算、24 小時清理、fail-soft
- `app/routes/auth.py`：
  - 登入前先 `check()`；被鎖 → `429`＋`Retry-After`，**不執行密碼驗證**
  - `InvalidCredentials` → `record_failure()`（帳號＋IP 各一列）→ 既有稽核 → `401`
  - 成功 → `reset_account()`（只清帳號，不清 IP）→ 發 token
  - OpenAPI 標註 `429`
- `app/services/auth_service.py`：
  - 帳號不存在時仍對固定的 dummy Argon2 hash 驗一次密碼，降低 timing 帳號列舉
- `docker-compose.yml`：
  - uvicorn 加 `--proxy-headers --forwarded-allow-ips=*`，讓 `request.client.host` 取得 nginx 後方的真實來源 IP
  - API 仍只以 `expose` 對內，不直接對外；文件中註明直接暴露 API 時不可信任 forwarded headers

### Web

- `features/auth/login-form.tsx`：`429` 顯示「嘗試次數過多，請稍後再試」，其餘錯誤維持「帳號或密碼錯誤」
- `messages/zh-TW.json`／`en.json`：新增 `login.tooManyAttempts`
- 新增 `features/auth/login-form.test.tsx`：429／401 文案分流
- `tests/login.spec.ts`：真實流程——連續 5 次錯密碼後第 6 次顯示鎖定文案；鎖定期間正確密碼也被拒絕

### 測試

- **Service**
  - HMAC key 穩定、長度 64、不同 kind 不碰撞、不含原始字串
  - 帳號 5 次／15 分鐘 → 封鎖；`Retry-After` 為正整數且 ≤ 15 分鐘
  - 帳號 10 次／1 小時、15 次／24 小時的較長分級
  - 成功登入清除帳號紀錄；IP 紀錄不被成功登入清除
  - 封鎖期間不再寫入新嘗試（避免無限延長）
  - 窗外舊紀錄不封鎖；24 小時前紀錄會被清理
  - 未知帳號與既有帳號走同一條鎖定路徑
  - IP 10 次／1 分鐘、30 次／15 分鐘分級
  - DB 查詢／寫入失敗時 fail-soft（不讓登入變成 500）
- **Route**
  - 5 次錯密碼 → 第 6 次 `429`＋`Retry-After`；此時正確密碼仍 `429`
  - 其他帳號不受影響
  - 未知帳號 5 次後同樣 `429`（不列舉）
  - 成功登入後可重新累積（帳號計數已重置）
  - 既有 `401 invalid credentials`、refresh cookie、稽核行為不回歸
- **Web**
  - `LoginForm` 429／401 文案
  - e2e 真實鎖定流程
- **Migration**
  - SQLite 以 `create_all` 覆蓋新表
  - 獨立 PostgreSQL 容器：`0026 → 0027 → 0026 → 0027`

### 文件

- `CHANGELOG.md` alpha.43
- `FEATURES.md` 新增「認證與登入防護」章節
- `docs/v2-roadmap.md`：Phase 43 完成列、候選 #8 移除、測試規模更新
- `docs/progress-2026-10-23.md`：更新為 Phase 40–43
- 本計畫：實作結果、Final Verification、測試基線

### 明確不在本期範圍

- CAPTCHA／MFA／WebAuthn
- 註冊、refresh、忘記密碼端點的 rate limit（登入是主要暴力破解面）
- 管理員解鎖 UI、帳號解鎖通知、封鎖事件告警
- 以 Redis 做滑動視窗（本專案 DB 已是必要依賴；多 worker 共享且重啟不歸零）
- 記錄原始 IP／User-Agent 到稽核表（隱私與 schema 變更；本 phase 只存 HMAC）
- 帳號列舉的完整 timing 防護（只做登入密碼驗證的 dummy hash；網路層 timing 不在範圍）

---

## 關鍵設計決策

### D1 只計「失敗」，不計成功與被封鎖的嘗試

`slowapi` 這類 route-level limiter 會在密碼驗證前計數，成功登入也會被算進去；本專案 e2e／NAT 共享 IP 會很容易誤鎖。因此改在 `InvalidCredentials` 之後才寫入失敗紀錄：

- 成功登入：不新增任何列，並刪除該帳號的失敗列
- 被封鎖的請求：直接回 `429`，**不再新增列**（否則攻擊者可持續延長受害者鎖定）
- 格式錯誤（422）／其他端點：不計數

### D2 帳號分級鎖定

| 門檻 | 觀察窗 | 鎖定時間 |
|------|--------|----------|
| 5 次 | 15 分鐘 | 15 分鐘 |
| 10 次 | 1 小時 | 30 分鐘 |
| 15 次 | 24 小時 | 1 小時 |

- 同一帳號（以 `username.strip()` 精確比對，不大寫折疊）為 key
- 每次 `check()` 取最近 24 小時的紀錄，逐級計算：
  - 該窗內失敗數 ≥ 門檻
  - 且「第 N 新的一筆 + 鎖定時間」仍大於現在 → 封鎖
  - 多級取最晚的解鎖時間
- 第 5 次失敗本身仍回 `401`；第 6 次起回 `429`（憑證真的錯了，先讓使用者知道）
- 帳號名稱不存在也照樣計數，避免用「只有既有帳號會被鎖」來列舉帳號

### D3 來源 IP 分級鎖定

| 門檻 | 觀察窗 | 鎖定時間 |
|------|--------|----------|
| 10 次 | 1 分鐘 | 1 分鐘 |
| 30 次 | 15 分鐘 | 15 分鐘 |

- Key 為 `request.client.host`；取不到時用 `"unknown"`（所有未知來源共用，寧可嚴格）
- 成功登入**不**清除 IP 紀錄；否則攻擊者可用一個已知密碼的帳號反覆重置 IP 計數
- 共享 NAT 的使用者可能被短暫影響；第一級只有 1 分鐘，第二級 15 分鐘，且成功登入不受影響

### D4 資料表：每次失敗一列，避免競態與計數器更新

`login_attempts` 每次失敗插入兩列（account／ip），**不維護可變的 counter row**：

- 無 `SELECT ... FOR UPDATE`／upsert 的併發競態
- 多 worker 共享 PostgreSQL，重啟不歸零
- 查詢只需 `(kind, key_hash, created_at)` 索引
- 每次寫入順便 `DELETE created_at < now - 24h`，避免表無限成長；被封鎖的請求不寫入，成長有上限

代價：每次失敗多 2 個 INSERT＋1 個 DELETE。登入失敗本來就有 Argon2 成本，這點寫入可接受。

### D5 隱私：只存 HMAC，不存原始帳號／IP

```
key_hash = HMAC-SHA256(jwt_secret, f"{kind}:{value}")
```

- 不存原始 username／IP，避免 DB 外洩時直接暴露來源
- 重用既有 `jwt_secret`；若輪替 secret，舊計數自然失效（可接受）
- 不使用明文 SHA-256，避免離線字典比對

### D6 對外一律 429，時間不洩漏帳號存在

- 既有帳號／未知帳號、帳號鎖定／IP 鎖定都回：
  - status `429`
  - body `{"detail": "too many login attempts"}`
  - `Retry-After: <seconds>`
- 不區分「帳號不存在」與「密碼錯誤」；既有 `401` 維持不變
- 稽核仍只記既有帳號的 `auth.login_failed`（Phase 40 行為），被封鎖的請求不寫稽核，避免洪水

### D7 Timing：未知帳號也驗一次 dummy Argon2

`AuthService.authenticate` 目前對未知帳號直接拋錯，和「既有帳號＋錯密碼」有明顯時間差。改為：

- 未知帳號：對固定 dummy Argon2 hash 執行 `verify_password(password, DUMMY_HASH)`，再拋 `InvalidCredentials`
- 既有帳號：照常驗證
- 仍回同一個 `401`；測試以 monkeypatch 斷言未知帳號確實呼叫 `verify_password`

### D8 Fail-soft：DB 防護失敗不讓登入全面 500

- `check()` 發生例外 → log warning、rollback、視為未封鎖（fail-open）
- `record_failure()` 發生例外 → log warning、rollback、仍回原本的 `401`
- `reset_account()` 發生例外 → log warning、rollback、仍讓登入成功
- 理由：登入可用性優先；資料庫若真的壞掉，使用者查詢本身也會失敗。此取捨會寫入文件與已知限制

### D9 Proxy 信任邊界

- compose 的 API 只 `expose: 8000`，對外唯一入口是 nginx
- nginx 已覆寫 `X-Forwarded-For`／`X-Real-IP`
- uvicorn 加 `--proxy-headers --forwarded-allow-ips=*` 後，`request.client.host` 才是真實來源
- **若直接把 API port 暴露到公網，必須移除這個旗標或限制允許的 proxy IP**；否則客戶端可偽造來源 IP
- 本地 `uv run uvicorn` 沒有 proxy 時，`request.client.host` 本身就是連線來源

### D10 為何不用 `slowapi`

`slowapi==0.1.9` 已在依賴中，但它是「請求次數」limiter：

- 無法只計算失敗（成功登入也被計）
- route decorator 以 IP 為主，難以用 request body 的 username 做 key
- 無法表達「成功重置帳號」
- 內建 memory storage 多 worker 不共享

本 phase 需要的是「失敗後計數、帳號＋IP 雙鍵、成功重置」的狀態邏輯，直接用 SQLAlchemy／PostgreSQL 較精確，也避免新增 Redis 依賴。

---

## 資料模型與 Migration

### `login_attempts`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | UUID PK | `uuid4` |
| `kind` | `varchar(8)` | `account`／`ip` |
| `key_hash` | `varchar(64)` | HMAC-SHA256 hex |
| `created_at` | `timestamptz` | 失敗時間（UTC） |

索引：

- `ix_login_attempts_lookup (kind, key_hash, created_at)`
- `ix_login_attempts_created_at (created_at)`

Migration `0027_login_attempts.py`：

- `upgrade()`：create table＋2 indexes
- `downgrade()`：drop indexes＋table
- 不比對／改寫既有資料，downgrade 只會刪除節流紀錄（安全）

---

## API 契約

`POST /api/auth/login`

- `200`：既有 `TokenResponse`＋refresh cookie（不變）
- `401`：`{"detail": "invalid credentials"}`（不變）
- `429`：`{"detail": "too many login attempts"}`＋`Retry-After: <seconds>`（新增）
- Request body 不變；不新增欄位、不改 response model

---

## 測試矩陣（預計）

| 層級 | 案例 |
|------|------|
| Service | 帳號 5/15m、10/1h、15/24h；IP 10/1m、30/15m；窗外；封鎖不新增；成功重置帳號；IP 不清除；未知帳號；HMAC；清理；fail-soft |
| Route | 5 次錯→第 6 次 429；正確密碼仍 429；其他帳號不受影響；未知帳號 429；成功後重置；401／cookie／稽核回歸 |
| AuthService | 未知帳號仍呼叫 `verify_password`（dummy hash） |
| Web | 429／401 文案；e2e 5 次錯→鎖定文案 |
| Migration | PG `0026 → 0027 → 0026 → 0027` |

---

## 實作步驟

- [ ] T1：model＋migration 0027＋`models/__init__.py`
- [ ] T2：`login_throttle_service`（分級、HMAC、清理、fail-soft）
- [ ] T3：`routes/auth.py` 接入、429＋`Retry-After`、OpenAPI
- [ ] T4：`auth_service` dummy hash timing 防護
- [ ] T5：Web 429 文案＋單元測試
- [ ] T6：e2e 鎖定流程
- [ ] T7：api-types 重新生成
- [ ] T8：完整驗證（API、golden eval、Web、typecheck、e2e、PG migration）
- [ ] T9：文件與計畫收尾

---

## 風險與取捨

| 風險 | 影響 | 對策 |
|------|------|------|
| 帳號鎖定 DoS | 攻擊者可刻意鎖住已知帳號 | 第一級只 15 分鐘；最長 1 小時；封鎖請求不延長；另有 IP 限制 |
| 共享 IP 誤鎖 | 辦公室／NAT 使用者暫時無法登入 | 第一級 1 分鐘；第二級 30 次/15 分鐘；成功登入不受影響 |
| DB 寫入成本 | 每次失敗 2 INSERT＋1 DELETE | 登入失敗低頻；索引＋24h 清理；封鎖後不再寫 |
| 偽造 X-Forwarded-For | 繞過 IP 限制 | API 只 expose 給 nginx；文件明示直接暴露時不可加 `--forwarded-allow-ips=*` |
| Fail-open | DB 異常時暫時不封鎖 | 登入可用性優先；log warning；DB 正常時登入本身也會失敗 |
| 偽造大量帳號 | `login_attempts` 成長 | IP 限制＋24h 清理＋封鎖後不寫 |
| 時區／naive datetime | 窗戶計算錯誤 | 全部轉 UTC aware；SQLite naive 視為 UTC（沿用既有模式） |

---

## 驗收條件

- [ ] `POST /api/auth/login` 對同一帳號第 6 次錯誤回 `429`，附 `Retry-After`
- [ ] 鎖定期間即使密碼正確也回 `429`（不能繞過）
- [ ] 未知帳號與既有帳號的鎖定行為一致
- [ ] 成功登入後帳號失敗計數清零
- [ ] 不同帳號互不影響
- [ ] IP 分級生效，且成功登入不清除 IP 計數
- [ ] 所有既有登入／refresh／稽核測試不回歸
- [ ] Web 顯示「嘗試次數過多」而非「帳號或密碼錯誤」
- [ ] Migration 0027 在 PostgreSQL up/down 正常
- [ ] API／Web／typecheck／e2e／golden eval 全綠

---

## 完成後補

- 實作結果（與計畫差異）
- Final Verification（指令與數字）
- 測試基線（main，Phase 43 完成）
