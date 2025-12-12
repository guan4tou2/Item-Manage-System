"""使用者服務模組"""
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories import user_repo


def authenticate(username: str, password: str) -> bool:
    """驗證使用者帳號密碼
    
    支援兩種模式：
    1. 雜湊密碼（安全模式）
    2. 明文密碼（僅供遷移期間使用，會自動升級為雜湊）
    """
    user = user_repo.find_by_username(username)
    if not user:
        return False
    
    if user.get("User") != username:
        return False
    
    stored_password = user.get("Password", "")
    
    # 檢查是否為雜湊密碼 (werkzeug 雜湊以特定格式開頭)
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, password)
    
    # 明文密碼比對（向後相容）
    # 如果驗證成功，自動升級為雜湊密碼
    if stored_password == password:
        _upgrade_password(username, password)
        return True
    
    return False


def _upgrade_password(username: str, plain_password: str) -> None:
    """將明文密碼升級為雜湊密碼"""
    hashed = generate_password_hash(plain_password)
    user_repo.update_password(username, hashed)


def hash_password(plain_password: str) -> str:
    """產生密碼雜湊"""
    return generate_password_hash(plain_password)


def get_user(username: str) -> Optional[dict]:
    """取得使用者資訊"""
    return user_repo.find_by_username(username)


def create_user(username: str, password: str, admin: bool = False) -> bool:
    """建立新使用者"""
    if user_repo.find_by_username(username):
        return False
    
    user_repo.insert_user({
        "User": username,
        "Password": generate_password_hash(password),
        "admin": admin,
    })
    return True
