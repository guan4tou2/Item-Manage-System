#!/usr/bin/env python
"""
測試通知服務腳本

這個腳本用於測試通知功能是否正常工作。
"""
import os
import sys
from datetime import date

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services import notification_service, email_service
from app.repositories import user_repo
from app.services import item_service


def test_notification_settings():
    """測試通知設定功能"""
    print("=" * 50)
    print("測試 1: 通知設定功能")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # 測試獲取設定
        settings = user_repo.get_notification_settings("admin")
        print(f"✅ 獲取設定成功: {settings}")
        
        # 測試更新設定
        user_repo.update_notification_settings(
            username="admin",
            email="test@example.com",
            notify_enabled=True,
            notify_days=30,
            notify_time="09:00"
        )
        print("✅ 更新設定成功")
        
        # 驗證設定
        settings = user_repo.get_notification_settings("admin")
        print(f"✅ 驗證設定: {settings}")
        
        # 測試獲取所有啟用通知的使用者
        users = user_repo.get_all_users_for_notification()
        print(f"✅ 啟用通知的使用者: {len(users)} 個")


def test_expiring_items():
    """測試到期物品檢測"""
    print("\n" + "=" * 50)
    print("測試 2: 到期物品檢測")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        expiry_info = item_service.get_expiring_items(days_threshold=30)
        print(f"✅ 總警報: {expiry_info['total_alerts']}")
        print(f"✅ 已過期: {expiry_info['expired_count']} 項")
        print(f"✅ 即將到期: {expiry_info['near_count']} 項")


def test_notification_summary():
    """測試通知摘要"""
    print("\n" + "=" * 50)
    print("測試 3: 通知摘要")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        summary = notification_service.get_notification_summary("admin")
        print(f"✅ 設定: {summary['settings']}")
        print(f"✅ 到期資訊: {expiry_info_summary(summary['expiry_info'])}")
        print(f"✅ 可以發送: {summary['can_send']}")


def test_email_configuration():
    """測試 Email 配置"""
    print("\n" + "=" * 50)
    print("測試 4: Email 配置")
    print("=" * 50)
    
    if email_service.is_email_configured():
        print("✅ Email 已配置")
        print(f"   伺服器: {email_service.MAIL_SERVER}")
        print(f"   埠號: {email_service.MAIL_PORT}")
        print(f"   使用者名稱: {email_service.MAIL_USERNAME}")
    else:
        print("❌ Email 未配置")
        print("   請設定環境變數:")
        print("   - MAIL_SERVER")
        print("   - MAIL_PORT")
        print("   - MAIL_USE_TLS")
        print("   - MAIL_USERNAME")
        print("   - MAIL_PASSWORD")


def expiry_info_summary(info):
    """格式化到期資訊摘要"""
    return {
        "total_alerts": info["total_alerts"],
        "expired_count": info["expired_count"],
        "near_count": info["near_count"],
    }


if __name__ == "__main__":
    print("\n🧪 開始測試通知服務\n")
    
    try:
        test_notification_settings()
        test_expiring_items()
        test_notification_summary()
        test_email_configuration()
        
        print("\n" + "=" * 50)
        print("✅ 所有測試完成")
        print("=" * 50)
        print("\n💡 提示:")
        print("   1. 如果 Email 未配置，請設定環境變數")
        print("   2. 啟動應用後，定時任務將自動執行")
        print("   3. 訪問 /notifications 設定通知偏好")
        print("")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
