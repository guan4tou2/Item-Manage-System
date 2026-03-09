"""共用認證工具模組"""
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import flash, redirect, session, url_for

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
