#!/bin/bash

echo "🏠 物品管理系統啟動腳本"
echo "================================"

# 檢查 uv 是否可用
if command -v uv >/dev/null 2>&1; then
  echo "🧰 檢測到 uv，使用 uv 建立與安裝套件"
  if [ ! -d "venv" ]; then
    uv venv venv
  fi
  source venv/bin/activate
  uv pip install -r requirements.txt
else
  echo "⚠️ 未找到 uv，改用內建 venv+pip（可先安裝 uv 以加速）"
  if [ ! -d "venv" ]; then
    python3 -m venv venv
  fi
  source venv/bin/activate
  pip install -r requirements.txt
fi

# 創建上傳目錄
echo "📁 創建上傳目錄..."
mkdir -p static/uploads

# 啟動應用程式
echo "🚀 啟動應用程式..."
echo "🌐 系統將在 http://localhost:8080 啟動"
echo "👤 預設登入帳號: admin / admin"
echo "================================"

python run.py