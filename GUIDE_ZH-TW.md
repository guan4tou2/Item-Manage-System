# 📚 物品管理系統 - 完整文檔

本系統提供完整的物品管理功能，包括保存期限追蹤、Email 通知、Docker 部署等。

## 📖 文檔導航

| 文檔 | 說明 | 適合對象 |
|-------|--------|----------|
| [安裝指南](#安裝指南) | 完整安裝步驟 | 所有用戶 |
| [快速開始](#快速開始) | 5 分鐘快速上手 | 新用戶 |
| [使用教學](#使用教學) | 詳細使用說明 | 所有用戶 |
| [通知系統](#通知系統) | 保存期限通知功能 | 用戶/管理員 |
| [Docker 部署](#docker-部署) | 容器化部署指南 | 開發者/運維 |
| [API 文檔](#api-文檔) | API 介面說明 | 開發者 |
| [常見問題](#常見問題) | 問題解決方案 | 所有用戶 |

---

## 🚀 安裝指南

### 方法一：Docker 部署（推薦）

#### 前置需求
- Docker 20.10+
- Docker Compose 2.0+

#### 快速啟動

```bash
# 1. 複製環境變數範例
cp .env.example .env

# 2. 編輯 .env 文件（可選，使用預設值也可）
vim .env

# 3. 啟動服務
docker compose up --build

# 4. 訪問系統
# 瀏覽器打開: http://localhost:8080
```

#### 環境變數說明

| 變數 | 必填 | 預設值 | 說明 |
|-------|--------|----------|------|
| `DB_TYPE` | 否 | `postgres` | 資料庫類型: `postgres` 或 `mongo` |
| `DATABASE_URL` | 否 | - | PostgreSQL 連接字串 |
| `MONGO_URI` | 否 | - | MongoDB 連接字串 |
| `SECRET_KEY` | 否 | 自動生成 | Flask session 密鑰 |
| `MAIL_SERVER` | 否 | - | SMTP 伺服器 |
| `MAIL_USERNAME` | 否 | - | Email 使用者名稱 |
| `MAIL_PASSWORD` | 否 | - | Email 密碼 |

詳細配置請參考 [DOCKER_POSTGRES_GUIDE.md](DOCKER_POSTGRES_GUIDE.md)

---

### 方法二：本地開發環境

#### 前置需求
- Python 3.13+
- PostgreSQL 16+ 或 MongoDB 7+
- pip 或 uv

#### 使用 uv 安裝（推薦）

```bash
# 1. 安裝 uv (如未安裝)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 創建虛擬環境
uv venv .venv

# 3. 激活虛擬環境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate   # Windows

# 4. 安裝依賴
uv pip install -r requirements.txt
```

#### 使用 pip 安裝

```bash
# 1. 創建虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 2. 安裝依賴
pip install -r requirements.txt
```

#### 資料庫設定

**PostgreSQL:**
```bash
# 1. 安裝 PostgreSQL
# macOS: brew install postgresql@16
# Ubuntu: sudo apt install postgresql-16

# 2. 啟動 PostgreSQL
brew services start postgresql@16

# 3. 創建資料庫
createdb itemman

# 4. 設定環境變數
export DB_TYPE=postgres
export DATABASE_URL=postgresql://$(whoami)@localhost:5432/itemman
```

**MongoDB:**
```bash
# 1. 安裝 MongoDB
# macOS: brew tap mongodb/brew && brew install mongodb-community
# Ubuntu: sudo apt install mongodb

# 2. 啟動 MongoDB
brew services start mongodb-community

# 3. 設定環境變數
export DB_TYPE=mongo
export MONGO_URI=mongodb://localhost:27017/myDB
```

#### 運行應用

```bash
# 運行開發服務器
python run.py

# 應用將在 http://localhost:8080 啟動
```

---

## ⚡ 快速開始

### 1. 首次登入

```
網址: http://localhost:8080
預設帳號: admin
預設密碼: admin
```

⚠️ **安全提示**: 首次登入後，請立即修改密碼！

### 2. 新增第一個物品

1. 點擊「新增物品」
2. 填寫資訊：
   - 物品名稱: `牛奶`
   - 物品 ID: `FOOD-001`
   - 物品類型: `食物`
   - 放置地點: `冰箱`
   - 樓層/房間: `1樓 / 廚房`
   - 使用期限: `2026-01-15`
3. 上傳照片（可選）
4. 點擊「儲存物品」

### 3. 設定通知

1. 點擊「管理」→「通知設定」
2. 配置:
   - Email 地址: `your-email@example.com`
   - 啟用通知: ✅
   - 提前通知天數: `7 天前`
   - 通知時間: `09:00`
3. 點擊「儲存設定」

### 4. 查看通知

1. 點擊導航列的鈴鐺圖標
2. 查看到期物品列表
3. 系統會在到期前發送 Email 通知

---

## 📖 使用教學

### 基本功能

#### 新增物品

**步驟：**
1. 點擊「新增物品」按鈕
2. 填寫必要欄位：
   - 物品名稱 (必填)
   - 物品 ID (必填，唯一)
   - 物品類型
   - 放置地點
3. 設定可選資訊：
   - 保固截止日
   - 使用期限
   - 樓層/房間/區域
   - 物品描述
4. 上傳照片 (JPG, PNG, GIF, 最大 16MB)
5. 點擊「儲存物品」

**提示：**
- 物品 ID 建議使用統一格式 (如 `FOOD-001`, `ELEC-012`)
- 使用樓層/房間/區域可建立階層式位置管理

#### 搜尋物品

**方式一：快速搜尋**
- 在導航列搜尋框輸入關鍵字
- 系統自動搜尋物品名稱

**方式二：進階搜尋**
1. 點擊「搜尋」頁面
2. 使用側邊欄篩選:
   - 物品類型
   - 樓層
   - 房間
   - 區域
3. 輸入搜尋關鍵字
4. 選擇排序方式（名稱、保固到期、使用期限）

**搜尋技巧：**
- 使用模糊搜尋: `奶` 可找到 `牛奶`、`奶粉`
- 組合篩選條件精確定位

#### 編輯物品

1. 在物品卡片點擊「編輯」
2. 修改需要的欄位
3. 點擊「儲存修改」

**注意：**
- 物品 ID 不可修改
- 照片可單獨更換

#### 刪除物品

1. 在物品卡片點擊「刪除」
2. 確認刪除
3. 照片檔案會一併刪除

⚠️ **警告**: 刪除後無法恢復，請謹慎操作

### 進階功能

#### QR/條碼標籤

**用途：**
- 物品貼標
- 快速掃描定位
- 便利管理

**操作：**
1. 在物品卡片點擊 QR 圖標
2. 選擇 QR Code 或 Bar Code
3. 下載圖片並列印
4. 貼在物品上

**掃描：**
1. 點擊「掃描」頁面
2. 授予相機權限
3. 掃描物品標籤
4. 系統自動顯示該物品

#### 批量操作

**批量刪除：**
1. 在「管理物品」頁面勾選多個物品
2. 點擊「批量刪除」
3. 確認刪除

**批量移動：**
1. 勾選要移動的物品
2. 輸入目標位置
3. 點擊「批量移動」
4. 系統自動記錄移動歷史

#### 收藏功能

1. 點擊物品的星星圖標
2. 加入「收藏」清單
3. 在「收藏」頁面快速查看

#### 統計報表

1. 點擊「統計」
2. 查看統計資訊：
   - 總物品數
   - 有照片數
   - 有位置數
   - 有分類數
   - 到期物品統計

---

## 🔔 通知系統

### 通知類型

| 類型 | 說明 |
|------|--------|
| **保存期限通知** | 食物、藥品等會過期的物品 |
| **保固到期通知** | 電器、家具等保固將到期 |
| **使用期限通知** | 有有效期的用品 |

### 配置步驟

1. **登入系統** → 管理員權限用戶可配置

2. **進入通知設定**
   - 導航列 → 管理 → 通知設定

3. **配置選項**
   
   - **啟用通知** ✅
     - 開啟 Email 通知功能
   
   - **Email 地址** 📧
     - 接收通知的 Email
   
   - **提前通知天數** 📅
     - 7 天: 高頻率，適合短效期物品
     - 14 天: 適合中效期
     - 30 天: 預設值，平衡選擇
     - 60 天: 低頻率，適合長效期
   
   - **通知時間** ⏰
     - 每天在此時間檢查並發送通知
     - 格式: `HH:MM` (如 `09:00`)

4. **測試設定**
   - 點擊「發送測試通知」
   - 檢查 Email 是否收到

### 通知內容

系統會發送包含以下資訊的 Email：

```
主題: 🔔 物品到期提醒 - 2026-01-07

內容:
⚠️ 已過期物品 (2 項)
• 牛奶 - 保固到期: 2026-01-05
• 面包 - 使用期限: 2026-01-06

⏰ 即將到期物品 (3 項)
• 雞蛋 - 保固到期: 2026-01-10
• 優格 - 使用期限: 2026-01-12
• 沙拉 - 保固到期: 2026-01-15

請登入系統查看詳情並進行處理。
```

### Gmail 設定範例

如使用 Gmail 作為通知服務：

1. **啟用兩步驟驗證**
   - Gmail 設定 → 安全性 → 兩步驟驗證

2. **生成應用程式密碼**
   - Google 帳戶 → 安全性 → 應用程式密碼
   - 選擇「郵件」→ 產生
   - 複製密碼

3. **配置環境變數**
   ```env
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

⚠️ **重要**: 使用應用程式密碼，而非帳號密碼！

### 通知規則

- ✅ 每天只發送一次通知
- ✅ 只在指定的通知時間發送
- ✅ 空的 Email 不發送通知
- ✅ 已發送的通知不重複發送
- ✅ 包含即將到期和已過期的所有物品

---

## 🐳 Docker 部署

### 生產環境配置

#### 1. 準備環境檔案

```bash
cp .env.example .env
vim .env
```

**生產環境必須配置：**

```env
# 強密碼
SECRET_KEY=使用 openssl rand -hex 32 生成
POSTGRES_PASSWORD=強密碼

# Email 配置
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@company.com
MAIL_PASSWORD=your-app-password
```

#### 2. 使用 Docker Compose

```bash
# 建構並啟動
docker compose up -d

# 查看日誌
docker compose logs -f app

# 停止服務
docker compose down

# 停止並刪除數據
docker compose down -v
```

#### 3. 使用反向代理 (Nginx)

```nginx
server {
    listen 80;
    server_name items.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4. HTTPS 配置

```nginx
server {
    listen 443 ssl http2;
    server_name items.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        # ... 同上
    }
}
```

### 資料庫備份

**PostgreSQL:**
```bash
# 備份
docker compose exec postgres pg_dump -U itemman itemman > backup.sql

# 還原
docker compose exec -T postgres psql -U itemman itemman < backup.sql
```

**MongoDB:**
```bash
# 備份
docker compose exec mongo mongodump --db myDB --out /backup

# 還原
docker compose exec -T mongo mongorestore --db myDB /backup
```

---

## 🔧 API 文檔

### 認證 API

#### 登入
```http
POST /auth/signin
Content-Type: application/json

{
  "User": "admin",
  "Password": "password"
}

Response:
{
  "success": true,
  "redirect": "/home"
}
```

#### 登出
```http
POST /auth/signout

Response:
{
  "success": true,
  "redirect": "/signin"
}
```

### 物品 API

#### 新增物品
```http
POST /items/add
Content-Type: multipart/form-data

- ItemName: 牛奶
- ItemID: FOOD-001
- ItemType: 食物
- ItemStorePlace: 冰箱
- UsageExpiry: 2026-01-15
- file: (binary)

Response:
{
  "success": true,
  "message": "物品新增成功"
}
```

#### 查詢物品
```http
GET /items/search?q=牛奶&type=食物

Query Parameters:
- q: 搜尋關鍵字
- type: 物品類型
- floor: 樓層
- room: 房間
- zone: 區域
- sort: 排序方式 (name, warranty, usage)
- page: 頁碼

Response:
{
  "items": [...],
  "total": 100,
  "page": 1,
  "total_pages": 10
}
```

#### 更新物品
```http
POST /items/edit/<item_id>
Content-Type: multipart/form-data

Response:
{
  "success": true,
  "message": "物品更新成功"
}
```

#### 刪除物品
```http
POST /items/delete/<item_id>

Response:
{
  "success": true,
  "message": "物品已刪除"
}
```

### 通知 API

#### 獲取設定
```http
GET /notifications/api/settings

Response:
{
  "email": "user@example.com",
  "notify_enabled": true,
  "notify_days": 30,
  "notify_time": "09:00"
}
```

#### 更新設定
```http
POST /notifications/api/settings
Content-Type: application/json

{
  "email": "new@example.com",
  "notify_enabled": true,
  "notify_days": 14,
  "notify_time": "08:00"
}

Response:
{
  "success": true,
  "message": "設定已更新"
}
```

#### 手動發送通知
```http
POST /notifications/api/send

Response:
{
  "success": true,
  "message": "通知發送成功",
  "expired_count": 5,
  "near_count": 3
}
```

### 響應狀態碼

| 狀態碼 | 說明 |
|---------|--------|
| 200 | 成功 |
| 302 | 重定向 |
| 400 | 請求錯誤 |
| 401 | 未授權 |
| 403 | 禁止訪問 |
| 404 | 資源不存在 |
| 500 | 伺服器錯誤 |

---

## ❓ 常見問題

### 安裝問題

**Q: Docker 啟動失敗，提示端口被佔用**
```
A: 1. 檢查是否有其他服務佔用 8080 端口
   lsof -i:8080
   
   2. 修改 docker-compose.yml 中的端口映射
   ports:
     - "8081:8080"  # 改用 8081
```

**Q: 無法連接資料庫**
```
A: 1. 檢查資料庫容器是否運行
   docker compose ps

   2. 查看資料庫日誌
   docker compose logs postgres
   docker compose logs mongo

   3. 確認環境變數正確
   docker compose config
```

**Q: Python 依賴安裝失敗**
```
A: 1. 確認 Python 版本 >= 3.13
   python --version

   2. 嘗試使用 uv 安裝
   pip install -U pip
   uv venv .venv
   uv pip install -r requirements.txt
```

### 使用問題

**Q: Email 通知沒有收到**
```
A: 1. 檢查 Email 配置是否正確
   - 確認 MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD
   
   2. 檢查垃圾郵件資料夾
   - 通知可能被分類為垃圾郵件
   
   3. 測試 Email 連接
   - 在通知設定頁面點擊「發送測試通知」
   
   4. 檢查通知設定
   - 確認「啟用通知」已勾選
   - 確認 Email 地址已填寫
   - 確認提前通知天數設置合理
```

**Q: 物品照片無法上傳**
```
A: 1. 檢查檔案大小是否超過 16MB
   - 系統限制: MAX 16MB

   2. 檢查檔案格式
   - 支援格式: JPG, PNG, GIF

   3. 檢查上傳目錄權限
   static/uploads/ 目錄需要有寫入權限

   4. 查看 Docker volume 掛載
   - 確認 static_uploads volume 已正確掛載
```

**Q: QR Code 無法生成**
```
A: 1. 確認物品有設置 ItemID
   - QR Code 依賴 ItemID 生成

   2. 檢查 qrcode 套件是否安裝
   pip list | grep qrcode

   3. 檢查網絡連接
   - QR Code 生成不需要網絡
```

### 部署問題

**Q: 生產環境性能不佳**
```
A: 1. 使用 Gunicorn 替代開發服務器
   pip install gunicorn
   
   gunicorn -w 4 -b 0.0.0.0.0:8080 app:app

   2. 配置 Nginx 緩存
   location ~* \.(jpg|png|css|js)$ {
       expires 1y;
   }

   3. 使用 PostgreSQL 替代 MongoDB
   - PostgreSQL 通常有更好的查詢性能
```

**Q: Docker 容器重啟後數據丟失**
```
A: 1. 確認使用 volume 持久化數據
   docker-compose.yml 中的 volumes 配置

   2. 定期備份資料庫
   - 設置 cron 任務定期備份

   3. 使用外部資料庫服務
   - 不使用容器內資料庫，連接外部實例
```

### 開發問題

**Q: 如何調試通知功能**
```
A: 1. 查看調度器日誌
   - 應用啟動時會輸出調度器狀態

   2. 手動觸發通知
   - 訪問 /notifications/api/send 端點

   3. 檢查日誌
   - 查看 Flask 應用日誌
   - 查看 Email 服務日誌
```

**Q: 如何遷移從 MongoDB 到 PostgreSQL**
```
A: 1. 導出 MongoDB 數據
   mongoexport --db myDB --collection items --out items.json
   mongoexport --db myDB --collection users --out users.json

   2. 使用遷移腳本導入 PostgreSQL
   - 需要編寫遷移腳本處理欄位映射

   3. 驗證數據
   - 對比兩邊數據量
   - 抽樣檢查數據完整性
```

---

## 📞 支援與貢獻

### 獲取幫助

- 📧 Email: 項目維護者
- 💬 GitHub Issues: [問題追蹤]
- 📖 Wiki: [知識庫]

### 貢獻指南

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

### 開發規範

- 遵循 PEP 8 程式碼風格
- 添加適當的文檔和註釋
- 編寫測試用例
- 確保所有測試通過 (`python run_tests.py`)

---

## 📄 授權

MIT License - 詳細請參考 [LICENSE](LICENSE) 檔案

---

**感謝使用物品管理系統！** 🎉
