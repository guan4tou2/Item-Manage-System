"""通用驗證工具模組"""
from typing import List


def validate_password_strength(password: str) -> List[str]:
    """Validate password meets minimum strength requirements.

    Returns a list of error messages; empty list means the password is valid.
    """
    errors = []
    if len(password) < 8:
        errors.append("密碼至少需要 8 個字元")
    if not any(c.isupper() for c in password):
        errors.append("密碼需包含至少一個大寫字母")
    if not any(c.islower() for c in password):
        errors.append("密碼需包含至少一個小寫字母")
    if not any(c.isdigit() for c in password):
        errors.append("密碼需包含至少一個數字")
    return errors
