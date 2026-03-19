"""API Token 管理路由"""
from flask import Blueprint, jsonify, render_template, request, session

from app.utils.auth import login_required, get_current_user
from app.services import api_token_service

bp = Blueprint("tokens", __name__)

AVAILABLE_SCOPES = [
    ("items:read", "讀取物品"),
    ("items:write", "新增/修改物品"),
    ("items:delete", "刪除物品"),
]


@bp.route("/settings/api-tokens")
@login_required
def token_management():
    """API Token 管理頁面"""
    user = get_current_user()
    user_id = session.get("UserID", "")
    tokens = api_token_service.list_user_tokens(user_id)
    return render_template(
        "api_tokens.html",
        User=user,
        tokens=tokens,
        available_scopes=AVAILABLE_SCOPES,
    )


@bp.route("/api/tokens/create", methods=["POST"])
@login_required
def create_token():
    """建立新 API Token，回傳明文 token（僅一次）"""
    user_id = session.get("UserID", "")
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Token 名稱不能為空"}), 400

    scopes = data.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    # 限制每人最多 10 個 token
    existing = api_token_service.list_user_tokens(user_id)
    active_count = sum(1 for t in existing if t.get("is_active"))
    if active_count >= 10:
        return jsonify({"error": "已達到 Token 上限（每人最多 10 個）"}), 400

    plaintext, token_id = api_token_service.generate_token(
        user_id=user_id,
        name=name,
        scopes=scopes,
    )

    return jsonify({
        "ok": True,
        "token": plaintext,
        "token_id": token_id,
        "name": name,
        "prefix": plaintext[:8],
    }), 201


@bp.route("/api/tokens/revoke/<int:token_id>", methods=["POST"])
@login_required
def revoke_token(token_id: int):
    """撤銷 API Token"""
    user_id = session.get("UserID", "")
    success = api_token_service.revoke_token(token_id, user_id)
    if success:
        return jsonify({"ok": True})
    return jsonify({"error": "找不到 Token 或無權限撤銷"}), 404
