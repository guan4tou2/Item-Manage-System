# 文件索引

目前工作樹僅包含 v2；v1 歷史快照保留於 `v1-final` tag。

| 文件 | 用途 |
|------|------|
| [README](README.md) | 功能總覽與快速開始 |
| [README_EN](README_EN.md) | 專案入口 |
| [使用手冊](User_Manual_zh-TW.md) | 使用者操作 |
| [功能詳述](FEATURES.md) | 功能與相關 API |
| [設計說明](DESIGN.md) | 設計脈絡 |
| [系統架構](docs/ARCHITECTURE.md) | 元件、資料流與部署拓樸 |
| [開發指南](docs/DEVELOPMENT.md) | 本機環境、型別產生與測試 |
| [部署指南](Deployment_Guide_zh-TW.md) | Compose、環境變數與營運 |
| [排程與到期提醒](docs/scheduling.md) | 外部 cron 與冪等 job |
| [AI 說明](docs/ai.md) | AI 功能與限制 |
| [驗收清單](docs/ACCEPTANCE-CHECKLIST.md) | 功能驗收 |
| [v2 路線圖](docs/v2-roadmap.md) | Phase 與既有測試基線 |
| [變更紀錄](CHANGELOG.md) | 發佈歷史 |

API 的權威規格由 FastAPI 提供：站台 `/api/docs`（Swagger UI）、`/api/redoc`、`/api/openapi.json`。Repo 內的 [OpenAPI 匯出](packages/api-types/openapi.json) 供產生 TypeScript 型別。

歷史設計與工作紀錄位於 `docs/plans/`、`docs/progress-*`、`docs/superpowers/`；內容保留當時狀態，可能引用已下線的檔案。
