"""通知服務模組"""
from typing import Dict, Any, List
from datetime import datetime, date, timedelta

from app.repositories import user_repo
from app.services import item_service
from app.services import email_service


def check_and_send_notifications() -> Dict[str, Any]:
    """
    檢查並發送到期通知
    
    回傳:
        {
            "success_users": 成功發送的用戶數量,
            "failed_users": 失敗的用戶數量,
            "total_notifications": 總通知數,
            "details": 用戶詳細資訊列表
        }
    """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # 取得所有啟用通知的使用者
    users = user_repo.get_all_users_for_notification()
    
    results = {
        "success_users": 0,
        "failed_users": 0,
        "total_notifications": 0,
        "details": [],
    }
    
    for user in users:
        username = user.get("User")
        user_email = user.get("email", "")
        notify_days = user.get("notify_days", 30)
        notify_time = user.get("notify_time", "09:00")
        last_notification_date = user.get("last_notification_date", "")
        
        user_result = {
            "username": username,
            "email": user_email,
            "sent": False,
            "reason": "",
            "items_count": 0,
        }
        
        # 檢查今天是否已發送通知
        if last_notification_date == today_str:
            user_result["reason"] = "今日已發送通知"
            results["details"].append(user_result)
            continue
        
        # 檢查是否到達通知時間
        current_time = datetime.now().strftime("%H:%M")
        if current_time < notify_time:
            user_result["reason"] = "尚未到達通知時間"
            results["details"].append(user_result)
            continue
        
        # 取得到期物品
        expiry_info = item_service.get_expiring_items(days_threshold=notify_days)
        
        if expiry_info["total_alerts"] == 0:
            user_result["reason"] = "無到期物品"
            results["details"].append(user_result)
            continue
        
        # 發送通知
        sent = email_service.send_expiry_notification(
            to_email=user_email,
            expired_items=expiry_info["expired"],
            near_expiry_items=expiry_info["near_expiry"],
        )
        
        if sent:
            # 更新最後通知日期
            user_repo.update_last_notification_date(username, today_str)
            results["success_users"] += 1
            results["total_notifications"] += expiry_info["total_alerts"]
            user_result["sent"] = True
            user_result["items_count"] = expiry_info["total_alerts"]
        else:
            results["failed_users"] += 1
            user_result["reason"] = "發送失敗"
        
        results["details"].append(user_result)
    
    return results


def send_manual_notification(username: str) -> Dict[str, Any]:
    """
    手動發送通知給指定使用者
    
    參數:
        username: 使用者名稱
    
    回傳:
        {
            "success": 是否成功,
            "message": 訊息,
            "expired_count": 已過期數量,
            "near_count": 即將到期數量
        }
    """
    # 取得使用者設定
    settings = user_repo.get_notification_settings(username)
    
    if not settings.get("email"):
        return {
            "success": False,
            "message": "使用者未設定 Email",
            "expired_count": 0,
            "near_count": 0,
        }
    
    notify_days = settings.get("notify_days", 30)
    
    # 取得到期物品
    expiry_info = item_service.get_expiring_items(days_threshold=notify_days)
    
    if expiry_info["total_alerts"] == 0:
        return {
            "success": False,
            "message": "無到期物品",
            "expired_count": 0,
            "near_count": 0,
        }
    
    # 發送通知
    sent = email_service.send_expiry_notification(
        to_email=settings["email"],
        expired_items=expiry_info["expired"],
        near_expiry_items=expiry_info["near_expiry"],
    )
    
    if sent:
        today = date.today()
        user_repo.update_last_notification_date(username, today.strftime("%Y-%m-%d"))
    
    return {
        "success": sent,
        "message": "通知發送成功" if sent else "通知發送失敗",
        "expired_count": expiry_info["expired_count"],
        "near_count": expiry_info["near_count"],
    }


def get_notification_summary(username: str) -> Dict[str, Any]:
    """
    取得指定使用者的通知摘要
    
    參數:
        username: 使用者名稱
    
    回傳:
        {
            "settings": 使用者設定,
            "expiry_info": 到期資訊,
            "can_send": 是否可以發送通知
        }
    """
    settings = user_repo.get_notification_settings(username)
    notify_days = settings.get("notify_days", 30)
    
    expiry_info = item_service.get_expiring_items(days_threshold=notify_days)
    
    # 檢查今天是否已發送通知
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    last_sent = settings.get("last_notification_date", "")
    can_send = last_sent != today_str and expiry_info["total_alerts"] > 0
    
    return {
        "settings": settings,
        "expiry_info": expiry_info,
        "can_send": can_send,
    }
