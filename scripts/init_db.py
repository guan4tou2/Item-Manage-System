#!/usr/bin/env python3
"""
資料庫初始化腳本

適用於 Docker 容器啟動時的自動初始化。
支援 PostgreSQL 和 MongoDB 雙資料庫模式。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db, mongo, get_db_type


def init_postgres_database():
    """初始化 PostgreSQL 資料庫"""
    from app.models import User, ItemType

    print("   📋 建立資料表...")
    db.create_all()
    print("   ✓ 資料表建立完成")

    print("   👤 檢查管理員帳號...")
    if not User.query.filter_by(User="admin").first():
        from werkzeug.security import generate_password_hash

        admin = User(
            User="admin",
            Password=generate_password_hash("admin"),
            admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("   ✓ 建立預設管理員: admin / admin")
    else:
        print("   ✓ 管理員帳號已存在")

    print("   🏷️  檢查預設類型...")
    default_types = ["電子產品", "家具", "文具", "工具", "其他"]
    for type_name in default_types:
        if not ItemType.query.filter_by(name=type_name).first():
            item_type = ItemType(name=type_name)
            db.session.add(item_type)
    db.session.commit()
    print("   ✓ 預設類型已設定")

    print("✅ PostgreSQL 資料庫初始化完成")


def init_mongo_database():
    """初始化 MongoDB 資料庫"""
    print("   📋 建立索引...")
    try:
        mongo.db.item.create_index("ItemID", unique=True, sparse=True, background=True)
        mongo.db.item.create_index("ItemName", background=True)
        mongo.db.item.create_index("ItemType", background=True)
        mongo.db.item.create_index(
            [("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)],
            background=True
        )
        mongo.db.user.create_index("User", unique=True, background=True)
        mongo.db.type.create_index("name", unique=True, sparse=True, background=True)
        mongo.db.locations.create_index(
            [("floor", 1), ("room", 1), ("zone", 1)],
            unique=True,
            background=True
        )
        print("   ✓ 索引建立完成")
    except Exception as e:
        print(f"   ⚠️  索引建立警告: {e}")

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

    print("   🏷️  檢查預設類型...")
    try:
        default_types = ["電子產品", "家具", "文具", "工具", "其他"]
        for type_name in default_types:
            if not mongo.db.type.find_one({"name": type_name}):
                mongo.db.type.insert_one({"name": type_name})
        print("   ✓ 預設類型已設定")
    except Exception as e:
        print(f"   ⚠️  類型設定警告: {e}")

    print("✅ MongoDB 資料庫初始化完成")


def show_statistics():
    """顯示資料統計"""
    db_type = get_db_type()
    print("\n📊 資料統計:")

    if db_type == "postgres":
        from app.models import User, Item, ItemType, Location

        print(f"   • 使用者: {User.query.count()} 筆")
        print(f"   • 物品: {Item.query.count()} 筆")
        print(f"   • 類型: {ItemType.query.count()} 筆")
        print(f"   • 位置: {Location.query.count()} 筆")
    else:
        print(f"   • 使用者: {mongo.db.user.count_documents({})} 筆")
        print(f"   • 物品: {mongo.db.item.count_documents({})} 筆")
        print(f"   • 類型: {mongo.db.type.count_documents({})} 筆")
        print(f"   • 位置: {mongo.db.locations.count_documents({})} 筆")


def main():
    print("=" * 40)
    print("🏠 物品管理系統 - 資料庫初始化")
    print("=" * 40)

    app = create_app()
    db_type = get_db_type()
    print(f"📦 資料庫類型: {db_type}")

    with app.app_context():
        try:
            if db_type == "postgres":
                from sqlalchemy import text
                db.session.execute(text("SELECT 1"))
                print("✓ PostgreSQL 連接成功")
                print("\n🔧 初始化資料庫...")
                init_postgres_database()
            else:
                mongo.db.command("ping")
                print("✓ MongoDB 連接成功")
                print("\n🔧 初始化資料庫...")
                init_mongo_database()

            show_statistics()

        except Exception as e:
            print(f"❌ 初始化失敗: {e}")
            sys.exit(1)

    print("=" * 40)


if __name__ == "__main__":
    main()
