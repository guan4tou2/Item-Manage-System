"""共用認證工具模組"""
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import flash, redirect, session, url_for

from app.services import user_service


def get_current_user() -> Dict[str, Any]:
    """取得當前登入使用者資訊"""
    user_id = session.get("UserID")
    if not user_id:
        return {"User": None, "admin": False}
    user = user_service.get_user(user_id)
    return user or {"User": user_id, "admin": False}


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

