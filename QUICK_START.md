# 🚀 快速開始指南

## ✅ 系統狀態
您的物品管理系統已經成功設置並運行！

### 🌐 訪問系統
- **網址**: http://localhost:8080
- **登入帳號**: admin
- **登入密碼**: admin

## 🔧 問題解決

### MongoDB連接問題
如果您遇到MongoDB連接錯誤，請按照以下步驟：

1. **檢查MongoDB服務狀態**
   ```bash
   brew services list | grep mongodb
   ```

2. **如果服務未運行，啟動MongoDB**
   ```bash
   brew services start mongodb/brew/mongodb-community@7.0
   ```

3. **創建測試使用者**
   ```bash
   mongosh --eval "use myDB; db.user.insertOne({User: 'admin', Password: 'admin', admin: true})"
   ```

4. **重新啟動應用程式**
   ```bash
   source venv/bin/activate
   python run.py
   ```

## 📱 系統功能

### 主要功能
- ✅ **照片上傳** - 支援JPG, PNG, GIF格式
- ✅ **放置地點管理** - 記錄物品位置
- ✅ **搜尋功能** - 按名稱和地點搜尋
- ✅ **統計資訊** - 物品數量統計
- ✅ **分類管理** - 自定義物品類型

### 使用流程
1. **登入系統** - 使用admin/admin
2. **新增物品** - 點擊「新增物品」
3. **上傳照片** - 選擇物品照片
4. **設定地點** - 記錄放置位置
5. **搜尋物品** - 快速找到需要的物品

## 🛠️ 常用命令

### 啟動系統
```bash
./start.sh
```

### 測試系統
```bash
python test_system.py
```

### 檢查MongoDB
```bash
mongosh
use myDB
show collections
```

## 📞 故障排除

### 常見問題

**Q: 無法連接到MongoDB**
A: 確保MongoDB服務正在運行
```bash
brew services start mongodb/brew/mongodb-community@7.0
```

**Q: 登入失敗**
A: 重新創建使用者帳號
```bash
mongosh --eval "use myDB; db.user.insertOne({User: 'admin', Password: 'admin', admin: true})"
```

**Q: 照片上傳失敗**
A: 檢查檔案格式和大小
- 支援格式：JPG, PNG, GIF
- 最大大小：16MB

## 🎉 系統特色

- 🏠 **直觀的界面** - 現代化設計
- 📸 **照片管理** - 完整的圖片處理
- 📍 **地點記錄** - 精確的位置管理
- 🔍 **智能搜尋** - 快速找到物品
- 📊 **統計分析** - 詳細的數據統計

---

**您的物品管理系統已經準備就緒！** 🎊 