# v2 重構路線圖

參見 [`docs/superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md`](superpowers/specs/2026-04-21-ims-rewrite-foundation-design.md) 了解基礎決策。

## 子專案

| # | 主題 | 狀態 |
|---|------|------|
| 0 | 基礎骨架（monorepo、auth、docker） | ✅ 完成 |
| 1 | 設計系統（深色模式、tokens、shadcn 整套） | ✅ 完成 |
| 2 | 資訊架構與全域導航 | ✅ 完成 |
| 3 | 物品 CRUD + 搜尋 | ✅ 完成 |
| 4 | 儀表板與統計 | ✅ 完成 |
| 5 | 通知中心 | ✅ 完成 |
| 6 | 清單類（旅行、購物、收藏） | ✅ 完成 |
| 7 | 協作（群組、借用、轉移） | ✅ 完成 |
| 8 | 管理與設定 | ✅ 完成 |
| 9 | 行動/PWA 體驗 | ✅ 完成 |

## 快速啟動（v2）

```bash
cp .env.example .env
pnpm install
pnpm --filter @ims/api gen:types
pnpm --filter @ims/api-types gen:types
docker compose up --build
# 開啟 http://localhost/
```

## 與 v1 的關係

v1（Flask + Jinja2）程式碼保留於 `app/`、`templates/`、`static/` 等目錄，直到 v2 全部子專案完成後於 `v1-final` tag 保留快照並移除。上線切換採 Big Bang — 舊資料**不遷移**，使用者需重新註冊與錄入。
