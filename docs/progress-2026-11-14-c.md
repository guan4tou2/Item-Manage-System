# 進度整理（2026-11-14，續二）

本輪整理 **Phase 47：樓層平面圖互動**、**Phase 48：收據人工核對與整張收據視圖**、**Phase 49：批次成本**、**Phase 50：清單分享唯讀連結**、**Phase 51：離線新增物品**，以及同日兩批維護項目（第一批：`AuthImage` blob 快取、ESLint 零警告、依賴升級、Dependabot 整理；第二批：Dependabot GitHub Actions 與 Python minor／patch 群組更新）。前次 Phase 45–46 記錄見 [進度文件](progress-2026-11-14-b.md)。

---

## 一、目前狀態

- 工作目錄為 `Item-Manage-System`、分支 `main`；本輪只寫工作樹，沒有 commit、push、tag、分支或 Git index 操作。
- Phase 47 於主工作樹實作；Phase 48 亦於主工作樹實作；Phase 49、50 與兩個維護項目各自在獨立 git worktree 分支平行實作後合併，合併皆無內容衝突（僅 `auth-image.tsx` 在兩個維護分支間有一處衝突，已解決）。
- Phase 51 由 codex 在獨立 worktree 實作；它在最後驗證階段用完使用額度、沒有交出最終回報。主代理接手檢查：實作已完整（計畫的實作結果段落 codex 已先寫好），並由主代理執行全部驗證後合併。
- 合併 Phase 51 時三個檔案有衝突（`messages/zh-TW.json`、`messages/en.json`、`components/shell/user-menu.test.tsx`），皆為兩邊各自新增內容，已保留雙方內容解決；兩個語系檔的鍵集合一致（各 1382 個鍵）。
- Phase 47–51 皆已實作完成；[Phase 48 計畫](plans/2026-11-14-phase48-receipt-review.md)、[Phase 49 計畫](plans/2026-11-14-phase49-batch-cost.md)、[Phase 50 計畫](plans/2026-11-14-phase50-list-share-links.md)、[Phase 51 計畫](plans/2026-11-14-phase51-offline-add.md) 狀態皆為 ✅ 完成。
- Migration 編號：0030（Phase 48）→ 0031（Phase 49）→ 0032（Phase 50）→ 0033（Phase 51），合併後為單一 head `0033`。

---

## 二、完成清單（Phase 47–51＋維護）

| 主題 | 內容 |
|------|------|
| Phase 47 樓層平面圖 | Migration 0029 `locations.plan_region`；`/locations/{id}/plan` 檢視與編輯；位置樹入口；viewer 唯讀；備份含區域 |
| Phase 48 收據人工核對 | Migration 0030 `ai_receipt_reviews`；`GET/PUT/DELETE /api/ai/receipts/{receipt_id}/review`；整張收據頁；群組標頭標記／取消核對 |
| Phase 49 批次成本 | Migration 0031 `item_batches.unit_cost`；有效單價與估值口徑；統計／報表共用 valuation；Web 批次對話框與估值小計 |
| Phase 50 清單分享 | Migration 0032 `list_shares`；`/share#{token}` 公開頁；`X-Share-Token` 端點；效期／撤銷／顯示價格；白名單回應與三標頭 |
| Phase 51 離線新增 | Migration 0033 `idempotency_keys`；`POST /api/items` 支援 `Idempotency-Key`；IndexedDB 佇列、single-flight 同步、失敗可編輯後重送或捨棄；離線提示、待同步區塊、導覽徽章 |
| AuthImage blob 快取 | 記憶體快取（`imageId` key、併發去重、引用計數、LRU 上限 50、失敗不快取、登出清空）；StrictMode 雙釋放修正 |
| ESLint 零警告 | 警告 30 → 0；`lint` script 改為 `next lint --max-warnings 0` |
| 依賴升級 | `next-intl` 3.21.1 → 4.15.1、`next-themes` 0.3.0 → 0.4.6；`pnpm audit --prod` 無已知漏洞 |
| Dependabot 第二批 | 合併 6 個檢查全綠的 PR：GitHub Actions（codeql-action 3→4、docker/login-action 3→4、setup-python 5→7、setup-qemu-action 3→4、setup-node 4→7）與 Python minor／patch 群組 |

---

## 三、驗證基線與本輪結果

| 項目 | 結果與範圍 |
|------|------------|
| API pytest | **1534 passed** |
| golden eval | **28 passed／1 skipped** |
| ruff | 零違規（`All checks passed!`） |
| Web vitest | **975 passed（154 檔）**（Node 22 與 Node 24 皆通過） |
| Web typecheck | 0 error |
| Web lint | `next lint --max-warnings 0` 通過 |
| `next build` | 成功 |
| api-types | 合併後以實際 API 重新產生 |
| `alembic heads` | 單一 `0033` |
| Phase 48 實際操作 | AI stub 模式：上傳收據→標記已核對→整張收據頁→接受品項→375px 無溢出→console 無錯誤 |
| Phase 49 實際操作 | 預設單價 50 物品＋三批（2 個＠45、3 個＠60、1 個未填成本）→ `total_value` 320.00，詳情顯示單價與估值 NT$320 |
| Phase 50 實際操作 | API 建立清單與分享連結→公開端點白名單、三標頭、token 不進 log；未登入 375px 公開頁正常顯示 |
| Phase 51 實際操作 | 本機 SQLite 暫時資料庫＋`next dev`，停止 API 行程模擬斷線：同一 `Idempotency-Key` 連送兩次 `POST /api/items` → 第一次 `201`、第二次 `200`，清單只有一筆；非 UUID key → `422`；開著新增表單停止 API → 送出後出現「1 筆待同步」「立即同步」與導覽列徽章；重新啟動 API 按「立即同步」→ toast「已同步 1 筆」、清單出現該物品且只有一筆 |
| Phase 51 分支內（合併前） | API 1465 passed、Web 873 passed（144 檔） |
| Phase 47 CI | run 43568435431：`api`、`web`、`audit`、`docker`、`e2e` 五個 job 全數通過 |
| Dependabot Python 群組更新後重跑 | 本次撰寫時尚未填入 |

