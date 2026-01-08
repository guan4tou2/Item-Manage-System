# 🏠 物品管理系統

一個功能完整的物品管理系統，支持保存期限追蹤、Email 通知、Docker 部署，兼容 PostgreSQL 和 MongoDB。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.1+-lightgrey.svg)

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
- 🔔 **Email 通知** - 到期自動提醒通知
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

### 快速導航

- 📘 [完整使用指南 (繁體中文)](GUIDE_ZH-TW.md) - 推薦新用戶閱讀
- 🇺🇸 [Complete Documentation (English)](GUIDE_EN.md) - English version

### 詳細文檔

| 文檔 | 說明 |
|-------|--------|
| [安裝指南](GUIDE_ZH-TW.md#安裝指南) | 詳細安裝步驟 |
| [快速開始](GUIDE_ZH-TW.md#快速開始) | 5 分鐘快速上手 |
| [使用教學](GUIDE_ZH-TW.md#使用教學) | 詳細功能說明 |
| [通知系統](GUIDE_ZH-TW.md#通知系統) | 保存期限通知配置 |
| [Docker 部署](GUIDE_ZH-TW.md#docker-部署) | 容器化部署指南 |
| [API 文檔](GUIDE_ZH-TW.md#api-文檔) | API 介面說明 |
| [常見問題](GUIDE_ZH-TW.md#常見問題) | 問題解決方案 |

### 其他文檔

- [部署指南](Deployment_Guide_zh-TW.md) - 生產環境部署
- [用戶手冊](User_Manual_zh-TW.md) - 詳細用戶手冊
- [功能說明](FEATURES.md) - 完整功能列表
- [測試文檔](TESTING.md) - 測試說明
- [Docker 指南](DOCKER_POSTGRES_GUIDE.md) - Docker 和 PostgreSQL 配置

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

歡迎貢獻！

### 開發流程

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

### 代碼規範

- 遵循 PEP 8 程式碼風格
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

如有問題或建議，請：
- 提交 [GitHub Issue](../../issues)
- 發送 [Email](mailto:support@example.com)
