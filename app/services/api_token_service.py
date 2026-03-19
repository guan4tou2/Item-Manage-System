"""API Token 服務模組"""
import hashlib
import json
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.repositories import api_token_repo


def _hash_token(token: str) -> str:
    """以 SHA-256 雜湊 token"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(
    user_id: str,
    name: str,
    scopes: Optional[List[str]] = None,
) -> Tuple[str, int]:
    """
    產生新的 API Token。
    回傳 (plaintext_token, token_id)。
    明文 token 只回傳一次，之後無法再取得。
    """
    plaintext = secrets.token_urlsafe(36)  # ~48 chars URL-safe
    token_hash = _hash_token(plaintext)
    prefix = plaintext[:8]
    scopes_json = json.dumps(scopes) if scopes else None

    token_id = api_token_repo.create_token(
        user_id=user_id,
        name=name,
        token_hash=token_hash,
        prefix=prefix,
        scopes=scopes_json,
    )
    return plaintext, token_id


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """
    驗證 token。
    成功時回傳 token dict（含 user_id），否則回傳 None。
    """
    if not token:
        return None

    token_hash = _hash_token(token)
    token_data = api_token_repo.find_by_hash(token_hash)
    if not token_data:
        return None

    if not token_data.get("is_active"):
        return None

    # 檢查是否過期
    expires_at = token_data.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                expires_at = None
        if expires_at and expires_at < datetime.utcnow():
            return None

    # 更新最後使用時間（非同步可接受，若失敗不影響驗證）
    try:
        api_token_repo.update_last_used(token_data["id"])
    except Exception:
        pass

    return token_data


def revoke_token(token_id, user_id: str) -> bool:
    """撤銷 token"""
    return api_token_repo.revoke_token(token_id, user_id)


def list_user_tokens(user_id: str) -> List[Dict[str, Any]]:
    """列出使用者的所有 token"""
    return api_token_repo.list_user_tokens(user_id)
