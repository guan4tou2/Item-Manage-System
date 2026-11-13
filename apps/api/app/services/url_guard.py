"""Webhook 出站 URL 防護（Phase 44 D10–D12，防 SSRF）。

兩道檢查，皆為純函式（DNS 解析可注入／可 mock）：

1. `validate_webhook_url`：寫入時（schema validator）。只看字面，**不做 DNS**。
2. `resolve_safe_addresses`：送出時。解析 DNS，所有結果都必須是全域位址；
   呼叫端再把連線釘在已驗證的 IP（避免 DNS rebinding 的 TOCTOU）。

`WEBHOOK_ALLOW_PRIVATE_HOSTS=true`（D12）時略過「私有位址」限制，但仍只允許
http／https、不得帶 userinfo、必須有 host。
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit

from app.config import get_settings

#: 寫入時驗證失敗的固定訊息（前端以此字串辨識，勿隨意更動）。
URL_NOT_ALLOWED_MESSAGE = "webhook_url_not_allowed"
#: 送出時被擋下的固定 excerpt（不得包含解析到的 IP 或其他內部資訊）。
DESTINATION_NOT_ALLOWED_EXCERPT = "error: destination not allowed"

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal")

# Python 的 is_global 對下列內嵌 IPv4 的轉換網段不一定判為非全域，一律視為不可信。
_BLOCKED_V6_NETWORKS = tuple(
    ipaddress.ip_network(n)
    for n in (
        "::/96",  # IPv4-compatible（已棄用）：`::7f00:1` 會被 is_global 判為全域
        "64:ff9b::/96",  # NAT64：可轉到任意 IPv4（含內網）
        "64:ff9b:1::/48",
        "2002::/16",  # 6to4：內嵌 IPv4
        "2001::/32",  # Teredo
    )
)

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class UnsafeUrlError(ValueError):
    """URL 或其解析結果不被允許。訊息固定，不含內部細節。"""

    def __init__(self) -> None:
        super().__init__(URL_NOT_ALLOWED_MESSAGE)


def allow_private_hosts() -> bool:
    return bool(get_settings().webhook_allow_private_hosts)


def is_public_address(ip: IPAddress) -> bool:
    """是否為可對外路由的全域單播位址。IPv4-mapped IPv6 先還原為 IPv4 判斷。"""
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif any(ip in net for net in _BLOCKED_V6_NETWORKS):
            return False
    if ip.is_multicast or ip.is_unspecified or ip.is_loopback or ip.is_link_local:
        return False
    return ip.is_global


def _split(url: str) -> tuple[SplitResult, str]:
    """解析並做與位址無關的結構檢查；回傳 (parts, 正規化 host)。"""
    if not isinstance(url, str) or url != url.strip() or not url:
        raise UnsafeUrlError()
    try:
        parts = urlsplit(url)
        _ = parts.port  # 非法 port 會在此丟 ValueError
    except ValueError:
        raise UnsafeUrlError() from None
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError()
    # userinfo：netloc 內任何 "@" 都拒絕（含空的 "@host"）
    if "@" in parts.netloc:
        raise UnsafeUrlError()
    host = (parts.hostname or "").rstrip(".")
    if not host or "%" in host:  # 無 host；或 IPv6 zone id
        raise UnsafeUrlError()
    return parts, host.lower()


def _literal_ip(host: str) -> IPAddress | None:
    """host 若為 IP 字面值回傳位址；非標準寫法（十進位／八進位／十六進位、
    省略段如 `127.1`）直接拒絕，因為 resolver 會把它們當成 IPv4。"""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        socket.inet_aton(host)  # 接受 2130706433、0x7f.1、0177.0.0.1、127.1
    except OSError:
        return None
    raise UnsafeUrlError()


def validate_webhook_url(url: str) -> str:
    """寫入時檢查（不做 DNS）。通過回傳原字串，否則丟 `UnsafeUrlError`。"""
    _parts, host = _split(url)
    ip = _literal_ip(host)
    if allow_private_hosts():
        return url
    if ip is not None:
        if not is_public_address(ip):
            raise UnsafeUrlError()
    elif host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError()
    return url


async def resolve_host(host: str, port: int) -> list[IPAddress]:
    """以 event loop 的 getaddrinfo 解析（不阻塞）。失敗丟 OSError。"""
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    out: list[IPAddress] = []
    for _family, _type, _proto, _canon, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
        if ip not in out:
            out.append(ip)
    return out


def is_destination_allowed_sync(url: str) -> bool:
    """同步版送出時檢查（給同步的 pywebpush 路徑用）。

    只回答「現在能不能送」；無法像 webhook 一樣釘住 IP（連線由 pywebpush／requests
    自行建立），因此對 DNS rebinding 僅有降低、沒有消除。結構不合格、DNS 失敗、
    任一解析結果非全域位址 → False。
    """
    try:
        parts, host = _split(url)
        literal = _literal_ip(host)
        if literal is not None:
            addrs: list[IPAddress] = [literal]
        else:
            port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            addrs = [
                ipaddress.ip_address(info[4][0].split("%", 1)[0]) for info in infos
            ]
    except (OSError, ValueError):  # UnsafeUrlError 是 ValueError 的子類
        return False
    if not addrs:
        return False
    return allow_private_hosts() or all(is_public_address(a) for a in addrs)


async def resolve_safe_addresses(url: str) -> tuple[SplitResult, str, list[IPAddress]]:
    """送出時檢查：回傳 (parts, host, 已驗證位址清單)。

    - 結構不合格或任一解析結果非全域位址 → `UnsafeUrlError`
    - DNS 本身失敗 → 原樣丟 `OSError`（屬一般網路失敗，由呼叫端照常記錄）
    opt-in（D12）時不檢查位址，但仍回傳解析結果供釘 IP。
    """
    parts, host = _split(url)
    port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    literal = _literal_ip(host)
    addrs = [literal] if literal is not None else await resolve_host(host, port)
    if not addrs:
        raise OSError("no address")
    if not allow_private_hosts() and not all(is_public_address(a) for a in addrs):
        raise UnsafeUrlError()
    return parts, host, addrs
