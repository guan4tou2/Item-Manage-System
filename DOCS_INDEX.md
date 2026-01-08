# 📚 物品管理系統 - 文檔總結

完整的物品管理系統，支持保存期限追蹤、Email 通知、Docker 部署，兼容 PostgreSQL 和 MongoDB。

## 📖 文檔目錄

| 文檔 | 大小 | 說明 | 適合用戶 |
|-------|------|--------|----------|
| [README.md](README.md) | 7.5K | 專案概述、快速導航 | 所有用戶 |
| [README_EN.md](README_EN.md) | 8.0K | 專案概述（英文） | 英文用戶 |
| [GUIDE_ZH-TW.md](GUIDE_ZH-TW.md) | 15K | 完整使用指南（繁體中文） | 推薦新用戶 |
| [QUICK_START.md](QUICK_START.md) | 2.7K | 5 分鐘快速開始指南 | 新用戶 |
| [User_Manual_zh-TW.md](User_Manual_zh-TW.md) | 3.3K | 詳細用戶手冊 | 所有用戶 |
| [DOCKER_POSTGRES_GUIDE.md](DOCKER_POSTGRES_GUIDE.md) | 4.9K | Docker + PostgreSQL 配置指南 | 開發者/運維 |
| [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md) | 3.7K | 生產環境部署指南 | 運維工程師 |
| [SETUP.md](SETUP.md) | 2.2K | 開發環境設定指南 | 開發者 |
| [TESTING.md](TESTING.md) | 3.1K | 測試說明文檔 | 開發者 |
| [FEATURES.md](FEATURES.md) | 3.9K | 完整功能列表 | 所有用戶 |
| [/.env.example](.env.example) | 704B | 環境變數範例 | 開發者 |

## 🚀 快速導航

### 新用戶開始

1. **閱讀** [README.md](README.md) - 了解專案概述
2. **跟隨** [QUICK_START.md](QUICK_START.md) - 5 分鐘完成首次設置
3. **深入學習** [GUIDE_ZH-TW.md](GUIDE_ZH-TW.md) - 掌握所有功能

### 開發者配置

1. **環境設定** - [SETUP.md](SETUP.md)
2. **Docker 開發** - [DOCKER_POSTGRES_GUIDE.md](DOCKER_POSTGRES_GUIDE.md)
3. **測試** - [TESTING.md](TESTING.md)
4. **部署** - [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md)

## ✨ 主要功能

### 核心功能
- ✅ 物品管理（新增、編輯、刪除）
- ✅ 智能搜尋（模糊搜尋、多條件篩選）
- ✅ 位置管理（樓層/房間/區域階層）
- ✅ 物品分類（自定義類型）
- ✅ 照片管理（上傳、縮圖、預覽）
- ✅ QR/條碼標籤（生成、列印、掃描）
- ✅ 批量操作（刪除、移動）
- ✅ 收藏功能（快速訪問）
- ✅ 統計報表（數據分析）

### 通知系統（新增）
- ✅ 保存期限追蹤（食物效期、用品有效期）
- ✅ 保固到期管理（產品保固期）
- ✅ Email 通知（到期自動提醒）
- ✅ 可自訂通知天數（7/14/30/60 天前）
- ✅ 可設定通知時間（每日檢查時間）
- ✅ 通知歷史追蹤

### 技術特性
- ✅ 雙資料庫支持（PostgreSQL / MongoDB）
- ✅ PWA 支持（可安裝為手機應用）
- ✅ Docker 部署（一鍵啟動）
- ✅ 操作日誌（追蹤所有變更）

## 📁 項目結構

