"""共用認證工具模組"""
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import flash, redirect, request, session, url_for, g

from app.services import user_service


def _normalize_user_payload(user: Optional[Dict[str, Any]], user_id: Optional[str]) -> Dict[str, Any]:
    """統一模板可用的使用者欄位，避免不同頁面取值不一致。"""
    normalized = dict(user or {})
    normalized["User"] = normalized.get("User") or user_id
    normalized["name"] = normalized.get("name") or normalized.get("User") or ""
    normalized["admin"] = bool(normalized.get("admin", False))
    return normalized


def get_current_user() -> Dict[str, Any]:
    """取得當前登入使用者資訊"""
    user_id = session.get("UserID")
    if not user_id:
        return _normalize_user_payload(None, None)
    user = user_service.get_user(user_id)
    return _normalize_user_payload(user, user_id)


def login_required(f: Callable) -> Callable:
    """要求登入的裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "UserID" not in session:
            flash("請先登入", "warning")
            return redirect(url_for("auth.signin"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f: Callable) -> Callable:
    """要求管理員權限的裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "UserID" not in session:
            flash("請先登入", "warning")
            return redirect(url_for("auth.signin"))
        user = get_current_user()
        if not user.get("admin"):
            flash("需要管理員權限", "danger")
            return redirect(url_for("items.home"))
        return f(*args, **kwargs)
    return decorated_function


def api_token_or_login_required(f: Callable) -> Callable:
    """支援 Bearer token 或 session 登入的裝飾器。

    優先檢查 Authorization: Bearer <token> 標頭；
    若未提供則回落到 session-based login_required。
    成功驗證後會在 g.api_user_id 設定使用者 ID。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            from app.services import api_token_service
            from flask import jsonify
            token_data = api_token_service.validate_token(token)
            if not token_data:
                return jsonify({"error": "無效或已過期的 API Token"}), 401
            g.api_user_id = token_data.get("user_id", "")
            g.api_token_data = token_data
            return f(*args, **kwargs)

        # 回落到 session 驗證
        if "UserID" not in session:
            from flask import jsonify as _jsonify
            # 若為 API 請求（Accept: application/json）回傳 JSON；否則重導
            if request.is_json or "application/json" in request.headers.get("Accept", ""):
                return _jsonify({"error": "請先登入或提供有效的 API Token"}), 401
            flash("請先登入", "warning")
            return redirect(url_for("auth.signin"))

        g.api_user_id = session.get("UserID", "")
        return f(*args, **kwargs)
    return decorated_function
