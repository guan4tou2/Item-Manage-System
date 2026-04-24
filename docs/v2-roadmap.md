# v2 重構路線圖

> **狀態：全部 10 個基礎子專案完成，之後追加 16 個進階 phase（Phase 1–16）也全部上線。** v2 已於 `main` 分支進入維護期。逐 phase 變更請看 [CHANGELOG.md](../CHANGELOG.md)。

參見 [`docs/superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md`](superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md) 了解基礎決策。

## 基礎子專案

| # | 主題 | 狀態 |
|---|------|------|
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 完成 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ✅ 完成 |
| 2 | 資訊架構與全域導航 | ✅ 完成 |
| 3 | 物品 CRUD + 搜尋 | ✅ 完成 |
| 4 | 儀表板與統計 | ✅ 完成（見下方 Phase 12 擴充） |
| 5 | 通知中心 | ✅ 完成（見下方 Phase 7 外部管道） |
| 6 | 清單類（旅行、購物、收藏） | ✅ 完成 |
| 7 | 協作（群組、借用、轉移） | ✅ 完成 |
| 8 | 管理與設定 | ✅ 完成 |
| 9 | 行動/PWA 體驗 | ✅ 完成（見下方 Phase 16 polish） |

## 進階 Phase 1–16（v1 功能補齊 + 增強）

| Phase | 主題 | 狀態 | 關鍵能力 |
|-------|------|------|----------|
| 1 | 收藏 + API Tokens + 稽核 | ✅ | `ims_pat_` PAT、audit log |
| 2 | 圖片上傳 | ✅ | MIME 允許清單、每用戶目錄 |
| 3 | Gemini AI 辨識 | ✅ | `gemini-2.0-flash`、繁中提示 |
| 4+5 | 自訂欄位 + 物品歷史 | ✅ | item types / custom fields / quantity logs / versions |
| 6 | 盤點 | ✅ | Session 盤點 → quantity log 自動寫入 |
| 7 | 外部通知 | ✅ | Email / LINE / Telegram / Web Push fail-soft |
| 8 | 倉庫 | ✅ | 跨實體場所隔離 |
| 9 | 備份匯出 | ✅ | JSON dump，含 `format_version` |
| 10 | Webhooks | ✅ | HMAC-SHA256、delivery log |
| 11 | 位置進階 | ✅ | 手動排序、樓層平面圖 |
| 12 | 儀表板 v2 | ✅ | 低庫存 / 借出逾期 / 30 天趨勢 / 活動流 |
| 13 | QR 標籤產生 | ✅ | 物品 PNG label + A4 列印預覽 |
| 14 | CSV 批次匯入/匯出 | ✅ | dry-run、per-row 驗證、query 匯出 |
| 15 | 相機 QR 掃描 | ✅ | `/scan` 頁、裸 UUID fallback |
| 16 | PWA polish | ✅ | shortcuts、iOS meta、SW v2 |
| 17 | 文件同步 | ✅ | CHANGELOG、README、FEATURES 對齊實作 |
| 18 | SW 更新提示 | ✅ | 偵測 waiting SW → sonner toast → skipWaiting |
| 19 | CSV tags round-trip | ✅ | export/import `tag_names`，pipe-delimited、dedup、per-owner 隔離 |

## 測試規模

- API 測試：406 passed（pytest-asyncio + FastAPI TestClient + aiosqlite）
- Web 測試：87 passed（vitest + @testing-library/react + jsdom）
- 兩套測試套件都是每次 phase 推進 main 前必綠條件

## 快速啟動（v2）

```bash
cp .env.example .env
pnpm install
docker compose up --build
# 開啟 http://localhost/
```

首次啟動需跑一次 Alembic：容器內會自動執行 `alembic upgrade head`；若本機跑則：

```bash
cd apps/api
.venv/bin/alembic upgrade head
```

詳細部署步驟見 [Deployment_Guide_zh-TW.md](../Deployment_Guide_zh-TW.md)。

## 與 v1 的關係

v1（Flask + Jinja2）程式碼仍保留於 `app/`、`templates/`、`static/` 等目錄作為唯讀參考。

- **不接受新功能**：所有新功能都進 `apps/web` + `apps/api`
- **沒有資料遷移**：採 Big Bang 切換，v1 使用者需在 v2 重新註冊。v1 的 CSV/JSON 匯出可匯入到 v2（見 Phase 14）
- **legacy tag**：未來會打 `v1-final` tag 保留 v1 快照，再從 main 移除這些目錄

## 後續候選（尚未排程）

依價值排序。完成項目已從此列表移到上方的 Phase 表格。

1. **Background Sync**：`/items/new` 在離線狀態接受新增，同步後 flush（需要 IndexedDB 佇列 + SW `sync` 事件）
2. **Webhook 重試**：目前失敗不重試，未來可加 exponential backoff + 最大嘗試次數
3. **多 location 階層**：目前 floor/room/zone 是 flat 三層，若需要巢狀 tree 會重做 schema
4. **Tag 管理 UI**：目前 tag 只能在建立 item 時輸入（CSV 匯入也會 auto-create，見 Phase 19）；未來可加獨立的 tag 管理頁面（rename、合併、刪除孤兒）

排程時請把選定項目升成正式 phase，走既有的 worktree → 測試 → merge 節奏。
