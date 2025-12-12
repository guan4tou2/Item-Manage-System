#!/bin/bash
#
# 物品管理系統啟動腳本
#
# 用法:
#   ./start.sh          啟動應用程式（含初始化）
#   ./start.sh --skip   跳過初始化，直接啟動
#   ./start.sh --init   只執行初始化
#

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🏠 物品管理系統${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 解析參數
SKIP_INIT=false
INIT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip)
            SKIP_INIT=true
            shift
            ;;
        --init)
            INIT_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}未知參數: $1${NC}"
            exit 1
            ;;
    esac
done

# ============================================================
# 1. 設置虛擬環境
# ============================================================

echo -e "${BLUE}📦 設置 Python 環境...${NC}"

if command -v uv >/dev/null 2>&1; then
    echo "   使用 uv（快速模式）"
    if [ ! -d "venv" ]; then
        uv venv venv
    fi
    source venv/bin/activate
    uv pip install -r requirements.txt --quiet
else
    echo "   使用 pip（標準模式）"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt --quiet
fi

echo -e "${GREEN}   ✓ 環境設置完成${NC}"

# ============================================================
# 2. 創建必要目錄
# ============================================================

echo -e "${BLUE}📁 檢查目錄結構...${NC}"
mkdir -p static/uploads
echo -e "${GREEN}   ✓ 目錄結構正常${NC}"

# ============================================================
# 3. 資料庫初始化
# ============================================================

if [ "$SKIP_INIT" = false ]; then
    echo -e "${BLUE}🔧 初始化資料庫...${NC}"
    
    # 等待 MongoDB 就緒（如果使用 Docker）
    if [ -n "$MONGO_URI" ]; then
        echo "   等待 MongoDB 就緒..."
        for i in {1..30}; do
            if python -c "from pymongo import MongoClient; MongoClient('$MONGO_URI').admin.command('ping')" 2>/dev/null; then
                break
            fi
            sleep 1
        done
    fi
    
    # 執行初始化
    python scripts/init_db.py || {
        echo -e "${YELLOW}   ⚠️  初始化警告（可能 MongoDB 未啟動）${NC}"
        echo -e "${YELLOW}   💡 請確保 MongoDB 正在運行${NC}"
    }
fi

# ============================================================
# 4. 啟動應用程式
# ============================================================

if [ "$INIT_ONLY" = true ]; then
    echo ""
    echo -e "${GREEN}✅ 初始化完成${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🚀 啟動應用程式${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "   🌐 網址: ${YELLOW}http://localhost:8080${NC}"
echo -e "   👤 帳號: ${YELLOW}admin / admin${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo ""

python run.py
