from typing import Optional, Dict, Any

from app import mongo


def find_by_username(username: str) -> Optional[Dict[str, Any]]:
    return mongo.db.user.find_one({"User": username})


def insert_user(user: Dict[str, Any]) -> None:
    mongo.db.user.insert_one(user)

