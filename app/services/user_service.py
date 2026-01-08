"""使用者服務模組"""
from typing import Optional, Tuple
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories import user_repo
from app.services import log_service

# 預設密碼（用於檢測是否需要強制修改）
DEFAULT_PASSWORD = "admin"

# 登入失敗鎖定設定
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def is_account_locked(username: str) -> Tuple[bool, str]:
    """檢查帳號是否被鎖定
    
    Returns:
        (是否鎖定, 解鎖時間或訊息)
    """
    locked_until = user_repo.get_lock_status(username)
    
    if locked_until:
        try:
            lock_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < lock_time:
                remaining = (lock_time - datetime.now()).seconds // 60
                return True, f"帳號已被鎖定，請在 {remaining + 1} 分鐘後重試"
            else:
                # 已過鎖定時間，解鎖
                user_repo.unlock_account(username)
        except Exception:
            pass
    
    return False, ""


def authenticate(username: str, password: str, ip_address: str = "") -> Tuple[bool, str]:
    """驗證使用者帳號密碼
    
    支援兩種模式：
    1. 雜湊密碼（安全模式）
    2. 明文密碼（僅供遷移期間使用，會自動升級為雜湊）
    
    Returns:
        (是否成功, 錯誤訊息)
    """
    # 檢查帳號是否被鎖定
    locked, message = is_account_locked(username)
    if locked:
        return False, message
    
    user = user_repo.find_by_username(username)
    if not user:
        return False, "帳號或密碼錯誤"
    
    if user.get("User") != username:
        return False, "帳號或密碼錯誤"
    
    stored_password = user.get("Password", "")
    success = False
    
    # 檢查是否為雜湊密碼 (werkzeug 雜湊以特定格式開頭)
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        success = check_password_hash(stored_password, password)
    else:
        # 明文密碼比對（向後相容）
        if stored_password == password:
            _upgrade_password(username, password)
            success = True
    
    # 記錄登入歷史
    user_repo.record_login(username, ip_address, success)
    
    if success:
        return True, ""
    else:
        # 檢查失敗次數
        failed_attempts = user_repo.get_failed_attempts(username)
        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            # 鎖定帳號
            lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            user_repo.lock_account(username, lock_until)
            
            # 記錄安全性事件
            log_service.log_action("security", "SYSTEM", details={
                "message": f"帳號 {username} 因登入失敗次數過多被鎖定",
                "username": username,
                "ip": ip_address
            })
            
            return False, f"登入失敗次數過多，帳號已被鎖定 {LOCKOUT_DURATION_MINUTES} 分鐘"
        
        remaining = MAX_FAILED_ATTEMPTS - failed_attempts
        return False, f"帳號或密碼錯誤（還有 {remaining} 次機會）"


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
    # 檢查是否已存在（區分大小寫）
    if user_repo.find_by_username(username):
        return False

    # 檢查是否已存在（不區分大小寫，防止混淆）
    if user_repo.find_by_username_case_insensitive(username):
        return False

    # 驗證新密碼強度
    ok, msg = validate_new_password(password)
    if not ok:
        return False

    user_repo.insert_user({
        "User": username,
        "Password": generate_password_hash(password),
        "admin": admin,
        "password_changed": True,  # 新用戶已自行設定密碼
    })
    return True


def validate_new_password(password: str) -> Tuple[bool, str]:
    """驗證新密碼是否符合強度要求"""
    if len(password) < 8:
        return False, "密碼至少需要 8 個字元"
    
    import re
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return False, "密碼必須包含至少一個字母與一個數字"
    
    return True, ""


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
    ok, msg = validate_new_password(new_password)
    if not ok:
        return False, msg
    
    if new_password == old_password:
        return False, "新密碼不可與舊密碼相同"
    
    if new_password == DEFAULT_PASSWORD:
        return False, "不可使用預設密碼"
    
    # 更新密碼
    hashed = generate_password_hash(new_password)
    user_repo.update_password(username, hashed)
    
    # 標記為已修改密碼
    user_repo.mark_password_changed(username)
    
    # 記錄操作
    log_service.log_action("update", username, details={"message": "修改個人密碼"})
    
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
    ok, msg = validate_new_password(new_password)
    if not ok:
        return False, msg
    
    if new_password == DEFAULT_PASSWORD:
        return False, "不可使用預設密碼"
    
    # 更新密碼
    hashed = generate_password_hash(new_password)
    user_repo.update_password(username, hashed)
    
    # 標記為已修改密碼
    user_repo.mark_password_changed(username)
    
    # 記錄操作
    log_service.log_action("update", username, details={"message": "首次登入設定密碼"})
    
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
    
    # 記錄安全性事件
    from flask import session
    admin_user = session.get("UserID", "ADMIN")
    log_service.log_action("security", admin_user, target_username, details={
        "message": f"管理員重置了使用者 {target_username} 的密碼"
    })
    
    return True, f"已重置 {target_username} 的密碼", new_password


def list_users() -> list:
    """取得所有使用者列表"""
    return user_repo.list_all_users()


def get_login_history(username: str) -> list:
    """取得使用者登入歷史"""
    return user_repo.get_login_history(username)


def unlock_user(username: str) -> bool:
    """解鎖使用者帳號"""
    user = user_repo.find_by_username(username)
    if not user:
        return False
    user_repo.unlock_account(username)
    return True
