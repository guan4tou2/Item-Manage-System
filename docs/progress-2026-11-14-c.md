# 進度整理（2026-11-14，續二）

本輪整理 **Phase 47：樓層平面圖互動**、**Phase 48：收據人工核對與整張收據視圖**、**Phase 49：批次成本**、**Phase 50：清單分享唯讀連結**，以及同日維護項目（`AuthImage` blob 快取、ESLint 零警告、依賴升級、Dependabot 整理）。前次 Phase 45–46 記錄見 [進度文件](progress-2026-11-14-b.md)。

---

## 一、目前狀態

- 工作目錄為 `Item-Manage-System`、分支 `main`；本輪只寫工作樹，沒有 commit、push、tag、分支或 Git index 操作。
- Phase 47 於主工作樹實作；Phase 48 亦於主工作樹實作；Phase 49、50 與兩個維護項目各自在獨立 git worktree 分支平行實作後合併，合併皆無內容衝突（僅 `auth-image.tsx` 在兩個維護分支間有一處衝突，已解決）。
- Phase 47–50 皆已實作完成；[Phase 48 計畫](plans/2026-11-14-phase48-receipt-review.md)、[Phase 49 計畫](plans/2026-11-14-phase49-batch-cost.md)、[Phase 50 計畫](plans/2026-11-14-phase50-list-share-links.md) 狀態皆為 ✅ 完成。
- Migration 編號預先排定：0030（Phase 48）→ 0031（Phase 49）→ 0032（Phase 50），合併後為單一 head `0032`。
- Phase 51 計畫與 migration 0033 尚未建立，本輪未寫入任何 Phase 51 內容。

---

## 二、完成清單（Phase 47–50＋維護）

| 主題 | 內容 |
|------|------|
| Phase 47 樓層平面圖 | Migration 0029 `locations.plan_region`；`/locations/{id}/plan` 檢視與編輯；位置樹入口；viewer 唯讀；備份含區域 |
| Phase 48 收據人工核對 | Migration 0030 `ai_receipt_reviews`；`GET/PUT/DELETE /api/ai/receipts/{receipt_id}/review`；整張收據頁；群組標頭標記／取消核對 |
| Phase 49 批次成本 | Migration 0031 `item_batches.unit_cost`；有效單價與估值口徑；統計／報表共用 valuation；Web 批次對話框與估值小計 |
| Phase 50 清單分享 | Migration 0032 `list_shares`；`/share#{token}` 公開頁；`X-Share-Token` 端點；效期／撤銷／顯示價格；白名單回應與三標頭 |
| AuthImage blob 快取 | 記憶體快取（`imageId` key、併發去重、引用計數、LRU 上限 50、失敗不快取、登出清空）；StrictMode 雙釋放修正 |
| ESLint 零警告 | 警告 30 → 0；`lint` script 改為 `next lint --max-warnings 0` |
| 依賴升級 | `next-intl` 3.21.1 → 4.15.1、`next-themes` 0.3.0 → 0.4.6；`pnpm audit --prod` 無已知漏洞 |
| CI 與 Dependabot | Phase 47 CI run 43568435431 五個 job 全通；關閉 6 個已涵蓋 PR（#8–#13）、5 個要求 rebase |

---

## 三、驗證基線與本輪結果

| 項目 | 結果與範圍 |
|------|------------|
| API pytest | **1524 passed** |
| golden eval | **28 passed／1 skipped** |
| ruff | 零違規（`All checks passed!`） |
| Web vitest | **926 passed（148 檔）** |
| Web typecheck | 0 error |
| Web lint | `next lint --max-warnings 0` 通過 |
| `next build` | 成功 |
| api-types | 重新產生，與合併結果一致 |
| `alembic heads` | 單一 `0032` |
| Phase 48 實際操作 | AI stub 模式：上傳收據→標記已核對→整張收據頁→接受品項→375px 無溢出→console 無錯誤 |
| Phase 49 實際操作 | 預設單價 50 物品＋三批（2 個＠45、3 個＠60、1 個未填成本）→ `total_value` 320.00，詳情顯示單價與估值 NT$320 |
| Phase 50 實際操作 | API 建立清單與分享連結→公開端點白名單、三標頭、token 不進 log；未登入 375px 公開頁正常顯示 |
| Phase 47 CI | run 43568435431：`api`、`web`、`audit`、`docker`、`e2e` 五個 job 全數通過 |

---

## 四、設計決策摘要與差異

- Phase 48：收據核對列獨立於 AI 草稿快照，不改寫 AI 快照、不寫稽核、不進備份；整張收據頁重用群組標頭時隱藏指向自己的連結。
- Phase 49：統計與報表共用 `repositories/valuation.py` 的單一定義；期初估值以目前加權平均單價反推（近似值）。
- Phase 50：公開頁從 fragment 取 token，獨立 fetch 不附登入憑證；根層 Provider 在 `/share` 略過登入偏好同步，避免間接觸發 refresh 或清除 store。
- 維護：`AuthImage` 快取登出時清空、token refresh 不清；ESLint 零警告門檻；依賴升級清掉最後 2 個 moderate advisory。

---

## 五、未驗證與已知限制

- **Playwright e2e 未在本機執行**（本機 Docker 未啟動）：Phase 47 為 31 spec／99 情境，Phase 48–50 新增的情境由 CI 執行。
- **Migration 0030／0031／0032 的 PostgreSQL 升降版未在本機執行**，交由 CI。
- Phase 48：只保留收據第一頁影像（既有限制）。
- Phase 49：報表期初估值為近似值（以目前加權平均單價反推）。
- Phase 50：公開存取沒有速率限制（token 為 256 bit，無法猜測；濫用防護交由前置代理）；本機實測用的是 SQLite，時間欄位在本機顯示為無時區（正式環境為 PostgreSQL timestamptz）。
- CI 結果在撰寫時尚未確認（push 後由 CI 確認）。

---

## 六、後續候選（未排程）

功能候選維持 [roadmap](v2-roadmap.md)：只剩 **Background Sync（離線新增）**。Phase 46 的部署驗證已是既有未驗證項目，未新增為產品功能候選。

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