```
Item-Manage-System/
├── 📄 文檔
│   ├── README.md                  # 專案概述
│   ├── README_EN.md              # 專案概述（英文）
│   ├── GUIDE_ZH-TW.md           # 完整使用指南
│   ├── QUICK_START.md            # 快速開始
│   ├── User_Manual_zh-TW.md     # 用戶手冊
│   ├── DOCKER_POSTGRES_GUIDE.md  # Docker 配置指南
│   ├── Deployment_Guide_zh-TW.md  # 部署指南
│   ├── SETUP.md                 # 開發設定
│   ├── TESTING.md                # 測試說明
│   ├── FEATURES.md               # 功能列表
│   └── .env.example             # 環境變數範例
│
├── 💻 應用核心 (app/)
│   ├── __init__.py              # 應用初始化（雙資料庫）
│   ├── models/                  # SQLAlchemy 模型
│   │   ├── user.py             # 用戶模型（含通知設定）
│   │   ├── item.py             # 物品模型
│   │   ├── item_type.py        # 物品類型模型
│   │   └── log.py             # 操作日誌模型
│   ├── repositories/             # 資料庫訪問層
│   │   ├── user_repo.py        # 用戶數據（雙資料庫）
│   │   ├── item_repo.py        # 物品數據（雙資料庫）
│   │   ├── type_repo.py        # 物品類型數據
│   │   ├── location_repo.py     # 位置數據
│   │   └── log_repo.py         # 日誌數據
│   ├── services/                # 業務邏輯層
│   │   ├── notification_service.py  # 通知服務（新增）
│   │   ├── email_service.py      # Email 發送服務
│   │   ├── item_service.py      # 物品業務邏輯
│   │   ├── log_service.py       # 日誌服務
│   │   ├── type_service.py      # 類型服務
│   │   ├── user_service.py      # 用戶服務
│   │   └── location_service.py   # 位置服務
│   ├── routes/                  # API 路由
│   │   ├── auth/               # 認證路由
│   │   ├── items/              # 物品路由
│   │   ├── types/              # 類型路由
│   │   ├── locations/           # 位置路由
│   │   └── notifications/      # 通知路由（新增）
│   ├── utils/                   # 工具模組
│   │   ├── storage.py          # 文件存儲
│   │   ├── image.py            # 圖片處理
│   │   ├── auth.py             # 認證工具
│   │   └── scheduler.py       # 定時任務調度（新增）
│   └── validators/             # 表單驗證
│
├── 🎨 前端資源
│   ├── templates/               # HTML 模板
│   │   ├── home.html           # 首頁
│   │   ├── additem.html        # 新增物品
│   │   ├── edititem.html       # 編輯物品
│   │   ├── manageitem.html     # 管理物品
│   │   ├── search.html         # 搜尋頁面
│   │   ├── scan.html           # 掃描頁面
│   │   ├── statistics.html     # 統計頁面
│   │   ├── favorites.html      # 收藏頁面
│   │   ├── notifications.html   # 通知列表（新增）
│   │   └── notifications_settings.html  # 通知設定（新增）
│   ├── static/
│   │   ├── css/               # 樣式文件
│   │   ├── js/                # JavaScript
│   │   ├── uploads/           # 上傳文件目錄
│   │   ├── brand/             # 品牌資源
│   │   ├── sw.js              # Service Worker (PWA)
│   │   └── manifest.json      # PWA 清單
│
├── 🧪 測試
│   ├── tests/                  # 單元測試
│   │   ├── test_items.py
│   │   ├── test_user_service.py
│   │   ├── test_routes.py
│   │   └── ...
│   ├── test_notifications.py     # 通知功能測試（新增）
│   ├── test_login.py           # 登入測試
│   └── test_system.py         # 系統測試
│
├── 🔧 配置和腳本
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── Dockerfile              # Docker 鏡像
│   ├── requirements.txt         # Python 依賴
│   ├── .gitignore              # Git 忽略文件
│   ├── Makefile                # Make 命令
│   ├── start.sh               # 啟動腳本
│   └── scripts/               # 工具腳本
│       ├── init_db.py         # 資料庫初始化
│       ├── setup_indexes.py    # 索引設定
│       └── verify_recommendations.py
│
└── 📜 其他
    ├── app.py                 # 應用入口
    ├── run.py                 # 運行腳本
    └── run_tests.py          # 測試運行腳本
```

## 🔧 環境配置

### 資料庫配置

**PostgreSQL（推薦）**
```bash
DB_TYPE=postgres
DATABASE_URL=postgresql://user:password@localhost:5432/itemman
```

**MongoDB**
```bash
DB_TYPE=mongo
MONGO_URI=mongodb://localhost:27017/myDB
```

### 通知配置

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### 應用配置

```bash
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

完整配置範例：[`.env.example`](.env.example)

## 📊 技術棧

### 後端
- **Flask 3.1+** - Web 框架
- **SQLAlchemy 2.0+** - ORM（PostgreSQL）
- **PyMongo** - MongoDB 驅動
- **APScheduler 3.11+** - 定時任務（新增）
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

### 開發/部署
- **Python 3.13+**
- **Docker & Docker Compose**
- **Git**
- **Nginx**（生產環境推薦）

## 🚀 快速開始指南

### 1️⃣ Docker 部署（最簡單）

```bash
# 克隆專案
git clone <repository-url>
cd Item-Manage-System

# 啟動服務（含 PostgreSQL）
docker compose up --build

# 訪問系統
# 瀏覽器: http://localhost:8080
# 預設帳號: admin / admin
```

### 2️⃣ 本地開發

```bash
# 創建虛擬環境
uv venv .venv
source .venv/bin/activate

# 安裝依賴
uv pip install -r requirements.txt

# 配置環境
cp .env.example .env
vim .env  # 編輯配置

