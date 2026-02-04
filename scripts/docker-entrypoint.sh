#!/bin/sh
#
# Docker 容器入口腳本
#
# 此腳本在容器啟動時執行以下操作：
# 1. 根據 DB_TYPE 等待對應資料庫就緒 (PostgreSQL 或 MongoDB)
# 2. 初始化資料庫（索引、管理員帳號）
# 3. 啟動 Flask 應用程式
#

set -e

echo "================================================"
echo "🏠 物品管理系統 - Docker 啟動"
echo "================================================"

# ============================================================
# 1. 等待資料庫就緒 (根據 DB_TYPE 切換)
# ============================================================

# 獲取資料庫類型，預設為 postgres
DB_TYPE="${DB_TYPE:-postgres}"
echo "📦 資料庫類型: $DB_TYPE"

# 最多等待 60 秒
MAX_RETRIES=60
RETRY_COUNT=0

if [ "$DB_TYPE" = "postgres" ] || [ "$DB_TYPE" = "postgresql" ]; then
    echo "⏳ 等待 PostgreSQL 就緒..."
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if python -c "
import os
import sys
try:
    import psycopg2
    uri = os.environ.get('DATABASE_URL', 'postgresql://itemman:itemman_pass@postgres:5432/itemman')
    conn = psycopg2.connect(uri, connect_timeout=2)
    conn.close()
    print('PostgreSQL 連接成功')
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
            echo "✓ PostgreSQL 已就緒"
            break
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "   等待中... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 1
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ PostgreSQL 連接超時"
        exit 1
    fi
else
    echo "⏳ 等待 MongoDB 就緒..."
    
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
fi

# ============================================================
# 2. 初始化資料庫
# ============================================================

echo ""
echo "🔧 初始化資料庫..."

if ! python scripts/init_db.py; then
    echo "❌ 資料庫初始化失敗"
    echo ""
    echo "可能原因："
    if [ "$DB_TYPE" = "postgres" ] || [ "$DB_TYPE" = "postgresql" ]; then
        echo "  • PostgreSQL 服務未正常運行"
    else
        echo "  • MongoDB 服務未正常運行"
    fi
    echo "  • 資料庫連接設定錯誤"
    echo "  • 初始化腳本執行錯誤"
    echo ""
    echo "請檢查資料庫狀態後重試"
    exit 1
fi

# ============================================================
# 3. 驗證初始化結果
# ============================================================

echo ""
echo "🔍 驗證初始化..."

if [ "$DB_TYPE" = "postgres" ] || [ "$DB_TYPE" = "postgresql" ]; then
    if ! python -c "
import os
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(User='admin').first()
    if not admin:
        print('❌ 管理員帳號不存在')
        sys.exit(1)
    print('✓ 管理員帳號已就緒')
    sys.exit(0)
" 2>/dev/null; then
        echo "⚠️  驗證失敗，應用程式將在啟動時自動建立管理員帳號"
    fi
else
    if ! python -c "
from pymongo import MongoClient
import os
import sys

uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/myDB')
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client.get_database()

admin = db.user.find_one({'User': 'admin'})
if not admin:
    print('❌ 管理員帳號不存在')
    sys.exit(1)

print('✓ 管理員帳號已就緒')
sys.exit(0)
" 2>/dev/null; then
        echo "⚠️  驗證失敗，嘗試建立管理員帳號..."
        python -c "
from pymongo import MongoClient
import os
uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/myDB')
client = MongoClient(uri)
db = client.get_database()
if not db.user.find_one({'User': 'admin'}):
    db.user.insert_one({'User': 'admin', 'Password': 'admin', 'admin': True})
    print('✓ 管理員帳號已建立')
else:
    print('✓ 管理員帳號已存在')
" || {
            echo "❌ 無法建立管理員帳號，應用程式可能無法正常登入"
            exit 1
        }
    fi
fi

# ============================================================
# 4. 創建必要目錄
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

