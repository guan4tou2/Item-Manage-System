#!/usr/bin/env python3
"""
新增「保健食品」物品類型腳本

用法:
    python scripts/add_supplement_type.py

此腳本會新增「保健食品」類型到系統中，適用於追蹤保健食品、
維他命、營養補充品等有數量和到期日管理需求的消耗品。

支援 PostgreSQL 和 MongoDB 雙資料庫。
"""

import sys
from pathlib import Path

# 加入專案根目錄到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.repositories import type_repo


def add_supplement_type():
    """新增保健食品類型"""
    type_name = "保健食品"
    
    print(f"🔍 檢查「{type_name}」類型是否存在...")
    
    existing = type_repo.get_type_by_name(type_name)
    
    if existing:
        print(f"✓ 類型「{type_name}」已存在，無需新增")
        return False
    
    print(f"➕ 新增類型「{type_name}」...")
    type_repo.insert_type(type_name)
    print(f"✅ 類型「{type_name}」新增成功")
    return True


def list_all_types():
    """列出所有類型"""
    print("\n📋 目前所有物品類型:")
    types = type_repo.list_types()
    for t in types:
        print(f"   • {t.get('name', 'Unknown')}")
    print(f"\n   共 {len(types)} 種類型")


def main():
    print("=" * 45)
    print("🏠 物品管理系統 - 新增保健食品類型")
    print("=" * 45)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 新增類型
            added = add_supplement_type()
            
            # 列出所有類型
            list_all_types()
            
            if added:
                print("\n💡 提示: 現在可以在新增物品時選擇「保健食品」類型，")
                print("   並設定數量、安全庫存、補貨門檻來追蹤庫存狀態。")
            
        except Exception as e:
            print(f"❌ 執行失敗: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print("=" * 45)


if __name__ == "__main__":
    main()
