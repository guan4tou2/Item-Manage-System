#!/bin/sh
#
# Docker 容器入口腳本
#
# 此腳本在容器啟動時執行以下操作：
# 1. 等待 MongoDB 就緒
# 2. 初始化資料庫（索引、管理員帳號）
# 3. 啟動 Flask 應用程式
#

set -e

echo "================================================"
echo "🏠 物品管理系統 - Docker 啟動"
echo "================================================"

# ============================================================
# 1. 等待 MongoDB 就緒
# ============================================================

echo "⏳ 等待 MongoDB 就緒..."

# 從 MONGO_URI 提取主機和端口
MONGO_HOST="${MONGO_HOST:-mongo}"
MONGO_PORT="${MONGO_PORT:-27017}"

# 最多等待 60 秒
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
from pymongo import MongoClient
import os
try:
    uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/myDB')
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    client.admin.command('ping')
    print('MongoDB 連接成功')
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; then
        echo "✓ MongoDB 已就緒"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   等待中... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ MongoDB 連接超時"
    exit 1
fi

# ============================================================
# 2. 初始化資料庫
# ============================================================

echo ""
echo "🔧 初始化資料庫..."

python scripts/init_db.py || {
    echo "⚠️  初始化警告（非致命錯誤）"
}

# ============================================================
# 3. 創建必要目錄
# ============================================================

echo ""
echo "📁 檢查目錄..."
mkdir -p static/uploads
echo "✓ 目錄結構正常"

# ============================================================
# 4. 啟動應用程式
# ============================================================

echo ""
echo "================================================"
echo "🚀 啟動 Flask 應用程式"
echo "================================================"
echo ""
echo "🌐 系統將在 http://localhost:8080 啟動"
echo "👤 預設登入帳號: admin / admin"
echo "--------------------------------------------------"
echo ""

# 執行傳入的命令，或預設啟動 Flask
exec "$@"