---

## 四、設計決策摘要與差異

- Phase 48：收據核對列獨立於 AI 草稿快照，不改寫 AI 快照、不寫稽核、不進備份；整張收據頁重用群組標頭時隱藏指向自己的連結。
- Phase 49：統計與報表共用 `repositories/valuation.py` 的單一定義；期初估值以目前加權平均單價反推（近似值）。
- Phase 50：公開頁從 fragment 取 token，獨立 fetch 不附登入憑證；根層 Provider 在 `/share` 略過登入偏好同步，避免間接觸發 refresh 或清除 store。
- Phase 51：
  - 範圍刻意收斂為「開著 App 時斷線可新增物品」，不做分頁關閉後背景同步、離線編輯／刪除、離線圖片／AI。
  - 冪等以 `idempotency_keys` 複合主鍵 `(owner_id, key)` 實現；物品與 key 在同一交易提交，並行競爭失敗時 rollback 後查回既有物品；重送不重新派送 webhook、不增加稽核紀錄。
  - IndexedDB 佇列依 `owner_user_id` 隔離；登出不刪除，但會提示；換帳號時停止舊帳號後續送出。
  - 同步為 single-flight，逐筆依建立順序重放線上新增流程（物品 → 第一個批次 → 自訂欄位值）。
  - 失敗分類：網路層失敗維持 pending；`401` 暫停等重新登入；確定性 4xx／`410` 標 failed 供編輯後重送或捨棄；`5xx` 最多自動重試 5 次。
  - 離線提示列與待同步區塊為中性資訊，失敗才用 destructive／warning token；zh-TW／en 同步。
- 維護：`AuthImage` 快取登出時清空、token refresh 不清；ESLint 零警告門檻；依賴升級清掉最後 2 個 moderate advisory；Dependabot 第二批合併後 Python 套件版本更新，以新版本（SQLAlchemy 2.1.8、uvicorn 0.54.0、pydantic 2.14.3 等）重跑：API 1534 passed、golden eval 28 passed／1 skipped、ruff 零違規；OpenAPI 輸出有描述性差異，產生的 TypeScript 型別不變、前端 typecheck 0 error。

---

## 五、未驗證與已知限制

- **Playwright e2e 未在本機執行**（本機 Docker 未啟動）：Phase 47 為 31 spec／99 情境，Phase 48–51 新增的情境（含 `offline-add.spec.ts`）由 CI 執行。
- Migration 0030／0031／0032／0033 的 PostgreSQL 升降版未在本機執行，已由 CI 確認通過。
- Phase 48：只保留收據第一頁影像（既有限制）。
- Phase 49：報表期初估值為近似值（以目前加權平均單價反推）。
- Phase 50：公開存取沒有速率限制（token 為 256 bit，無法猜測；濫用防護交由前置代理）；本機實測用的是 SQLite，時間欄位在本機顯示為無時區（正式環境為 PostgreSQL timestamptz）。
- Phase 51：
  - 真實瀏覽器的離線模式（`navigator.onLine=false`）、私密視窗無 IndexedDB、儲存空間不足、375px 版面：未以瀏覽器實測（單元測試涵蓋邏輯）。
  - 分頁關閉期間不會同步；從未開過 App／頁面的離線啟動不保證可用（設計上的限制）。
  - 超過七天保留期的 `Idempotency-Key` 重送視為新請求。
- **CI 已確認**（run 43578011792，commit `a2ba6a0`）：`api`（含 ruff、golden eval、Migration 0030–0033 在 PostgreSQL 的 `upgrade head → downgrade -1 → upgrade head`）、`web`、`audit`、`docker`、`e2e`（chromium 與 ai-stub）五個 job 全數通過。第一次推送（`9bb3e86`）時 e2e 有 2 個情境失敗：(1) 批次成本情境在 375px 的水平溢出檢查——原因是物品詳情頁標題遇到沒有斷字機會的長名稱不折行，屬**既有的版面問題**，已修正（標題可任意斷行）；(2) 離線情境的 spec 在位置由 API 建立後沒有重新載入頁面，表單拿到舊的位置快取，屬測試前置問題，已修正。修正前後另在本機以「SQLite＋正式建置＋反向代理」的方式實跑：離線 3 情境、AI stub 5 情境（含收據人工核對）、批次成本、清單分享、平面圖皆通過。

---

## 六、後續候選（未排程）

功能候選見 [roadmap](v2-roadmap.md)：Phase 51 完成後，只剩 **離線編輯／刪除與分頁關閉後的背景同步** 列為未排程候選（粗估 L）。Phase 46 的部署驗證已是既有未驗證項目，未新增為產品功能候選。

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
