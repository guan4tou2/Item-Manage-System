# Phase 44：安全收斂（依賴、SSRF、session 撤銷）

- **狀態**：✅ 完成
- **日期**：2026-11-14
- **分支**：`phase44-security-hardening`
- **基線**：`main` `492c6bf`（Phase 43）；API 1272 passed、Web 790 passed（133 檔）、e2e 94 情境、Migration `0027 (head)`
- **來源**：2026-11-14 專案分析的 P0／P1 安全項目

---

## 目標

不加新功能，把已知的安全缺口收掉：

1. **前端框架脫離已知 RCE 受影響版本**：Next.js 15.0.0（React2Shell，CVE-2025-55182／66478）與 React 19 RC → 已修補的穩定版。
2. **Webhook 不能被用來打內網**：出站 URL 驗證，擋私有／loopback／link-local／metadata 位址。
3. **Session 可以撤銷**：改密碼、「登出所有裝置」後，既有 access／refresh token 立即失效。
4. **汰換無人維護或有 CVE 的認證依賴**：`python-jose` → `PyJWT`；`passlib` → 直接使用 `argon2-cffi`。
5. **依賴不再靜默老化**：Dependabot ＋ CI 依賴稽核。

---

## 設計決策

### 依賴

- **D1 Next 走 15.5 線，不跳 16**：目標 `next@15.5.29`（npm `backport` tag，15.x 最新修補版）；`react`／`react-dom` 升到 19 穩定版；`zustand` 5 穩定版；`eslint-config-next`、`@types/react*` 對齊。跳 major 的風險留給獨立 phase。
- **D2 `python-jose` → `PyJWT`**：只用 HS256，API 表面極小；`decode` 一律傳明確的 `algorithms=[…]`。既有 token 格式相容（同為標準 JWS），升級不會登出使用者。
- **D3 `passlib` → `argon2-cffi`**：`passlib` 本來就是包 `argon2-cffi`，既有 `$argon2id$…` 雜湊可直接驗證，不需資料遷移；`verify_password` 對不合法雜湊回 `False` 而非丟例外（**行為變更**：passlib 原本會丟 `UnknownHashError`；改為回 `False` 讓壞資料走一般的「密碼錯誤」路徑而不是 500）。`_DUMMY_PASSWORD_HASH` 的 timing 防護保留。

### Session 撤銷

- **D4 `users.token_version`（Migration 0028）**：`INTEGER NOT NULL DEFAULT 0`。access／refresh token 新增 `ver` claim；驗證時與 `user.token_version` 比對（使用者本來就會載入，零額外查詢）。不符 → `401`。
- **D5 舊 token 相容**：沒有 `ver` 的 token 視為 `ver=0`，升級當下不會把所有人登出；第一次撤銷後自然失效。
- **D6 何時遞增**：
  - `POST /api/users/me/change-password` 成功 → 遞增；回應**重新簽發** access token 並重設 refresh cookie，讓「目前這個裝置」不被登出（additive 欄位 `access_token`）。
  - 新增 `POST /api/auth/logout-all`（需登入）→ 遞增＋清 cookie；稽核 `auth.logout_all`。
  - `POST /api/auth/logout` **維持**只清 cookie（單一裝置登出）；該裝置的 access token 最多再活 15 分鐘（已知限制）。
- **D7 不做 per-session refresh 表**：不做 refresh rotation 重用偵測、裝置清單、單一 session 撤銷；版本計數已涵蓋「密碼外洩後全部踢掉」的主要情境。
- **D8 PAT 不受影響**：`ims_pat_` 有自己的刪除流程；改密碼不撤銷 PAT（cron 等自動化不應因改密碼中斷）。文件明示。
- **D9 Web 補上自動 refresh**：盤點時發現前端**從未呼叫** `/api/auth/refresh`，access token 15 分鐘到期即 `401` → 清 store → 被踢回登入頁。`apiFetch` 改為 `401` 時 single-flight 呼叫一次 refresh、成功則重試原請求一次，失敗才清 store。`/auth/*` 路徑本身不重試。

### Webhook SSRF

- **D10 兩道檢查**：
  - **寫入時**（create／update）：只接受 `http`／`https`；必須有 host；不得帶 userinfo；host 為 IP 字面值且非全域位址 → `422`；`localhost`／`*.localhost`／`*.local`／`*.internal` → `422`。不做 DNS 解析（避免建立時的外部相依與 flaky）。
  - **送出時**（每次投遞，含重試）：解析 DNS，**所有**解析結果都必須是全域位址（`ipaddress.is_global`，並處理 IPv4-mapped IPv6）；任一不合格 → 不發請求，記一筆失敗 delivery（`status_code=NULL`、excerpt 為固定字串，不含內部資訊）。
