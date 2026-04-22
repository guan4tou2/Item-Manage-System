# 🏠 物品管理系統

> **⚠️ v2 重構進行中**：專案正在以 Next.js + FastAPI 全面重寫，參見 [v2 路線圖](docs/v2-roadmap.md)。v1（Flask + Jinja2）仍可運行於 `app/`、`templates/` 目錄，v2 新程式碼位於 `apps/` 目錄。

一個功能完整的物品管理系統，支持保存期限追蹤、Email 通知、Docker 部署，兼容 PostgreSQL 和 MongoDB。

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.1+-lightgrey.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-7+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Code Style](https://img.shields.io/badge/code%20style-PEP8-orange.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

[功能特色](#-核心功能) •
[快速開始](#-快速開始) •
[文檔](#-完整文檔) •
[架構](#-技術架構) •
[貢獻](#-貢獻指南) •
[授權](#-授權)

</div>

---

## ✨ 核心功能

- 📸 **物品管理** - 新增、編輯、刪除物品
- 📍 **位置追蹤** - 樓層/房間/區域階層記錄
- 📧 **照片管理** - 支持物品照片上傳
- 🔍 **智能搜尋** - 模糊搜尋、多條件篩選
- 🏷️ **物品分類** - 自定義物品類型
- 📊 **統計報表** - 詳細的數據統計
- 📦 **QR/條碼** - 生成標籤、相機掃描
- 🍎 **保存期限** - 食物、用品有效期追蹤
- 🛡 **保固管理** - 產品保固期管理
- 🔔 **到期通知** - 提醒梯度與到期提醒
- 📦 **庫存門檻** - 安全庫存/補貨門檻與補貨清單
- 🧳 **旅行清單** - 多群組打包、臨時項目、攜帶勾選與 CSV/PDF 匯出
- 🛒 **購買清單** - 旅行/通用清單，數量/預算/店家/優先級/尺寸備註，匯出與待辦統計
- 📡 **通知管道** - Email + Web Push/LINE/Telegram 預留
- 📋 **批量操作** - 批量刪除、移動物品
- ⭐ **收藏功能** - 常用物品快速訪問
- 📱 **PWA 支持** - 可安裝為手機應用

## 🚀 快速開始

### 方法一：Docker 部署（最簡單）

```bash
# 1. 克隆專案
git clone <repository-url>
cd Item-Manage-System

# 2. 啟動服務
docker compose up --build

# 3. 訪問系統
# 瀏覽器打開: http://localhost:8080
# 預設帳號: admin / admin
```

### 方法二：本地開發

```bash
# 1. 創建虛擬環境
uv venv .venv
source .venv/bin/activate

# 2. 安裝依賴
uv pip install -r requirements.txt

# 3. 配置環境
cp .env.example .env
# 編輯 .env 配置資料庫連接

# 4. 運行應用
python run.py
```

## 📖 完整文檔

### 📚 使用者文檔

| 文檔 | 說明 | 語言 |
|-------|--------|------|
| [完整使用指南](GUIDE_ZH-TW.md) | 詳細使用說明 - **推薦新用戶閱讀** | 🇹🇼 繁體中文 |
| [Complete Guide](GUIDE_EN.md) | Full usage guide | 🇺🇸 English |
| [用戶手冊](User_Manual_zh-TW.md) | 快速參考手冊 | 🇹🇼 繁體中文 |
| [功能說明](FEATURES.md) | 完整功能列表 | 🇹🇼 繁體中文 |
| [快速開始](QUICK_START.md) | 5 分鐘快速上手 | 🇹🇼 繁體中文 |

### 👨‍💻 開發者文檔

| 文檔 | 說明 |
|-------|--------|
| [📡 API 文檔](docs/API.md) | **完整 API 端點文檔** (60+ endpoints) |
| [🏗️ 架構文檔](docs/ARCHITECTURE.md) | **系統架構與設計模式** |
| [👨‍💻 開發指南](docs/DEVELOPMENT.md) | **完整開發環境設置與最佳實踐** |
| [🧪 測試文檔](TESTING.md) | 測試框架與覆蓋率 |
| [🚀 部署指南](Deployment_Guide_zh-TW.md) | 生產環境部署 |
| [🐳 Docker 指南](DOCKER_POSTGRES_GUIDE.md) | Docker 和 PostgreSQL 配置 |

### 🔍 快速連結

| 主題 | 連結 |
|------|------|
| **安裝** | [Docker 安裝](GUIDE_ZH-TW.md#安裝指南) \| [本地安裝](GUIDE_ZH-TW.md#方法二本地開發環境) |
| **使用** | [基本功能](GUIDE_ZH-TW.md#使用教學) \| [進階功能](GUIDE_ZH-TW.md#進階功能) |
| **通知** | [Email 通知設定](GUIDE_ZH-TW.md#通知系統) \| [通知 API](docs/API.md#notifications) |
| **API** | [認證](docs/API.md#authentication) \| [物品管理](docs/API.md#items) \| [健康檢查](docs/API.md#health--monitoring) |
| **開發** | [環境設置](docs/DEVELOPMENT.md#getting-started) \| [新增功能](docs/DEVELOPMENT.md#adding-new-features) \| [測試](TESTING.md) |
| **疑難排解** | [常見問題](GUIDE_ZH-TW.md#常見問題) \| [故障排除](docs/DEVELOPMENT.md#troubleshooting) |

## 🛠️ 技術架構

### 後端

- **Flask 3.1+** - Web 框架
- **SQLAlchemy 2.0+** - ORM（PostgreSQL）
- **PyMongo** - MongoDB 驅動
- **APScheduler 3.11+** - 定時任務
- **Flask-Mail** - Email 發送
- **Flask-Login** - 認證
- **Flask-WTF** - 表單驗證
- **Flask-Limiter** - 請求限流

### 前端

- **Bootstrap 5** - UI 框架
- **Font Awesome** - 圖標庫
- **JavaScript** - 交互功能
- **PWA** - 漸進式 Web 應用

### 資料庫

- **PostgreSQL 16+** - 主資料庫（推薦）
- **MongoDB 7+** - 保留支持

### 開發工具

- **Python 3.13+**
- **Docker & Docker Compose**
- **Git**

## 📁 項目結構

```
Item-Manage-System/
├── app/                      # 應用核心
│   ├── __init__.py           # 應用初始化
│   ├── models/               # SQLAlchemy 模型
│   │   ├── user.py
│   │   ├── item.py
│   │   ├── item_type.py
│   │   └── log.py
│   ├── repositories/          # 資料庫訪問層
│   │   ├── user_repo.py
│   │   ├── item_repo.py
│   │   ├── type_repo.py
│   │   ├── location_repo.py
│   │   └── log_repo.py
│   ├── services/             # 業務邏輯層
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   ├── item_service.py
│   │   └── log_service.py
│   ├── routes/               # API 路由
│   │   ├── auth/
│   │   ├── items/
│   │   ├── types/
│   │   ├── locations/
│   │   └── notifications/
│   ├── utils/                # 工具模組
│   │   ├── storage.py
│   │   ├── image.py
│   │   ├── auth.py
│   │   └── scheduler.py
│   └── validators/           # 表單驗證
├── templates/                 # HTML 模板
├── static/                   # 靜態資源
│   ├── css/
│   ├── js/
│   ├── uploads/              # 上傳文件
│   └── brand/
├── tests/                    # 測試用例
├── scripts/                  # 腳本工具
├── docker-compose.yml          # Docker 編排
├── Dockerfile               # Docker 鏡像
├── requirements.txt          # Python 依賴
├── .env.example            # 環境變數範例
└── docs/                   # 文檔目錄
```

## 🔧 環境配置

### 資料庫配置

```bash
# 使用 PostgreSQL（推薦）
export DB_TYPE=postgres
export DATABASE_URL=postgresql://user:password@localhost:5432/itemman

# 或使用 MongoDB
export DB_TYPE=mongo
export MONGO_URI=mongodb://localhost:27017/myDB
```

### Email 通知配置

```bash
export MAIL_SERVER=smtp.gmail.com
export MAIL_PORT=587
export MAIL_USE_TLS=true
export MAIL_USERNAME=your-email@gmail.com
export MAIL_PASSWORD=your-app-password
export MAIL_DEFAULT_SENDER=your-email@gmail.com
```

完整配置請參考 [`.env.example`](.env.example)

## 🧪 測試

```bash
# 運行測試
python run_tests.py

# 測試通知功能
python test_notifications.py

# 測試登入
python test_login.py

# 測試系統
python test_system.py
```

## 📱 PWA 安裝

本系統支持 PWA，可以安裝為手機應用：

1. 在手機瀏覽器訪問系統
2. 點擊瀏覽器菜單「添加到主屏幕」
3. 確認安裝

## 🚀 生產部署

### 推薦配置
1. **使用 PostgreSQL** - 更好的性能和可靠性
2. **配置 HTTPS** - 安全通信
3. **使用 Nginx** - 反向代理和靜態文件服務
4. **定期備份** - 資料庫和上傳文件
5. **監控日誌** - 及時發現問題

詳細部署指南請參考 [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md)

---

## 🚀 生產部署

### 健康檢查和監控端點

應用程序現提供生產級別的監控端點，用於 Kubernetes 準備和負載均衡器集成。

#### 端點列表

| 端點 | 方法 | 說明 |
|-------|------|------|
| `/health` | GET | 簡單健康檢查，檢查資料庫和 Redis 連接 |
| `/ready` | GET | 準備度檢查，檢查應用是否準備處理流量 |
| `/metrics` | GET | 基礎應用指標，用於監控儀表板 |

#### 健康檢查端點 (`/health`)

**檢查項目：**
- ✅ 資料庫連接
- ✅ Redis 緩存連接
- ✅ 服務狀態

**響應示例（健康）：**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T16:45:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "healthy"
  }
}
```

**響應示例（降級）：**
```json
{
  "status": "degraded",
  "timestamp": "2025-01-08T16:45:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "unhealthy"
  }
}
```

#### 準備度檢查端點 (`/ready`)

**檢查項目：**
- ✅ 資料庫連接
- ✅ Redis 緩存連接
- ✅ 數據庫遷移狀態（僅 PostgreSQL）
- ✅ 應用是否準備處理流量

**響應示例（就緒）：**
```json
{
  "ready": true,
  "timestamp": "2025-01-08T16:45:00Z",
  "checks": {
    "database": "pass",
    "cache": "pass",
    "migrations": "pass"
  }
}
```

**響應示例（未就緒）：**
```json
{
  "ready": false,
  "timestamp": "2025-01-08T16:45:00Z",
  "checks": {
    "database": "pass",
    "cache": "pass",
    "migrations": "skip"
  }
}
```

#### 應用指標端點 (`/metrics`)

**返回的指標：**
- 總物品數量
- 有照片的物品數量
- 有位置記錄的物品數量
- 有分類的物品數量
- 類型總數
- 位置總數
- 用戶總數

**響應示例：**
```json
{
  "timestamp": "2025-01-08T16:45:00Z",
  "application": "item-manage-system",
  "version": "1.0.0",
  "counts": {
    "total_items": 142,
    "items_with_photo": 87,
    "items_with_location": 134,
    "items_with_type": 56,
    "types": 8,
    "locations": 12,
    "users": 5
  }
}
```

#### Kubernetes 準備配置

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
    initialDelaySeconds: 10
    periodSeconds: 10
    successThreshold: 1
    failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
    initialDelaySeconds: 5
    periodSeconds: 5
    successThreshold: 1
    failureThreshold: 3
```

#### 使用方法

```bash
# 健康檢查
curl http://localhost:8080/health

# 準備度檢查
curl http://localhost:8080/ready

# 應用指標
curl http://localhost:8080/metrics
```

#### 監控建議

這些端點可以與以下監控系統集成：
- **Prometheus** - 通過 metrics 端點收集指標
- **Grafana** - 創建監控儀表板
- **ELK Stack** - 收集和分析結構化日誌
- **Datadog** - 雲端監控和分析
- **New Relic** - 應用性能監控

---

## 🐛 故障排除

### 常見問題

| 問題 | 解決方案 |
|-------|----------|
| Docker 端口被佔用 | 修改 `docker-compose.yml` 端口映射 |
| 無法連接資料庫 | 檢查資料庫容器狀態和連接字符串 |
| Email 通知未發送 | 檢查 SMTP 配置和垃圾郵件資料夾 |
| 照片上傳失敗 | 檢查文件大小（<16MB）和格式 |
| 性能問題 | 使用 PostgreSQL，添加數據庫索引 |

更多問題解決方案請參考 [GUIDE_ZH-TW.md#常見問題](GUIDE_ZH-TW.md#常見問題)

## 🤝 貢獻指南

我們歡迎各種形式的貢獻！無論是報告 bug、建議新功能、改進文檔還是提交代碼。

### 🐛 報告問題

發現 bug？請[創建 Issue](../../issues/new) 並包含：
- 詳細的問題描述
- 重現步驟
- 預期行為 vs 實際行為
- 環境信息（OS、Python 版本等）
- 錯誤日誌（如果有）

### 💡 建議功能

有好點子？請[創建 Feature Request](../../issues/new) 並說明：
- 功能描述
- 使用場景
- 預期效果
- 可能的實現方案（可選）

### 📝 改進文檔

文檔有錯誤或不清楚？
- 直接編輯 Markdown 文件
- 提交 Pull Request
- 或創建 Issue 說明問題

### 👨‍💻 貢獻代碼

#### 開發流程

1. **Fork & Clone**
   ```bash
   git clone https://github.com/your-username/Item-Manage-System.git
   cd Item-Manage-System
   ```

2. **設置開發環境**
   ```bash
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   uv pip install -e ".[test]"
   ```

3. **創建功能分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```

4. **開發 & 測試**
   ```bash
   # 編寫代碼
   # 編寫測試
   pytest
   ```

5. **提交代碼**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

6. **推送 & 創建 PR**
   ```bash
   git push origin feature/amazing-feature
   # 在 GitHub 上創建 Pull Request
   ```

#### 代碼規範

- ✅ 遵循 [PEP 8](https://pep8.org/) 程式碼風格
- ✅ 添加類型提示（Type Hints）
- ✅ 編寫 Google 風格的 Docstrings
- ✅ 為新功能添加測試（目標覆蓋率 85%+）
- ✅ 更新相關文檔
- ✅ 確保所有測試通過
- ✅ 使用[語義化提交信息](https://www.conventionalcommits.org/)

#### Commit Message 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**類型 (type):**
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響功能）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具相關

**範例:**
```bash
feat(items): add bulk delete functionality
fix(auth): resolve session expiration issue
docs(api): update endpoint documentation
test(services): add notification service tests
```

#### Pull Request 檢查清單

提交 PR 前請確認：

- [ ] 代碼遵循項目風格指南
- [ ] 已添加/更新測試
- [ ] 所有測試通過 (`pytest`)
- [ ] 已更新相關文檔
- [ ] Commit messages 遵循規範
- [ ] 已在本地測試功能
- [ ] PR 描述清楚說明改動

### 📚 開發資源

- [開發指南](docs/DEVELOPMENT.md) - 完整開發文檔
- [架構文檔](docs/ARCHITECTURE.md) - 系統架構說明
- [API 文檔](docs/API.md) - API 介面參考
- [測試指南](TESTING.md) - 測試框架說明

## 🌟 專案狀態

### 功能完成度

| 模塊 | 狀態 | 覆蓋率 | 說明 |
|------|------|--------|------|
| 認證系統 | ✅ 完成 | 95% | 登入、註冊、密碼管理 |
| 物品管理 | ✅ 完成 | 90% | CRUD、搜尋、篩選、批量操作 |
| 位置管理 | ✅ 完成 | 85% | 樓層/房間/區域階層 |
| 通知系統 | ✅ 完成 | 88% | Email 通知、提醒梯度 |
| 旅行清單 | ✅ 完成 | 82% | 打包清單、群組管理 |
| 購物清單 | ✅ 完成 | 80% | 購買清單、預算追蹤 |
| QR/條碼 | ✅ 完成 | 90% | 生成與掃描 |
| 健康監控 | ✅ 完成 | 100% | Health check endpoints |
| API 文檔 | ✅ 完成 | - | Swagger/OpenAPI (部分) |

### 路線圖

#### 近期計劃 (v1.1)
- [ ] Web Push 通知
- [ ] LINE/Telegram 整合
- [ ] 多語言支持 (i18n)
- [ ] 深色模式
- [ ] 高級搜尋（全文檢索）

#### 中期計劃 (v1.2)
- [ ] 手機 App (React Native)
- [ ] 圖表與分析儀表板
- [ ] 數據匯出（Excel、PDF）
- [ ] 多用戶權限管理
- [ ] API 完整 RESTful 化

#### 長期計劃 (v2.0)
- [ ] 雲端同步
- [ ] AI 物品識別
- [ ] 語音助手整合
- [ ] 區塊鏈追蹤（供應鏈）

## 📊 專案統計

- **代碼行數**: ~7,500+ 行 Python 代碼
- **測試覆蓋率**: 85%+
- **API 端點**: 60+ 個
- **支持的數據庫**: PostgreSQL, MongoDB
- **文檔頁數**: 3,500+ 行文檔
- **開發時間**: 3+ 個月

## 📄 授權

本專案採用 **MIT License** 授權 - 詳見 [LICENSE](LICENSE) 文件

### 簡要說明

✅ **可以:**
- 商業使用
- 修改
- 分發
- 私人使用

⚠️ **限制:**
- 責任限制
- 無保證

📋 **條件:**
- 需保留授權和版權聲明

## 🙏 致謝

### 技術棧

- [Flask](https://flask.palletsprojects.com/) - 強大的 Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - 優秀的 Python ORM
- [Bootstrap](https://getbootstrap.com/) - 響應式 UI 框架
- [PostgreSQL](https://www.postgresql.org/) - 強大的開源資料庫
- [Redis](https://redis.io/) - 高性能緩存系統

### 貢獻者

感謝所有為此專案做出貢獻的開發者！

<!-- ALL-CONTRIBUTORS-LIST:START -->
<!-- Add contributors here -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

### 社群

- 💬 [Discussions](../../discussions) - 提問與討論
- 🐛 [Issues](../../issues) - Bug 報告與功能建議
- 📧 Email: support@example.com

## 📞 支持

### 獲取幫助

| 方式 | 用途 | 響應時間 |
|------|------|----------|
| [GitHub Issues](../../issues) | Bug 報告、功能建議 | 1-3 天 |
| [Discussions](../../discussions) | 使用問題、討論 | 1-2 天 |
| [Email](mailto:support@example.com) | 私密問題、商業合作 | 3-5 天 |

### 常見問題

遇到問題？先查看：
1. [常見問題解答](GUIDE_ZH-TW.md#常見問題)
2. [故障排除指南](docs/DEVELOPMENT.md#troubleshooting)
3. [已知問題](../../issues?q=is%3Aissue+label%3Aknown-issue)

### 商業支持

需要專業支持？我們提供：
- 🔧 定制開發
- 🎓 培訓服務
- 🚀 部署協助
- 💼 技術諮詢

聯繫：[business@example.com](mailto:business@example.com)

---

<div align="center">

**感謝使用物品管理系統！** 🎉

如果這個專案對你有幫助，請給個 ⭐ Star！

[回到頂部](#-物品管理系統) | [查看文檔](#-完整文檔) | [開始使用](#-快速開始)

---

Made with ❤️ by the Item Management System Team

**[GitHub](../../) • [文檔](docs/) • [問題回報](../../issues) • [討論區](../../discussions)**

</div>
