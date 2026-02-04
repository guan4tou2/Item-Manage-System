"""通知藍圖模組"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session

from app import csrf
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
    
    return render_template(
        "notifications_settings.html",
        settings=summary["settings"],
        expiry_info=summary["expiry_info"],
        can_send=summary["can_send"],
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
@csrf.exempt
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
@csrf.exempt
def send_notification():
    """手動發送通知"""
    if "UserID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    result = notification_service.send_manual_notification(session["UserID"])
    
    if result["success"]:
        flash(f"通知已發送到您的 Email", "success")
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
