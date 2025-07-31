# 🚀 快速設置指南

## 📋 系統需求
- Python 3.7+
- MongoDB
- macOS/Linux/Windows

## ⚡ 快速啟動

### 方法一：使用啟動腳本（推薦）
```bash
# 1. 克隆專案
git clone <repository-url>
cd Item-Manage-System

# 2. 執行啟動腳本
./start.sh
```

### 方法二：手動設置
```bash
# 1. 創建虛擬環境
python3 -m venv venv

# 2. 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動MongoDB
# 確保MongoDB服務正在運行

# 5. 運行應用程式
python run.py
```

## 🔧 MongoDB設置

### 安裝MongoDB
```bash
# macOS (使用Homebrew)
brew install mongodb-community

# 啟動MongoDB服務
brew services start mongodb-community
```

### 創建測試使用者
```bash
# 連接到MongoDB
mongosh

# 切換到資料庫
use myDB

# 創建管理員使用者
db.user.insertOne({
  "User": "admin",
  "Password": "admin",
  "admin": true
})
```

## 🌐 訪問系統

1. 打開瀏覽器
2. 訪問 `http://localhost:8080`
3. 使用預設帳號登入：
   - 使用者名稱：`admin`
   - 密碼：`admin`

## 📸 功能特色

### ✅ 已完成功能
- [x] 使用者登入系統
- [x] 物品新增與管理
- [x] 照片上傳與顯示
- [x] 放置地點記錄
- [x] 物品搜尋功能
- [x] 統計資訊顯示
- [x] 響應式設計
- [x] 現代化UI界面

### 🎯 核心功能
1. **照片記錄** - 支援上傳物品照片
2. **地點管理** - 記錄物品放置位置
3. **搜尋功能** - 快速找到需要的物品
4. **統計分析** - 查看物品統計資訊
5. **分類管理** - 自定義物品類型

## 🛠️ 故障排除

### 常見問題

**Q: MongoDB連接失敗**
A: 確保MongoDB服務正在運行
```bash
brew services list | grep mongodb
```

**Q: 照片上傳失敗**
A: 檢查檔案大小和格式
- 最大檔案大小：16MB
- 支援格式：JPG, PNG, GIF

**Q: 頁面載入緩慢**
A: 檢查圖片檔案大小，系統會自動生成縮圖

## 📞 支援

如有問題，請：
1. 查看 `README.md` 詳細文檔
2. 運行 `python test_system.py` 進行系統測試
3. 檢查MongoDB連接狀態

---

**物品管理系統** - 讓您的物品管理變得簡單高效！ 🎉 