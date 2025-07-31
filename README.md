# 🏠 物品管理系統

一個用於記錄和管理家中物品位置的Web應用程式，支援照片上傳和精確的位置記錄。

## ✨ 主要功能

### 📸 照片記錄
- 支援上傳物品照片 (JPG, PNG, GIF)
- 自動生成縮圖以提升載入速度
- 照片預覽功能

### 📍 放置地點管理
- 記錄每個物品的具體放置地點
- 支援按地點搜尋物品
- 地點標籤顯示
- 快速更新物品位置

### 🔍 搜尋功能
- 按物品名稱搜尋
- 按放置地點搜尋
- 模糊搜尋支援

### 📊 統計資訊
- 總物品數量
- 有照片的物品數量
- 有位置記錄的物品數量
- 有分類的物品數量

### 🏷️ 物品分類
- 自定義物品類型
- 類型標籤顯示
- 按類型管理

## 🚀 安裝與運行

### 環境需求
- Python 3.7+
- MongoDB
- Flask

### 安裝步驟

1. **克隆專案**
```bash
git clone <repository-url>
cd Item-Manage-System
```

2. **安裝依賴**
```bash
pip install -r requirements.txt
```

3. **設定MongoDB**
確保MongoDB服務正在運行，並創建必要的集合：
- `user` - 使用者資料
- `item` - 物品資料
- `type` - 物品類型

4. **初始化資料**
在MongoDB中創建測試使用者：
```javascript
use myDB
db.user.insertOne({
  "User": "admin",
  "Password": "admin",
  "admin": true
})
```

5. **運行應用程式**
```bash
python app.py
```

6. **訪問系統**
打開瀏覽器訪問 `http://localhost:8080`

## 📱 使用指南

### 登入系統
- 使用預設帳號：admin / admin
- 或創建自己的使用者帳號

### 新增物品
1. 點擊「新增物品」按鈕
2. 填寫物品資訊：
   - 物品名稱
   - 物品ID
   - 上傳照片（可選）
   - 放置地點
   - 物品類型
   - 擁有者
   - 取得日期
   - 使用年限
   - 物品描述
3. 點擊「儲存物品」

### 搜尋物品
1. 在首頁搜尋欄位輸入關鍵字
2. 或點擊「搜尋」頁面進行進階搜尋
3. 支援按物品名稱和放置地點搜尋

### 管理物品
1. 在「管理物品」頁面查看所有物品
2. 可以快速更新物品位置
3. 編輯物品資訊
4. 搜尋相似物品

## 🛠️ 技術架構

### 後端技術
- **Flask** - Web框架
- **PyMongo** - MongoDB驅動
- **Pillow** - 圖片處理
- **Werkzeug** - 文件上傳

### 前端技術
- **Bootstrap 5** - UI框架
- **Font Awesome** - 圖標庫
- **JavaScript** - 互動功能

### 資料庫
- **MongoDB** - NoSQL資料庫

## 📁 專案結構

```
Item-Manage-System/
├── app.py                 # 主應用程式
├── requirements.txt       # Python依賴
├── README.md             # 專案說明
├── static/               # 靜態檔案
│   ├── css/             # CSS樣式
│   ├── js/              # JavaScript
│   ├── brand/           # 品牌資源
│   └── uploads/         # 上傳檔案
└── templates/           # HTML模板
    ├── template.html    # 基礎模板
    ├── home.html        # 首頁
    ├── additem.html     # 新增物品
    ├── search.html      # 搜尋頁面
    ├── manageitem.html  # 管理物品
    ├── edititem.html    # 編輯物品
    ├── addtype.html     # 新增類型
    └── signin.html      # 登入頁面
```

## 🔧 配置選項

### 檔案上傳設定
- 最大檔案大小：16MB
- 支援格式：JPG, PNG, GIF
- 縮圖尺寸：300x300像素

### 資料庫設定
- MongoDB URI：`mongodb://localhost:27017/myDB`
- 資料庫名稱：`myDB`

## 🐛 故障排除

### 常見問題

1. **MongoDB連接失敗**
   - 確保MongoDB服務正在運行
   - 檢查連接字串是否正確

2. **照片上傳失敗**
   - 檢查檔案大小是否超過16MB
   - 確認檔案格式是否支援
   - 檢查上傳目錄權限

3. **頁面載入緩慢**
   - 檢查圖片檔案大小
   - 確認縮圖是否正常生成

## 🤝 貢獻指南

歡迎提交Issue和Pull Request來改善這個專案！

## 📄 授權

本專案採用MIT授權條款。

## 📞 聯絡資訊

如有任何問題或建議，請透過以下方式聯絡：
- 提交GitHub Issue
- 發送Email至專案維護者

---

**物品管理系統** - 讓您的物品位置記錄變得簡單高效！ 🎉
