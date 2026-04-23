#!/usr/bin/env python3
"""產生 Web Push 所需的 VAPID 金鑰對。

用法::

    uv run python scripts/generate_vapid_keys.py

或指定輸出 ``.env`` 區段::

    uv run python scripts/generate_vapid_keys.py --env

把輸出的兩個 base64url 字串塞進環境變數：

    VAPID_PUBLIC_KEY=...
    VAPID_PRIVATE_KEY=...
    VAPID_SUBJECT=mailto:you@example.com
"""

from __future__ import annotations

import argparse
import base64
import sys


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_keys() -> tuple[str, str]:
    """回傳 (public_key, private_key) 兩個 base64url 字串。"""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "需要 cryptography 套件。請先安裝：\n  uv pip install cryptography"
        ) from exc

    private = ec.generate_private_key(ec.SECP256R1())

    # 私鑰：32 bytes 大端整數
    raw_private = private.private_numbers().private_value.to_bytes(32, "big")

    # 公鑰：未壓縮 65 bytes (0x04 || X || Y)
    raw_public = private.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    return _b64url(raw_public), _b64url(raw_private)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate VAPID key pair for Web Push.")
    parser.add_argument("--env", action="store_true", help="以 .env 格式輸出")
    parser.add_argument(
        "--subject",
        default="mailto:admin@example.com",
        help="VAPID subject（mailto: 或 https://）",
    )
    args = parser.parse_args(argv)

    public_key, private_key = generate_keys()

    if args.env:
        print(f"VAPID_PUBLIC_KEY={public_key}")
        print(f"VAPID_PRIVATE_KEY={private_key}")
        print(f"VAPID_SUBJECT={args.subject}")
    else:
        print("Public key (前端使用):")
        print(f"  {public_key}")
        print()
        print("Private key (後端保留):")
        print(f"  {private_key}")
        print()
        print("Subject:")
        print(f"  {args.subject}")
        print()
        print("把以下三個變數加入 .env：")
        print(f"  VAPID_PUBLIC_KEY={public_key}")
        print(f"  VAPID_PRIVATE_KEY={private_key}")
        print(f"  VAPID_SUBJECT={args.subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
