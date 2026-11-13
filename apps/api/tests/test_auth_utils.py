import base64
import json
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_token, decode_token, token_version, TokenError
from app.config import get_settings
from app.services.auth_service import _DUMMY_PASSWORD_HASH

#: Phase 44：passlib 1.7.4 `CryptContext(schemes=["argon2"])` 對 "legacy-pass-123"
#: 產生的雜湊（汰換 passlib 前寫死），確認既有資料免遷移即可驗證。
_PASSLIB_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$MwagVOq9N6aUUqoVAsBYSw"
    "$faH2HI5un822Ew9xC+rPAEok2/ULZhgYNjbpRZyOdCc"
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("secret1234")
    assert hashed != "secret1234"
    assert hashed.startswith("$argon2id$")


def test_verify_password_accepts_correct():
    hashed = hash_password("secret1234")
    assert verify_password("secret1234", hashed) is True


def test_verify_password_rejects_wrong():
    hashed = hash_password("secret1234")
    assert verify_password("wrong-pass", hashed) is False


def test_verify_password_accepts_legacy_passlib_hash():
    assert verify_password("legacy-pass-123", _PASSLIB_HASH) is True
    assert verify_password("legacy-pass-124", _PASSLIB_HASH) is False


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "not-a-hash",
        "$argon2id$garbage",
        "$2b$12$abcdefghijklmnopqrstuv",
        "$argon2id$v=19$m=65536,t=3,p=4$MwagVOq9N6aUUqoVAsBYSw$AAAA",
    ],
)
def test_verify_password_malformed_hash_returns_false(bad):
    assert verify_password("anything", bad) is False


def test_dummy_hash_runs_full_argon2_verification():
    """timing 防護：dummy hash 必須是可解析的合法雜湊，驗證會真的跑完 Argon2
    （得到 VerifyMismatchError，而非格式錯誤的快速失敗）。"""
    with pytest.raises(VerifyMismatchError):
        PasswordHasher().verify(_DUMMY_PASSWORD_HASH, "whatever-user-typed")
    assert verify_password("whatever-user-typed", _DUMMY_PASSWORD_HASH) is False


def test_create_and_decode_token_roundtrip():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"
    assert token_version(payload) == 0


def test_create_token_carries_version():
    token = create_token(
        subject="user-id-1", ttl=timedelta(minutes=5), token_type="refresh", version=3
    )
    assert token_version(decode_token(token, expected_type="refresh")) == 3


def test_token_without_ver_is_version_zero():
    assert token_version({"sub": "x"}) == 0


@pytest.mark.parametrize("ver", ["1", 1.0, True, None])
def test_token_version_rejects_non_int(ver):
    with pytest.raises(TokenError):
        token_version({"sub": "x", "ver": ver})


def test_decode_rejects_wrong_type():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="refresh")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_decode_rejects_tampered_token():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(TokenError):
        decode_token(tampered, expected_type="access")


def test_decode_rejects_expired_token():
    token = create_token(subject="user-id-1", ttl=timedelta(seconds=-10), token_type="access")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def _claims() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": "user-id-1",
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def test_decode_rejects_alg_none():
    unsigned = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(_claims())}."
    with pytest.raises(TokenError):
        decode_token(unsigned, expected_type="access")


@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
def test_decode_rejects_other_hmac_algorithm():
    """同一把密鑰、不同演算法（HS512）也不接受：algorithms 白名單只有設定值。"""
    token = pyjwt.encode(_claims(), get_settings().jwt_secret, algorithm="HS512")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_decode_rejects_token_without_exp():
    claims = _claims()
    del claims["exp"]
    token = pyjwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")
