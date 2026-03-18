"""通知服務模組"""
import json
from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from urllib import request as urlrequest

from flask import current_app

from app import get_db_type
from app.repositories import user_repo
from app.services import item_service
from app.services import email_service
from app.models import LineUserLink, TelegramUserLink


def _parse_reminder_ladder(value):
    if isinstance(value, list):
        return [int(v) for v in value if isinstance(v, int) or str(v).isdigit()]
    if isinstance(value, str):
        result = []
        for part in value.split(","):
            part = part.strip()
            if part.isdigit():
                result.append(int(part))
        return result
    return None


def _build_plain_notification_text(expiry_info: Dict[str, Any], replacement_info: Dict[str, Any]) -> str:
    lines = ["物品提醒摘要"]
    if expiry_info.get("expired"):
        lines.append(f"已過期 {len(expiry_info['expired'])} 項")
    if expiry_info.get("near_expiry"):
        lines.append(f"即將到期 {len(expiry_info['near_expiry'])} 項")
    if replacement_info.get("due"):
        lines.append(f"需保養 / 更換 {len(replacement_info['due'])} 項")
    if replacement_info.get("upcoming"):
        lines.append(f"即將保養 / 更換 {len(replacement_info['upcoming'])} 項")
    lines.append("請回到系統查看詳細清單。")
    return "\n".join(lines)


def _line_push(line_user_id: str, text: str) -> bool:
    token = current_app.config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not line_user_id:
        return False
    req = urlrequest.Request(
        url="https://api.line.me/v2/bot/message/push",
        data=json.dumps(
            {
                "to": line_user_id,
                "messages": [{"type": "text", "text": text[:1000]}],
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


def _telegram_send(chat_id: str, text: str) -> bool:
    token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return False
    req = urlrequest.Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


def _send_chat_notifications(username: str, channels: set[str], text: str) -> Dict[str, bool]:
    status = {"line": False, "telegram": False}
    if get_db_type() != "postgres":
        return status
    if "line" in channels:
        links = LineUserLink.query.filter_by(user_id=username).all()
        status["line"] = any(_line_push(link.line_user_id, text) for link in links)
    if "telegram" in channels:
        links = TelegramUserLink.query.filter_by(user_id=username).all()
        status["telegram"] = any(_telegram_send(link.chat_id, text) for link in links)
    return status


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
        notify_channels = user.get("notify_channels", []) or ["email"]
        reminder_ladder = user.get("reminder_ladder")
        last_notification_date = user.get("last_notification_date", "")
        
        user_result = {
            "username": username,
            "email": user_email,
            "sent": False,
            "reason": "",
            "items_count": 0,
        }
        
        if not username:
            user_result["reason"] = "找不到使用者"
            results["details"].append(user_result)
            continue
        
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
        
        expiry_info = item_service.get_expiring_items(
            days_threshold=notify_days,
            ladder=_parse_reminder_ladder(reminder_ladder),
        )
        replacement_info = item_service.get_replacement_items(user)
        total_alerts = expiry_info["total_alerts"] + replacement_info["total_alerts"]
        
        if total_alerts == 0:
            user_result["reason"] = "無到期或保養提醒"
            results["details"].append(user_result)
            continue
        
        # 發送通知
        sent = False
        channel_status = {"email": False, "line": False, "telegram": False}
        if "email" in notify_channels:
            if user_email:
                channel_status["email"] = email_service.send_expiry_notification(
                    to_email=user_email,
                    expired_items=expiry_info["expired"],
                    near_expiry_items=expiry_info["near_expiry"],
                    replacement_due=replacement_info["due"],
                    replacement_upcoming=replacement_info["upcoming"],
                )
        chat_status = _send_chat_notifications(
            username,
            set(notify_channels or []),
            _build_plain_notification_text(expiry_info, replacement_info),
        )
        channel_status.update(chat_status)
        sent = any(channel_status.values())
        
        if sent:
            # 更新最後通知日期
            user_repo.update_last_notification_date(username, today_str)
            results["success_users"] += 1
            results["total_notifications"] += total_alerts
            user_result["sent"] = True
            user_result["items_count"] = total_alerts
        else:
            results["failed_users"] += 1
            user_result["reason"] = "發送失敗"
        user_result["channel_status"] = channel_status
        
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
    
    notify_days = settings.get("notify_days", 30)
    notify_channels = settings.get("notify_channels", []) or ["email"]
    reminder_ladder = settings.get("reminder_ladder")
    
    # 取得到期物品
    expiry_info = item_service.get_expiring_items(
        days_threshold=notify_days,
        ladder=_parse_reminder_ladder(reminder_ladder),
    )
    
    replacement_info = item_service.get_replacement_items(settings)
    total_alerts = expiry_info["total_alerts"] + replacement_info["total_alerts"]

    if total_alerts == 0:
        return {
            "success": False,
            "message": "無到期或保養提醒",
            "expired_count": 0,
            "near_count": 0,
            "replacement_due_count": 0,
            "replacement_upcoming_count": 0,
        }
    
    # 發送通知
    sent = False
    channel_status = {"email": False, "line": False, "telegram": False}
    if "email" in notify_channels:
        if settings.get("email"):
            channel_status["email"] = email_service.send_expiry_notification(
                to_email=settings["email"],
                expired_items=expiry_info["expired"],
                near_expiry_items=expiry_info["near_expiry"],
                replacement_due=replacement_info["due"],
                replacement_upcoming=replacement_info["upcoming"],
            )

    chat_status = _send_chat_notifications(
        username,
        set(notify_channels),
        _build_plain_notification_text(expiry_info, replacement_info),
    )
    channel_status.update(chat_status)
    sent = any(channel_status.values())
    
    if sent:
        today = date.today()
        user_repo.update_last_notification_date(username, today.strftime("%Y-%m-%d"))
    
    return {
        "success": sent,
        "message": "通知發送成功" if sent else "通知發送失敗",
        "expired_count": expiry_info["expired_count"],
        "near_count": expiry_info["near_count"],
        "replacement_due_count": len(replacement_info["due"]),
        "replacement_upcoming_count": len(replacement_info["upcoming"]),
        "channel_status": channel_status,
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
    reminder_ladder = settings.get("reminder_ladder")
    
    expiry_info = item_service.get_expiring_items(
        days_threshold=notify_days,
        ladder=_parse_reminder_ladder(reminder_ladder),
    )

    replacement_info = item_service.get_replacement_items(settings)
    combined_total = expiry_info["total_alerts"] + replacement_info["total_alerts"]
    
    # 檢查今天是否已發送通知
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    last_sent = settings.get("last_notification_date", "")
    can_send = last_sent != today_str and combined_total > 0
    
    return {
        "settings": settings,
        "expiry_info": expiry_info,
        "replacement_info": replacement_info,
        "can_send": can_send,
    }
