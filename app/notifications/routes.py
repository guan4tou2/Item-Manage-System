"""通知藍圖模組"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.services import notification_service
from app.repositories import user_repo

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/")
@login_required
def index():
    """通知設定頁面"""
    summary = notification_service.get_notification_summary(current_user.id)
    
    return render_template(
        "notifications_settings.html",
        settings=summary["settings"],
        expiry_info=summary["expiry_info"],
        can_send=summary["can_send"],
        User=current_user,
    )


@bp.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    """取得使用者通知設定"""
    settings = user_repo.get_notification_settings(current_user.id)
    return jsonify(settings)


@bp.route("/api/settings", methods=["POST"])
@login_required
def update_settings():
    """更新使用者通知設定"""
    data = request.get_json()
    
    email = data.get("email")
    notify_enabled = data.get("notify_enabled")
    notify_days = data.get("notify_days")
    notify_time = data.get("notify_time")
    
    user_repo.update_notification_settings(
        username=current_user.id,
        email=email,
        notify_enabled=notify_enabled,
        notify_days=notify_days,
        notify_time=notify_time,
    )
    
    return jsonify({"success": True, "message": "設定已更新"})


@bp.route("/api/send", methods=["POST"])
@login_required
def send_notification():
    """手動發送通知"""
    result = notification_service.send_manual_notification(current_user.id)
    
    if result["success"]:
        flash(f"通知已發送到您的 Email", "success")
    else:
        flash(f"發送失敗: {result['message']}", "error")
    
    return jsonify(result)


@bp.route("/api/summary", methods=["GET"])
@login_required
def get_summary():
    """取得通知摘要"""
    summary = notification_service.get_notification_summary(current_user.id)
    return jsonify(summary)
