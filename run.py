#!/usr/bin/env python3
"""
物品管理系統啟動腳本
"""

import sys

from app import create_app

app = create_app()


if __name__ == "__main__":
    print("🏠 物品管理系統啟動中...")
    print("📝 請確保MongoDB服務正在運行")
    print("🌐 系統將在 http://localhost:8080 啟動")
    print("👤 預設登入帳號: admin / admin")
    print("-" * 50)

    try:
        app.run(debug=True, host="0.0.0.0", port=8080)
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        print("💡 請檢查MongoDB是否正在運行")
        sys.exit(1)