- **D11 釘住解析結果**：驗證通過後直接連到已驗證的 IP（`Host` 標頭與 TLS SNI／憑證驗證仍用原 hostname），避免 DNS rebinding 的 TOCTOU。不跟隨 redirect（httpx 預設即不跟隨，明確寫出）。
- **D12 自架情境的 opt-in**：`WEBHOOK_ALLOW_PRIVATE_HOSTS`（預設 `false`）。家用自架常把 webhook 指向 LAN 上的 Home Assistant／n8n，由**營運者**明確開啟；開啟時仍只允許 `http`／`https`。
- **D13 既有資料**：不做 migration、不刪既有 webhook；不合格的既有 URL 在下一次投遞時被擋下並留下失敗紀錄，使用者在 UI 看得到。
- **D15 Web Push endpoint 同樣納管**（審查時發現的第二個入口）：`POST /api/channels/web-push/subscriptions` 的 `endpoint` 也是使用者提供、伺服器會對它發請求的 URL。寫入時要求 `https` 並套用同一個 guard；送出前同步解析並檢查所有位址；`requests` session 設 `max_redirects=0`。pywebpush 自行建立連線，**無法釘 IP**，對 DNS rebinding 只有降低、沒有消除（回應不回傳給使用者，屬 blind）。
- **D16 `::/96`（IPv4-compatible IPv6）明確封鎖**：`ipaddress.is_global` 會把 `::7f00:1` 判為全域位址；與 NAT64／6to4／Teredo 一併列入封鎖網段。

### CI

- **D14**：`.github/dependabot.yml`（pip `apps/api`、npm 根目錄、github-actions；每週）；CI 新增 `audit` job（`pip-audit` ＋ `pnpm audit --prod`）。稽核 job 先設為會失敗的 gate；若初次跑出無法立即處理的項目，再以明確的 ignore 清單處理，不整個關掉。

---

## 明確不在本期範圍

- access token 移出 `localStorage`、CSP／HSTS／TLS（→ Phase 46）
- MFA／WebAuthn、忘記密碼流程
- per-session refresh token 表與裝置管理
- v1 目錄下線與 release 管線（→ Phase 45）
- Next 16 升級

---

## 分工

| 工作 | 模型 | 範圍 |
|------|------|------|
| API 認證強化（D2–D8） | Opus | `apps/api` auth／users／migration 0028／依賴 |
| Webhook SSRF（D10–D13） | Sonnet | `apps/api` webhook schema／service／設定 ＋ e2e spec |
| 前端依賴升級（D1） | Sonnet | `apps/web/package.json`、lockfile、升級造成的修正 |
| CI 稽核與 Dependabot（D14） | Haiku | `.github/` |
| Web 自動 refresh、改密碼流程、webhook 422 文案（D6／D9） | Sonnet | `apps/web`（依賴升級與 API 完成後） |
| 設計決策、diff 審查、整合驗證、文件 | 主代理 | — |

---

## 驗證

- API：`cd apps/api && uv run pytest -q`；`uv run pytest evals/ -q`
- Web：`pnpm vitest run`、`pnpm typecheck`、`pnpm lint`、`pnpm build`
- Migration 0028：PostgreSQL 容器 `0027 → 0028 → 0027 → 0028`
- e2e：live stack `chromium` 專案（含 webhook、登入、改密碼）

## 實作結果

### 實際完成

- **D1–D3 依賴**：Web 升到 `next` 15.5.29、`react`／`react-dom` 19.3.1、`zustand` 5.1.0、`eslint-config-next` 15.5.29、`@types/react`／`@types/react-dom` 19.3.0；`next.config.mjs` 的 `experimental.typedRoutes` 改頂層 `typedRoutes`；沒有原始碼因 React 19 型別需要修改。API 以 `pyjwt==2.15.1`、`argon2-cffi==25.1.0` 取代 `python-jose`、`passlib`；`uv.lock` 移除 python-jose、passlib、ecdsa、rsa；測試用 `JWT_SECRET` 加長到 ≥32 bytes。
- **D4–D9 Session 撤銷**：Migration 0028 `users.token_version`；token 帶 `ver`，不符 → `401 token revoked`；改密碼回應新增 `access_token`／`token_type` 並重設 refresh cookie；新增 `POST /api/auth/logout-all`（204、稽核 `auth.logout_all`，action 總數 12 → 13）；`/logout` 不變、PAT 不受影響。Web `apiFetch` 加 single-flight refresh＋重試一次，改密碼成功後寫回新 token，密碼設定頁新增「登出所有裝置」區塊，zh-TW／en i18n。
- **D10–D13、D15、D16 SSRF**：新模組 `apps/api/app/services/url_guard.py`；寫入時與送出時兩道檢查、釘 IP（`Host`／SNI 仍用原 hostname、`follow_redirects=False`、`trust_env=False`、最多試 3 個位址）、被擋時記失敗 delivery（`status_code=NULL`、excerpt `error: destination not allowed`）、`WEBHOOK_ALLOW_PRIVATE_HOSTS`（`.env.example` 已加）；Web Push endpoint 要求 `https`、套同一個 guard、送出前同步解析、`max_redirects=0`、timeout 10 秒；Web 對 `webhook_url_not_allowed` 顯示明確文案。
- **D14 CI**：新增 `.github/dependabot.yml` 與 `ci.yml` 的獨立 `audit` job（`pip-audit` ＋ `pnpm audit --prod --audit-level=high`）。

