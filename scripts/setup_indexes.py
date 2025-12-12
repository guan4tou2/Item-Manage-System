#!/usr/bin/env python3
"""
資料庫索引設定腳本

執行方式：
    python scripts/setup_indexes.py

此腳本會建立以下索引：
- item 集合：ItemID (唯一), ItemName, ItemType, 位置欄位, 到期日欄位
- user 集合：User (唯一)
- type 集合：name (唯一)
- locations 集合：複合唯一索引
"""

import sys
from pathlib import Path

# 加入專案根目錄到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, mongo


def setup_item_indexes():
    """設定 item 集合索引"""
    print("📦 設定 item 集合索引...")
    
    # ItemID 唯一索引
    mongo.db.item.create_index("ItemID", unique=True, background=True)
    print("  ✓ ItemID 唯一索引")
    
    # 常用搜尋欄位索引
    mongo.db.item.create_index("ItemName", background=True)
    print("  ✓ ItemName 索引")
    
    mongo.db.item.create_index("ItemType", background=True)
    print("  ✓ ItemType 索引")
    
    # 位置欄位索引
    mongo.db.item.create_index("ItemFloor", background=True)
    mongo.db.item.create_index("ItemRoom", background=True)
    mongo.db.item.create_index("ItemZone", background=True)
    print("  ✓ 位置欄位索引 (ItemFloor, ItemRoom, ItemZone)")
    
    # 複合索引 - 位置層級搜尋
    mongo.db.item.create_index(
        [("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)],
        background=True
    )
    print("  ✓ 位置複合索引")
    
    # 到期日期索引
    mongo.db.item.create_index("WarrantyExpiry", background=True)
    mongo.db.item.create_index("UsageExpiry", background=True)
    print("  ✓ 到期日期索引 (WarrantyExpiry, UsageExpiry)")


def setup_user_indexes():
    """設定 user 集合索引"""
    print("👤 設定 user 集合索引...")
    
    mongo.db.user.create_index("User", unique=True, background=True)
    print("  ✓ User 唯一索引")


def setup_type_indexes():
    """設定 type 集合索引"""
    print("🏷️ 設定 type 集合索引...")
    
    mongo.db.type.create_index("name", unique=True, background=True)
    print("  ✓ name 唯一索引")


def setup_location_indexes():
    """設定 locations 集合索引"""
    print("📍 設定 locations 集合索引...")
    
    # 複合唯一索引，避免重複的位置組合
    mongo.db.locations.create_index(
        [("floor", 1), ("room", 1), ("zone", 1)],
        unique=True,
        background=True
    )
    print("  ✓ 位置複合唯一索引")


def list_all_indexes():
    """列出所有現有索引"""
    print("\n📋 現有索引列表：")
    
    collections = ["item", "user", "type", "locations"]
    for coll_name in collections:
        coll = mongo.db[coll_name]
        indexes = list(coll.list_indexes())
        print(f"\n  {coll_name} 集合：")
        for idx in indexes:
            print(f"    - {idx['name']}: {idx['key']}")


def main():
    print("🔧 物品管理系統 - 資料庫索引設定")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            setup_item_indexes()
            setup_user_indexes()
            setup_type_indexes()
            setup_location_indexes()
            
            list_all_indexes()
            
            print("\n✅ 所有索引設定完成！")
            
        except Exception as e:
            print(f"\n❌ 設定失敗: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

