from typing import Optional

from app.repositories import user_repo


def authenticate(username: str, password: str) -> bool:
    user = user_repo.find_by_username(username)
    if not user:
        return False
    return user.get("User") == username and user.get("Password") == password


def get_user(username: str) -> Optional[dict]:
    return user_repo.find_by_username(username)

