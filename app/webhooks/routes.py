"""Webhook 管理路由"""
import json
import secrets

from flask import Blueprint, render_template, request, jsonify
from flask_babel import gettext as _

from app.utils.auth import login_required, admin_required, get_current_user
from app.repositories import webhook_repo
from app.services import webhook_service

bp = Blueprint("webhooks", __name__)

ALL_EVENTS = [
    "item.created",
    "item.updated",
    "item.deleted",
    "item.quantity.changed",
]


@bp.route("/settings/webhooks")
@admin_required
def webhook_list():
    """Webhook 管理頁面"""
    user = get_current_user()
    user_id = user.get("User", "")
    webhooks = webhook_repo.list_user_webhooks(user_id)
    return render_template(
        "webhooks.html",
        User=user,
        webhooks=webhooks,
        all_events=ALL_EVENTS,
    )


@bp.route("/api/webhooks", methods=["POST"])
@admin_required
def create_webhook():
    """API: 建立 webhook"""
    user = get_current_user()
    user_id = user.get("User", "")

    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    events = data.get("events") or []
    secret = (data.get("secret") or "").strip()

    if not url:
        return jsonify({"success": False, "message": _("請填寫 URL")}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"success": False, "message": _("URL 必須以 http:// 或 https:// 開頭")}), 400
    if not secret:
        secret = secrets.token_hex(20)

    # Validate events
    valid_events = [e for e in events if e in ALL_EVENTS]

    wh_id = webhook_service.create_webhook(user_id, url, valid_events, secret)
    return jsonify({"success": True, "id": wh_id, "secret": secret})


@bp.route("/api/webhooks/<int:webhook_id>/delete", methods=["POST"])
@admin_required
def delete_webhook(webhook_id: int):
    """API: 刪除 webhook"""
    user = get_current_user()
    user_id = user.get("User", "")

    ok = webhook_service.delete_webhook(webhook_id, user_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "message": _("找不到 Webhook 或無權限")}), 404


@bp.route("/api/webhooks/<int:webhook_id>/test", methods=["POST"])
@admin_required
def test_webhook(webhook_id: int):
    """API: 傳送測試事件"""
    user = get_current_user()
    user_id = user.get("User", "")

    ok = webhook_service.test_webhook(webhook_id, user_id)
    if ok:
        return jsonify({"success": True, "message": _("測試事件已成功傳送")})
    return jsonify({"success": False, "message": _("測試傳送失敗，請確認 URL 是否正確")}), 400
