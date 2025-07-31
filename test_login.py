#!/usr/bin/env python3
"""
登入測試腳本
"""

import sys

import requests


def test_login():
    """測試登入功能"""
    print("🔐 測試登入功能...")

    # 測試正確的登入資訊
    login_data = {"UserID": "admin", "Password": "admin"}

    try:
        response = requests.post("http://localhost:8080/signin", data=login_data)

        if response.status_code == 200:
            if "Redirecting" in response.text or "home" in response.text:
                print("✅ 登入成功！")
                return True
            else:
                print("❌ 登入失敗 - 沒有重定向到首頁")
                return False
        else:
            print(f"❌ 登入失敗 - HTTP狀態碼: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到應用程式，請確保應用程式正在運行")
        return False
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_mongodb_connection():
    """測試MongoDB連接"""
    print("🗄️ 測試MongoDB連接...")

    try:
        import pymongo

        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client.myDB
        user = db.user.find_one({"User": "admin"})

        if user:
            print("✅ MongoDB連接成功，找到admin使用者")
            return True
        else:
            print("❌ MongoDB連接成功，但找不到admin使用者")
            return False

    except Exception as e:
        print(f"❌ MongoDB連接失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔍 登入功能測試")
    print("=" * 50)

    # 測試MongoDB連接
    mongodb_ok = test_mongodb_connection()
    print()

    # 測試登入功能
    login_ok = test_login()
    print()

    print("=" * 50)
    if mongodb_ok and login_ok:
        print("🎉 所有測試通過！登入功能正常")
        print("💡 您現在可以使用以下資訊登入：")
        print("   網址: http://localhost:8080")
        print("   帳號: admin")
        print("   密碼: admin")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查系統配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