# 運行應用
python run.py
```

## 📱 PWA 安裝

系統支持 PWA，可安裝為手機應用：

1. 在手機瀏覽器訪問系統
2. 點擊瀏覽器菜單「添加到主屏幕」
3. 確認安裝

安裝後可離線瀏覽已訪問過的頁面。

## 🍎 通知系統使用

### 配置步驟

1. 登入系統
2. 導航：管理 → 通知設定
3. 配置選項：
   - 啟用通知 ✅
   - Email 地址 📧
   - 提前天數（7/14/30/60 天）
   - 通知時間（HH:MM）
4. 儲存設定

### 通知規則

- 每天只發送一次通知
- 在指定時間檢查並發送
- 空的 Email 不發送
- 包含即將到期和已過期的所有物品

### Gmail 設定範例

```bash
# 1. 啟用兩步驟驗證
# 2. 生成應用程式密碼
# 3. 配置環境變數
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=xxxx-xxxx-xxxx
```

⚠️ **重要**：使用應用程式密碼，而非帳號密碼！

## 🔧 開發指南

### 運行測試

```bash
# 運行所有測試
python run_tests.py

# 測試通知功能
python test_notifications.py

# 測試登入
python test_login.py
```

### Make 命令

```bash
make test          # 運行測試
make lint          # 代碼檢查
make format        # 代碼格式化
make build         # 構建鏡像
make up            # 啟動服務
make down          # 停止服務
```

## 📚 學習資源

### 推薦閱讀順序

1. **初學者**：README.md → QUICK_START.md → User_Manual_zh-TW.md
2. **深入學習**：GUIDE_ZH-TW.md → FEATURES.md
3. **開發者**：SETUP.md → TESTING.md → DOCKER_POSTGRES_GUIDE.md
4. **部署者**：Deployment_Guide_zh-TW.md

### 文檔特色

- ✅ 詳細的步驟說明
- ✅ 代碼示例
- ✅ 截圖說明（用戶手冊）
- ✅ 常見問題解決方案
- ✅ API 文檔
- ✅ 環境配置指南

## 🎯 使用場景

### 家庭物品管理
- 食物效期追蹤（牛奶、麵包等）
- 用品保固管理（家電、家具等）
- 玩具和配件管理
- 藥品和工具管理

### 功能亮點

| 場景 | 使用功能 |
|------|----------|
| 快速找物品 | 搜尋 + QR 掃描 |
| 避免浪費 | 到期通知 |
| 統計分析 | 統計報表 |
| 標籤管理 | QR/條碼標籤 |
| 批量管理 | 批量刪除/移動 |

## 🐛 常見問題

### 快速解決

**Q: Docker 啟動失敗，端口被佔用**
```bash
# 檢查端口佔用
lsof -i:8080

# 修改 docker-compose.yml
ports:
  - "8081:8080"  # 改用 8081
```

**Q: Email 通知沒收到**
```bash
# 1. 檢查配置
grep MAIL .env

# 2. 測試 Email 連接
# 在通知設定頁點擊「發送測試通知」

# 3. 檢查垃圾郵件資料夾
```

**Q: 照片無法上傳**
```bash
# 檢查權限
ls -la static/uploads

# 檢查大小限制（16MB）
```

更多問題：[GUIDE_ZH-TW.md#常見問題](GUIDE_ZH-TW.md#常見問題)

## 🚢 生產部署檢查清單

### 必做項目

- [ ] 修改預設密碼（admin / admin）
- [ ] 設置強 SECRET_KEY
- [ ] 配置 PostgreSQL（推薦）
- [ ] 配置 Email SMTP
- [ ] 設置 HTTPS（Nginx）
- [ ] 配置定期備份
- [ ] 啟用監控日誌

### 可選項目

- [ ] 使用 Gunicorn 替代開發服務器
- [ ] 配置 CDN 靜態資源
- [ ] 設置負載均衡
- [ ] 配置資料庫主從複製

## 🤝 貢獻指南

### 如何貢獻

1. Fork 本專案
2. 創建功能分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 開啟 Pull Request

### 代碼規範

- 遵循 PEP 8 編碼風格
- 添加適當的文檔和註釋
- 編寫測試用例
- 確保所有測試通過

## 📄 授權

MIT License - 詳細請參考 [LICENSE](LICENSE) 文件

## 🙏 致謝

- Flask 團隊
- Bootstrap 團隊
- 所有貢獻者

---

**感謝使用物品管理系統！** 🎉

如有問題或建議：
- 📧 [提交 Issue](../../issues)
- 💬 發送 [Email](mailto:support@example.com)
- 📚 查看完整文檔：[GUIDE_ZH-TW.md](GUIDE_ZH-TW.md)
