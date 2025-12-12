"""使用者資料存取模組"""
from typing import Optional, Dict, Any

from app import mongo


def find_by_username(username: str) -> Optional[Dict[str, Any]]:
    """根據使用者名稱查詢使用者"""
    return mongo.db.user.find_one({"User": username})


def insert_user(user: Dict[str, Any]) -> None:
    """新增使用者"""
    mongo.db.user.insert_one(user)


def update_password(username: str, hashed_password: str) -> None:
    """更新使用者密碼"""
    mongo.db.user.update_one(
        {"User": username},
        {"$set": {"Password": hashed_password}}
    )


def mark_password_changed(username: str) -> None:
    """標記使用者已修改密碼"""
    mongo.db.user.update_one(
        {"User": username},
        {"$set": {"password_changed": True}}
    )


def mark_password_not_changed(username: str) -> None:
    """標記使用者需要修改密碼（用於密碼重置後）"""
    mongo.db.user.update_one(
        {"User": username},
        {"$set": {"password_changed": False}}
    )


def list_all_users() -> list:
    """取得所有使用者列表"""
    return list(mongo.db.user.find({}, {"_id": 0, "Password": 0}))


def record_login(username: str, ip_address: str, success: bool) -> None:
    """記錄登入歷史"""
    from datetime import datetime
    
    login_record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip_address,
        "success": success
    }
    
    # 添加到登入歷史（只保留最近 10 筆）
    mongo.db.user.update_one(
        {"User": username},
        {
            "$push": {
                "login_history": {
                    "$each": [login_record],
                    "$slice": -10
                }
            }
        }
    )
    
    if success:
        # 重置失敗次數
        mongo.db.user.update_one(
            {"User": username},
            {
                "$set": {
                    "failed_attempts": 0,
                    "locked_until": None,
                    "last_login": login_record["time"],
                    "last_login_ip": ip_address
                }
            }
        )
    else:
        # 增加失敗次數
        mongo.db.user.update_one(
            {"User": username},
            {"$inc": {"failed_attempts": 1}}
        )


def get_failed_attempts(username: str) -> int:
    """取得登入失敗次數"""
    user = mongo.db.user.find_one({"User": username}, {"failed_attempts": 1})
    if user:
        return user.get("failed_attempts", 0)
    return 0


def lock_account(username: str, until: str) -> None:
    """鎖定帳號"""
    mongo.db.user.update_one(
        {"User": username},
        {"$set": {"locked_until": until}}
    )


def get_lock_status(username: str) -> str:
    """取得帳號鎖定狀態"""
    user = mongo.db.user.find_one({"User": username}, {"locked_until": 1})
    if user:
        return user.get("locked_until")
    return None


def unlock_account(username: str) -> None:
    """解鎖帳號"""
    mongo.db.user.update_one(
        {"User": username},
        {"$set": {"failed_attempts": 0, "locked_until": None}}
    )


def get_login_history(username: str) -> list:
    """取得登入歷史"""
    user = mongo.db.user.find_one({"User": username}, {"login_history": 1})
    if user:
        return user.get("login_history", [])
    return []
