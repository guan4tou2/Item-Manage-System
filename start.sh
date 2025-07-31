#!/bin/bash

echo "🏠 物品管理系統啟動腳本"
echo "================================"

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "📦 創建虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 安裝依賴
echo "📥 安裝依賴套件..."
pip install -r requirements.txt

# 創建上傳目錄
echo "📁 創建上傳目錄..."
mkdir -p static/uploads

# 啟動應用程式
echo "🚀 啟動應用程式..."
echo "🌐 系統將在 http://localhost:8080 啟動"
echo "👤 預設登入帳號: admin / admin"
echo "================================"

python run.py 