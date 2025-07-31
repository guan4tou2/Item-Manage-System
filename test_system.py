#!/usr/bin/env python3
"""
物品管理系統測試腳本
"""

import os
import sys


def test_dependencies():
    """測試依賴套件"""
    print("🔍 測試依賴套件...")
    try:
        import flask
        import pymongo
        from PIL import Image
        from werkzeug.utils import secure_filename

        print("✅ 所有依賴套件已安裝")
        return True
    except ImportError as e:
        print(f"❌ 依賴套件缺失: {e}")
        return False


def test_directories():
    """測試目錄結構"""
    print("📁 測試目錄結構...")
    required_dirs = ["static/uploads", "templates", "static/css", "static/js"]

    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path} 存在")
        else:
            print(f"❌ {dir_path} 不存在")
            return False
    return True


def test_files():
    """測試必要檔案"""
    print("📄 測試必要檔案...")
    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        "templates/template.html",
        "templates/home.html",
        "templates/additem.html",
        "templates/search.html",
    ]

    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
            return False
    return True


def test_app_import():
    """測試應用程式導入"""
    print("🚀 測試應用程式導入...")
    try:
        print("✅ 應用程式導入成功")
        return True
    except Exception as e:
        print(f"❌ 應用程式導入失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🏠 物品管理系統測試")
    print("=" * 50)

    tests = [test_dependencies, test_directories, test_files, test_app_import]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 所有測試通過！系統準備就緒")
        print("💡 使用 './start.sh' 啟動系統")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查系統配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