### 與計畫的差異

- Next 版本與 D1 一致（15.5.29，不跳 16）；15.0.x 線的修補版為 15.0.5，本次未採用。
- `typedRoutes` 設定位置須由 `experimental` 移到頂層（升級至 15.5 的設定調整，D1 未逐項列出）。
- Webhook 寫入時的檢查額外拒絕十進位／八進位／十六進位／省略段 IPv4 寫法；送出時額外封鎖 `::/96`、NAT64、6to4、Teredo。
- 釘 IP 最多試 3 個位址（僅連線層失敗時換下一個）（D11 未細列此細節）。
- 審查時新增第二個入口 Web Push endpoint（D15）與 `::/96` 封鎖（D16）。
- 實作中確認前端從未呼叫 `/auth/refresh`（D9），一併修正。

### 驗證結果

- API：`1425 passed`（基線 1272，＋153）；golden eval `28 passed／1 skipped`。
- Web：vitest `805 passed（135 檔）`（基線 790／133 檔，＋15）；typecheck 0 error；`next build` 成功（Next.js 15.5.29，37 個靜態頁）。
- Migration 0028：一次性 PostgreSQL 16 容器實測 `0027 → 0028 → 0027 → 0028`，既有列回填 0、降級後欄位移除。
- 釘 IP 的 TLS 行為：以自簽憑證＋本機 TLS server 實測（SNI 為原 hostname 時 200、為其他 hostname 時 `CERTIFICATE_VERIFY_FAILED`）；此測試未納入 pytest，pytest 只驗證傳給 httpx 的 URL／`Host`／`extensions`。
- api-types 重新產生：新增 path `/api/auth/logout-all`、schema `PasswordChangeResponse`。

### 未驗證項目

- **e2e**：全新 docker stack 實跑，chromium 91 passed／1 skipped、ai-stub 4 passed（30 spec／96 情境）。新增的 `tests/session-security.spec.ts` 與改寫的 `tests/webhooks.spec.ts` 首跑即通過；skip 的 1 個情境是 `locations-tree.spec.ts` 的「真實遷移後的位置樹」依賴舊 dev 庫的 `phase26_demo` 遷移 fixture，全新資料庫不存在 → 改為明確 skip（原本會登入逾時失敗；與本期無關）。
- **`pnpm lint` 無法執行**：repo 從未有 ESLint 設定檔（`next lint` 卡在互動式設定提示），為既有缺口、與升級無關；排入 Phase 46。
- CI `audit` job 未在 GitHub Actions 實跑，首次執行可能因既有漏洞紅燈。
- 升級後仍有升級前就存在的 peer 警告：`next-intl@3.21.1`、`next-themes@0.3.0` 未宣告支援 React 19／Next 15；`next@15.5.29` 要 `@playwright/test ^1.51.1`（目前 1.48.0）。

### 已知限制

- `/logout` 後該裝置 access token 最長仍可用 15 分鐘；無 per-session 撤銷與裝置清單。
- access token 仍存 `localStorage`、無 CSP（Phase 46）。
- 正式環境 `JWT_SECRET` 少於 32 bytes 時 PyJWT 發 warning（仍可運作）；dev 預設 secret 為 30 bytes 會觸發；建議 `openssl rand -hex 32`。
- Web Push 無法釘 IP，對 DNS rebinding 只有降低；回應不回傳使用者（blind）。
- Webhook 回應本文仍整份讀入後才截 500 字（未做串流上限）。
- 版本遞增為 ORM 讀取後加 1（非 SQL 原子遞增）；並行時可能只加一次，安全效果相同。
- PAT 可呼叫 `/logout-all` 與改密碼（改密碼仍須舊密碼），延續「PAT 等同使用者權限」的既有設計。
- 既有指向內網／localhost 的 webhook 於下一次投遞被擋下；需要者設 `WEBHOOK_ALLOW_PRIVATE_HOSTS=true`。
- 2026-11-14 依使用者指示將 `main` push 至 `origin/main`；首次 push 後的 CI 結果尚未確認（lint 步驟預期失敗、`audit` job 未曾實跑）。
