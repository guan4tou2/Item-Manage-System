#!/usr/bin/env python3
"""
資料庫初始化腳本（簡化版）

適用於 Docker 容器啟動時的自動初始化。
只執行必要的初始化操作，不會覆蓋現有資料。

用法:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

# 加入專案根目錄到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, mongo


def init_database():
    """初始化資料庫"""
    print("🔧 初始化資料庫...")
    
    # 1. 建立索引（冪等操作，重複執行不會出錯）
    print("   📋 建立索引...")
    try:
        # Item 索引
        mongo.db.item.create_index("ItemID", unique=True, sparse=True, background=True)
        mongo.db.item.create_index("ItemName", background=True)
        mongo.db.item.create_index("ItemType", background=True)
        mongo.db.item.create_index(
            [("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)],
            background=True
        )
        
        # User 索引
        mongo.db.user.create_index("User", unique=True, background=True)
        
        # Type 索引
        mongo.db.type.create_index("name", unique=True, sparse=True, background=True)
        
        # Locations 索引
        mongo.db.locations.create_index(
            [("floor", 1), ("room", 1), ("zone", 1)],
            unique=True,
            background=True
        )
        print("   ✓ 索引建立完成")
    except Exception as e:
        print(f"   ⚠️  索引建立警告: {e}")
    
    # 2. 建立預設管理員（如果不存在）
    print("   👤 檢查管理員帳號...")
    try:
        if not mongo.db.user.find_one({"User": "admin"}):
            mongo.db.user.insert_one({
                "User": "admin",
                "Password": "admin",
                "admin": True
            })
            print("   ✓ 建立預設管理員: admin / admin")
        else:
            print("   ✓ 管理員帳號已存在")
    except Exception as e:
        print(f"   ⚠️  管理員帳號警告: {e}")
    
    # 3. 建立預設類型（如果不存在）
    print("   🏷️  檢查預設類型...")
    try:
        default_types = ["電子產品", "家具", "文具", "工具", "其他"]
        for type_name in default_types:
            if not mongo.db.type.find_one({"name": type_name}):
                mongo.db.type.insert_one({"name": type_name})
        print("   ✓ 預設類型已設定")
    except Exception as e:
        print(f"   ⚠️  類型設定警告: {e}")
    
    print("✅ 資料庫初始化完成")


def main():
    print("=" * 40)
    print("🏠 物品管理系統 - 資料庫初始化")
    print("=" * 40)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 測試連接
            mongo.db.command("ping")
            print("✓ MongoDB 連接成功")
            
            init_database()
            
            # 顯示統計
            print("\n📊 資料統計:")
            print(f"   • 使用者: {mongo.db.user.count_documents({})} 筆")
            print(f"   • 物品: {mongo.db.item.count_documents({})} 筆")
            print(f"   • 類型: {mongo.db.type.count_documents({})} 筆")
            print(f"   • 位置: {mongo.db.locations.count_documents({})} 筆")
            
        except Exception as e:
            print(f"❌ 初始化失敗: {e}")
            sys.exit(1)
    
    print("=" * 40)


if __name__ == "__main__":
    main()

