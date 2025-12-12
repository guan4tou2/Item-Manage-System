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
