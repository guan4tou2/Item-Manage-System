"""通知藍圖模組"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app

from app.services import notification_service
from app.repositories import user_repo

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/")
def index():
    """通知設定頁面"""
    if "UserID" not in session:
        return redirect(url_for("auth.signin"))
    
    summary = notification_service.get_notification_summary(session["UserID"])
    
    user_obj = user_repo.find_by_username(session["UserID"])
    
    line_link = None
    telegram_link = None
    try:
        from app import get_db_type
        if get_db_type() == "postgres":
            from app.models import LineUserLink, TelegramUserLink
            line_link = LineUserLink.query.filter_by(user_id=session["UserID"]).first()
            telegram_link = TelegramUserLink.query.filter_by(user_id=session["UserID"]).first()
    except Exception:
        pass
    telegram_bot_username = (current_app.config.get("TELEGRAM_BOT_USERNAME", "") or "").strip()
    integration = {
        "line_linked": bool(line_link),
        "telegram_linked": bool(telegram_link),
        "telegram_bind_available": bool(telegram_bot_username),
        "telegram_link_url": url_for("telegram.link") if telegram_bot_username else "",
        "line_bot_url": current_app.config.get("LINE_BOT_URL", ""),
    }

    return render_template(
        "notifications_settings.html",
        settings=summary["settings"],
        expiry_info=summary["expiry_info"],
        replacement_info=summary.get("replacement_info", {"due": [], "upcoming": [], "total_alerts": 0}),
        can_send=summary["can_send"],
        integration=integration,
        User={"id": session["UserID"], "name": session["UserID"], "admin": user_obj.get("admin", False) if user_obj else False},
    )


@bp.route("/api/settings", methods=["GET"])
def get_settings():
    """取得使用者通知設定"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    settings = user_repo.get_notification_settings(session["UserID"])
    return jsonify(settings)


@bp.route("/api/settings", methods=["POST"])
def update_settings():
    """更新使用者通知設定"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    
    email = data.get("email")
    notify_enabled = data.get("notify_enabled")
    notify_days = data.get("notify_days")
    notify_time = data.get("notify_time")
    notify_channels = data.get("notify_channels")
    reminder_ladder = data.get("reminder_ladder")
    replacement_enabled = data.get("replacement_enabled", True)
    replacement_intervals_raw = data.get("replacement_intervals")

    replacement_intervals = replacement_intervals_raw
    if isinstance(replacement_intervals_raw, str):
        parsed = []
        for part in replacement_intervals_raw.split(","):
            if "=" in part:
                name, days = part.split("=", 1)
                name = name.strip()
                try:
                    days_int = int(days.strip())
                    if name and days_int > 0:
                        parsed.append({"name": name, "days": days_int})
                except Exception:
                    continue
        replacement_intervals = parsed

    user_repo.update_notification_settings(
        username=session["UserID"],
        email=email,
        notify_enabled=notify_enabled,
        notify_days=notify_days,
        notify_time=notify_time,
        notify_channels=notify_channels,
        reminder_ladder=reminder_ladder,
        replacement_enabled=replacement_enabled,
        replacement_intervals=replacement_intervals,
    )
    
    return jsonify({"success": True, "message": "設定已更新"})
 

@bp.route("/api/send", methods=["POST"])
def send_notification():
    """手動發送通知"""
    if "UserID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    result = notification_service.send_manual_notification(session["UserID"])
    
    if result["success"]:
        flash("通知已送出到可用管道", "success")
    else:
        flash(f"發送失敗: {result['message']}", "error")
    
    return jsonify(result)
 

@bp.route("/api/summary", methods=["GET"])
def get_summary():
    """取得通知摘要"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    summary = notification_service.get_notification_summary(session["UserID"])
    return jsonify(summary)


# --- Web Push (PWA) ---------------------------------------------------------

from app.utils import push_service  # noqa: E402  – 需要在路由前可用


@bp.route("/api/vapid-public-key", methods=["GET"])
def vapid_public_key():
    """提供前端 Web Push 訂閱所需的 VAPID 公鑰。"""
    return jsonify({"publicKey": current_app.config.get("VAPID_PUBLIC_KEY", "")})


@bp.route("/subscribe", methods=["POST"])
def subscribe():
    """前端 Service Worker 推送訂閱端點。"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    payload = request.get_json(silent=True) or {}
    if not payload.get("endpoint"):
        return jsonify({"error": "Invalid subscription"}), 400
    push_service.add_subscription(session["UserID"], payload)
    return jsonify({"success": True})


@bp.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    """取消推送訂閱。"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    if not endpoint:
        return jsonify({"error": "Invalid endpoint"}), 400
    push_service.remove_subscription(session["UserID"], endpoint)
    return jsonify({"success": True})


@bp.route("/api/push-test", methods=["POST"])
def push_test():
    """寄一則測試推送給目前使用者（需有訂閱與 VAPID 設定）。"""
    if "UserID" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    result = push_service.send_push(
        session["UserID"],
        title="物品管理系統",
        body="這是一則測試推送通知 ✓",
        url="/notifications/",
    )
    return jsonify(result)
