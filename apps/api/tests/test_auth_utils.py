import pytest
from datetime import timedelta

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_token, decode_token, TokenError


def test_hash_password_is_not_plaintext():
    hashed = hash_password("secret1234")
    assert hashed != "secret1234"
    assert hashed.startswith("$argon2")


def test_verify_password_accepts_correct():
    hashed = hash_password("secret1234")
    assert verify_password("secret1234", hashed) is True


def test_verify_password_rejects_wrong():
    hashed = hash_password("secret1234")
    assert verify_password("wrong-pass", hashed) is False


def test_create_and_decode_token_roundtrip():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"


def test_decode_rejects_wrong_type():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="refresh")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_decode_rejects_tampered_token():
    token = create_token(subject="user-id-1", ttl=timedelta(minutes=5), token_type="access")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(TokenError):
        decode_token(tampered, expected_type="access")
