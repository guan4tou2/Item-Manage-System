from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

#: Phase 44：直接使用 argon2-cffi（取代 passlib）。預設參數（argon2id、
#: t=3、m=64 MiB、p=4）與 passlib 既有雜湊相同，舊的 `$argon2id$…` 可直接驗證。
_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """驗證密碼；不相符或雜湊格式不合法都回 False，不丟例外。"""
    try:
        return _hasher.verify(hashed, plain)
    except (Argon2Error, InvalidHashError):
        return False
