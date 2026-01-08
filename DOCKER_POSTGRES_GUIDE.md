# Docker + PostgreSQL 設置指南

本文檔說明如何使用 Docker 和 PostgreSQL 運行物品管理系統。

## 功能概述

物品管理系統現在支援：
- ✅ 物品記錄與管理
- ✅ 保存期限/保固追蹤
- ✅ 到期通知（Email）
- ✅ 支援 PostgreSQL 和 MongoDB 兩種資料庫
- ✅ Docker 部署

## 快速開始

### 1. 使用 Docker Compose（推薦）

```bash
# 啟動服務（PostgreSQL + 應用）
docker compose up --build

# 或後台運行
docker compose up -d
```

預設配置：
- PostgreSQL 16
- 用戶: `itemman`
- 密碼: `itemman_pass`
- 資料庫: `itemman`
- 應用: http://localhost:8080
- 預設帳號: `admin` / `admin`

### 2. 使用本地 PostgreSQL

如果您已安裝本地 PostgreSQL：

```bash
# 創建虛擬環境
uv venv .venv
source .venv/bin/activate

# 安裝依賴
uv pip install -r requirements.txt

# 創建資料庫
createdb itemman

# 設定環境變數
export DB_TYPE=postgres
export DATABASE_URL=postgresql://$(whoami):password@localhost:5432/itemman

# 運行應用
python run.py
```

### 3. 使用 MongoDB（原有方式）

如果您想繼續使用 MongoDB：

```bash
# 設定環境變數
export DB_TYPE=mongo
export MONGO_URI=mongodb://localhost:27017/myDB

# 運行
python run.py
```

## 環境變數配置

複製 `.env.example` 為 `.env` 並修改：

```bash
cp .env.example .env
```

重要環境變數：

| 變數 | 說明 | 預設值 |
|-------|--------|--------|
| `DB_TYPE` | 資料庫類型 | `postgres` |
| `DATABASE_URL` | PostgreSQL 連接字串 | - |
| `MONGO_URI` | MongoDB 連接字串 | - |
| `SECRET_KEY` | Flask secret key | 隨機值 |
| `MAIL_SERVER` | Email SMTP 伺服器 | - |
| `MAIL_USERNAME` | Email 使用者名稱 | - |
| `MAIL_PASSWORD` | Email 密碼 | - |

## 通知設定

### Email 配置

要啟用到期通知，請配置 SMTP 設定：

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**Gmail 特別說明**：
1. 啟用兩步驟驗證
2. 生成應用程式密碼（不使用帳號密碼）
3. 在 `.env` 中使用應用程式密碼

### 用戶通知偏好

1. 登入系統
2. 前往「管理 > 通知設定」
3. 配置：
   - ✅ 啟用通知
   - 📧 Email 地址
   - 📅 提前通知天數（7/14/30/60 天）
   - ⏰ 通知時間（每天此時間檢查）

## 項目結構

```
Item-Manage-System/
├── app/
│   ├── __init__.py          # 應用初始化（支援雙資料庫）
│   ├── models/             # SQLAlchemy 模型（PostgreSQL）
│   │   ├── user.py
│   │   ├── item.py
│   │   ├── item_type.py
│   │   └── log.py
│   ├── repositories/        # 資料庫訪問層
│   ├── services/           # 業務邏輯
│   ├── notifications/      # 通知模組
│   └── routes/           # 路由
├── docker-compose.yml      # Docker 編排配置
├── requirements.txt        # Python 依賴
├── run.py               # 應用入口
└── .env.example         # 環境變數範例
```

## 常見問題

### 無法連接 PostgreSQL

檢查 Docker 容器狀態：
```bash
docker compose ps
docker compose logs postgres
```

### Email 發送失敗

1. 確認 SMTP 設定正確
2. 檢查防火牆是否允許 SMTP 連接
3. Gmail 需要使用應用程式密碼

### 資料庫遷移

從 MongoDB 遷移到 PostgreSQL 需要導出數據並導入：

```bash
# 1. 導出 MongoDB 數據
mongoexport --db myDB --collection items --out items.json
mongoexport --db myDB --collection users --out users.json

# 2. 導入 PostgreSQL（需要編寫遷移腳本）
python scripts/migrate_mongo_to_postgres.py
```

## 生產部署建議

1. **更改預設密碼**
   ```env
   SECRET_KEY=強隨機密鑰
   POSTGRES_PASSWORD=強密碼
   ```

2. **使用反向代理**
   - Nginx 或 Apache
   - 啟用 HTTPS

3. **配置備份**
   - PostgreSQL: `pg_dump`
   - 定期備份 `static/uploads` 目錄

4. **監控**
   - 日誌收集
   - 資源監控
   - Email 通知監控

## 技術架構

### 後端
- **Flask 3** - Web 框架
- **SQLAlchemy 2** - ORM（PostgreSQL）
- **PyMongo** - MongoDB 驅動
- **APScheduler** - 定時任務
- **Flask-Mail** - Email 發送

### 前端
- **Bootstrap 5** - UI 框架
- **Font Awesome** - 圖標
- **JavaScript** - 交互功能

### 資料庫
- **PostgreSQL 16** - 主資料庫（推薦）
- **MongoDB 7** - 保留支持

## 開發指南

### 使用 uv（推薦）

```bash
# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 創建虛擬環境
uv venv .venv

# 激活
source .venv/bin/activate

# 安裝依賴（快速）
uv pip install -r requirements.txt
```

### 運行測試

```bash
python test_notifications.py
```

### Docker 開發

```bash
# 構建並啟動
docker compose up --build

# 查看日誌
docker compose logs -f app

# 停止並清理
docker compose down
```

## 授權

MIT License
