"""使用者服務模組"""
from typing import Optional, Tuple

from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories import user_repo

# 預設密碼（用於檢測是否需要強制修改）
DEFAULT_PASSWORD = "admin"


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
        "password_changed": True,  # 新用戶已自行設定密碼
    })
    return True


def needs_password_change(username: str) -> bool:
    """檢查使用者是否需要強制修改密碼
    
    以下情況需要修改：
    1. 使用者是 admin 且 password_changed 標記為 False 或不存在
    2. 使用者使用預設密碼登入
    """
    user = user_repo.find_by_username(username)
    if not user:
        return False
    
    # 檢查是否已標記為已修改密碼
    if user.get("password_changed", False):
        return False
    
    # admin 用戶首次登入需要修改
    if username == "admin":
        return True
    
    return False


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """修改使用者密碼
    
    Args:
        username: 使用者名稱
        old_password: 舊密碼
        new_password: 新密碼
    
    Returns:
        (成功與否, 訊息)
    """
    # 驗證舊密碼
    if not authenticate(username, old_password):
        return False, "舊密碼錯誤"
    
    # 驗證新密碼
    if len(new_password) < 6:
        return False, "新密碼至少需要 6 個字元"
    
    if new_password == old_password:
        return False, "新密碼不可與舊密碼相同"
    
    if new_password == DEFAULT_PASSWORD:
        return False, "不可使用預設密碼"
    
    # 更新密碼
    hashed = generate_password_hash(new_password)
    user_repo.update_password(username, hashed)
    
    # 標記為已修改密碼
    user_repo.mark_password_changed(username)
    
    return True, "密碼修改成功"


def force_change_password(username: str, new_password: str) -> Tuple[bool, str]:
    """強制修改密碼（首次登入時使用，不需驗證舊密碼）
    
    Args:
        username: 使用者名稱
        new_password: 新密碼
    
    Returns:
        (成功與否, 訊息)
    """
    # 驗證新密碼
    if len(new_password) < 6:
        return False, "新密碼至少需要 6 個字元"
    
    if new_password == DEFAULT_PASSWORD:
        return False, "不可使用預設密碼"
    
    # 更新密碼
    hashed = generate_password_hash(new_password)
    user_repo.update_password(username, hashed)
    
    # 標記為已修改密碼
    user_repo.mark_password_changed(username)
    
    return True, "密碼設定成功"


def admin_reset_password(target_username: str) -> Tuple[bool, str, str]:
    """管理員重置用戶密碼
    
    Args:
        target_username: 要重置密碼的使用者名稱
    
    Returns:
        (成功與否, 訊息, 新密碼)
    """
    user = user_repo.find_by_username(target_username)
    if not user:
        return False, "找不到該用戶", ""
    
    # 生成隨機密碼
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # 更新密碼
    hashed = generate_password_hash(new_password)
    user_repo.update_password(target_username, hashed)
    
    # 標記為需要修改密碼（下次登入時強制修改）
    user_repo.mark_password_not_changed(target_username)
    
    return True, f"已重置 {target_username} 的密碼", new_password


def list_users() -> list:
    """取得所有使用者列表"""
    return user_repo.list_all_users()
