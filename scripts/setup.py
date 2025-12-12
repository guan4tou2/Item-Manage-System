#!/usr/bin/env python3
"""
物品管理系統 - 綜合設定腳本

用法:
    python scripts/setup.py [命令]

命令:
    all         執行所有設定（預設）
    indexes     只建立資料庫索引
    admin       只建立預設管理員帳號
    sample      建立範例資料
    check       檢查系統狀態
    reset       重置資料庫（危險！）

範例:
    python scripts/setup.py              # 執行所有設定
    python scripts/setup.py indexes      # 只建立索引
    python scripts/setup.py check        # 檢查狀態
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 加入專案根目錄到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, mongo


# ============================================================
# 資料庫索引設定
# ============================================================

def setup_indexes() -> bool:
    """建立所有資料庫索引"""
    print("\n🗂️  建立資料庫索引...")
    print("-" * 40)
    
    try:
        # Item 集合索引
        print("📦 item 集合:")
        mongo.db.item.create_index("ItemID", unique=True, sparse=True, background=True)
        print("   ✓ ItemID (唯一)")
        
        mongo.db.item.create_index("ItemName", background=True)
        print("   ✓ ItemName")
        
        mongo.db.item.create_index("ItemType", background=True)
        print("   ✓ ItemType")
        
        mongo.db.item.create_index("ItemFloor", background=True)
        mongo.db.item.create_index("ItemRoom", background=True)
        mongo.db.item.create_index("ItemZone", background=True)
        print("   ✓ ItemFloor, ItemRoom, ItemZone")
        
        mongo.db.item.create_index(
            [("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)],
            background=True
        )
        print("   ✓ 位置複合索引")
        
        mongo.db.item.create_index("WarrantyExpiry", background=True)
        mongo.db.item.create_index("UsageExpiry", background=True)
        print("   ✓ WarrantyExpiry, UsageExpiry")
        
        # User 集合索引
        print("👤 user 集合:")
        mongo.db.user.create_index("User", unique=True, background=True)
        print("   ✓ User (唯一)")
        
        # Type 集合索引
        print("🏷️  type 集合:")
        mongo.db.type.create_index("name", unique=True, sparse=True, background=True)
        print("   ✓ name (唯一)")
        
        # Locations 集合索引
        print("📍 locations 集合:")
        mongo.db.locations.create_index(
            [("floor", 1), ("room", 1), ("zone", 1)],
            unique=True,
            background=True
        )
        print("   ✓ 位置複合唯一索引")
        
        print("\n✅ 索引建立完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 索引建立失敗: {e}")
        return False


# ============================================================
# 預設管理員帳號
# ============================================================

def setup_admin(force: bool = False) -> bool:
    """建立預設管理員帳號"""
    print("\n👤 檢查管理員帳號...")
    print("-" * 40)
    
    try:
        existing = mongo.db.user.find_one({"User": "admin"})
        
        if existing and not force:
            print("   ℹ️  admin 帳號已存在，跳過建立")
            return True
        
        if existing and force:
            mongo.db.user.delete_one({"User": "admin"})
            print("   🗑️  已刪除舊的 admin 帳號")
        
        mongo.db.user.insert_one({
            "User": "admin",
            "Password": "admin",  # 首次登入會自動升級為雜湊
            "admin": True,
            "created_at": datetime.utcnow()
        })
        print("   ✓ 建立管理員帳號: admin / admin")
        print("\n✅ 管理員帳號設定完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 管理員帳號設定失敗: {e}")
        return False


# ============================================================
# 範例資料
# ============================================================

def setup_sample_data() -> bool:
    """建立範例資料"""
    print("\n📝 建立範例資料...")
    print("-" * 40)
    
    try:
        # 範例類型
        sample_types = ["電子產品", "家具", "文具", "工具", "其他"]
        for type_name in sample_types:
            if not mongo.db.type.find_one({"name": type_name}):
                mongo.db.type.insert_one({"name": type_name})
                print(f"   ✓ 類型: {type_name}")
            else:
                print(f"   ℹ️  類型已存在: {type_name}")
        
        # 範例位置
        sample_locations = [
            {"floor": "1F", "room": "客廳", "zone": "電視櫃"},
            {"floor": "1F", "room": "客廳", "zone": "書架"},
            {"floor": "1F", "room": "廚房", "zone": "櫥櫃"},
            {"floor": "2F", "room": "臥室", "zone": "衣櫃"},
            {"floor": "2F", "room": "書房", "zone": "書桌"},
        ]
        for loc in sample_locations:
            if not mongo.db.locations.find_one(loc):
                mongo.db.locations.insert_one(loc)
                print(f"   ✓ 位置: {loc['floor']} > {loc['room']} > {loc['zone']}")
            else:
                print(f"   ℹ️  位置已存在: {loc['floor']} > {loc['room']} > {loc['zone']}")
        
        print("\n✅ 範例資料建立完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 範例資料建立失敗: {e}")
        return False


# ============================================================
# 系統狀態檢查
# ============================================================

def check_status() -> bool:
    """檢查系統狀態"""
    print("\n🔍 系統狀態檢查...")
    print("-" * 40)
    
    all_ok = True
    
    try:
        # 資料庫連接
        mongo.db.command("ping")
        print("   ✓ MongoDB 連接正常")
    except Exception as e:
        print(f"   ❌ MongoDB 連接失敗: {e}")
        all_ok = False
        return False
    
    # 集合統計
    print("\n📊 資料統計:")
    collections = {
        "user": "使用者",
        "item": "物品",
        "type": "類型",
        "locations": "位置"
    }
    
    for coll, name in collections.items():
        try:
            count = mongo.db[coll].count_documents({})
            print(f"   • {name}: {count} 筆")
        except Exception:
            print(f"   • {name}: 無法讀取")
    
    # 索引檢查
    print("\n📋 索引狀態:")
    for coll in collections.keys():
        try:
            indexes = list(mongo.db[coll].list_indexes())
            index_count = len(indexes) - 1  # 扣除 _id 索引
            print(f"   • {coll}: {index_count} 個自訂索引")
        except Exception:
            print(f"   • {coll}: 無法讀取索引")
    
    # 管理員帳號檢查
    print("\n👤 管理員帳號:")
    admin = mongo.db.user.find_one({"User": "admin"})
    if admin:
        is_hashed = admin.get("Password", "").startswith(("pbkdf2:", "scrypt:"))
        status = "已雜湊" if is_hashed else "明文（首次登入後會升級）"
        print(f"   ✓ admin 帳號存在，密碼: {status}")
    else:
        print("   ⚠️  admin 帳號不存在")
        all_ok = False
    
    # 上傳目錄檢查
    print("\n📁 目錄狀態:")
    upload_dir = Path(__file__).resolve().parent.parent / "static" / "uploads"
    if upload_dir.exists():
        file_count = len(list(upload_dir.glob("*")))
        print(f"   ✓ 上傳目錄存在 ({file_count} 個檔案)")
    else:
        print("   ⚠️  上傳目錄不存在")
    
    print("\n" + ("✅ 系統狀態正常" if all_ok else "⚠️  部分檢查未通過"))
    return all_ok


# ============================================================
# 重置資料庫
# ============================================================

def reset_database() -> bool:
    """重置資料庫（刪除所有資料）"""
    print("\n⚠️  資料庫重置")
    print("-" * 40)
    print("警告：此操作將刪除所有資料！")
    
    confirm = input("請輸入 'RESET' 確認: ")
    if confirm != "RESET":
        print("❌ 取消重置")
        return False
    
    try:
        collections = ["user", "item", "type", "locations"]
        for coll in collections:
            result = mongo.db[coll].delete_many({})
            print(f"   🗑️  {coll}: 刪除 {result.deleted_count} 筆")
        
        print("\n✅ 資料庫已重置")
        return True
        
    except Exception as e:
        print(f"\n❌ 重置失敗: {e}")
        return False


# ============================================================
# 主程式
# ============================================================

def run_all() -> bool:
    """執行所有設定"""
    success = True
    success = setup_indexes() and success
    success = setup_admin() and success
    success = setup_sample_data() and success
    check_status()
    return success


def main():
    parser = argparse.ArgumentParser(
        description="物品管理系統設定工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python scripts/setup.py              執行所有設定
  python scripts/setup.py indexes      只建立索引
  python scripts/setup.py admin        只建立管理員帳號
  python scripts/setup.py sample       建立範例資料
  python scripts/setup.py check        檢查系統狀態
  python scripts/setup.py reset        重置資料庫
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "indexes", "admin", "sample", "check", "reset"],
        help="要執行的命令 (預設: all)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="強制執行（例如重建管理員帳號）"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🏠 物品管理系統 - 設定工具")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        commands = {
            "all": run_all,
            "indexes": setup_indexes,
            "admin": lambda: setup_admin(args.force),
            "sample": setup_sample_data,
            "check": check_status,
            "reset": reset_database,
        }
        
        success = commands[args.command]()
        
        print("\n" + "=" * 50)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

