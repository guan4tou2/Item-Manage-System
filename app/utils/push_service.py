"""伺服端 Web Push 推送服務。

設計重點：
- 訂閱以 ``UserID -> [subscription, ...]`` 結構儲存到 JSON 檔（``instance/push_subs.json``），
  簡單且不需要新增資料庫遷移；之後若要升級可改成 SQLAlchemy Model。
- ``send_push`` 內部使用 ``pywebpush``，未安裝套件 / 未設定 VAPID 時優雅降級。
- 408/410（訂閱失效）會自動清除該筆失效訂閱。

設定來源 (Flask config)：
- ``VAPID_PUBLIC_KEY``、``VAPID_PRIVATE_KEY``、``VAPID_SUBJECT``。

對外介面：
- ``add_subscription(user_id, subscription)``
- ``remove_subscription(user_id, endpoint)``
- ``list_subscriptions(user_id)``
- ``send_push(user_id, title, body, url=None) -> dict``
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Iterable

try:
    from flask import current_app
except Exception:  # pragma: no cover
    current_app = None  # type: ignore[assignment]


_LOCK = threading.Lock()


def _store_path() -> Path:
    """取得訂閱檔路徑；置於專案 ``instance/`` 內。"""
    if current_app is not None:
        try:
            base = Path(current_app.instance_path)
        except Exception:
            base = Path("instance")
    else:
        base = Path("instance")
    base.mkdir(parents=True, exist_ok=True)
    return base / "push_subs.json"


def _load() -> dict[str, list[dict]]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save(data: dict[str, list[dict]]) -> None:
    path = _store_path()
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)


# --- public API -------------------------------------------------------------


def add_subscription(user_id: str, subscription: dict) -> bool:
    """新增訂閱。重複的 endpoint 會被忽略。"""
    if not user_id or not isinstance(subscription, dict):
        return False
    endpoint = subscription.get("endpoint")
    if not endpoint:
        return False
    with _LOCK:
        data = _load()
        subs = data.setdefault(user_id, [])
        if not any(s.get("endpoint") == endpoint for s in subs):
            subs.append(subscription)
            _save(data)
    return True


def remove_subscription(user_id: str, endpoint: str) -> bool:
    if not user_id or not endpoint:
        return False
    with _LOCK:
        data = _load()
        if user_id not in data:
            return False
        before = len(data[user_id])
        data[user_id] = [s for s in data[user_id] if s.get("endpoint") != endpoint]
        if len(data[user_id]) == before:
            return False
        if not data[user_id]:
            data.pop(user_id, None)
        _save(data)
    return True


def list_subscriptions(user_id: str) -> list[dict]:
    return list(_load().get(user_id, []))


def _config_get(key: str, default: str = "") -> str:
    """安全讀取 Flask config；無 app context 時退回環境變數。"""
    if current_app is not None:
        try:
            return (current_app.config.get(key) or default) or default
        except RuntimeError:
            pass
        except Exception:
            pass
    import os
    return os.environ.get(key, default)


def _vapid_claims() -> dict:
    subject = _config_get("VAPID_SUBJECT", "") or "mailto:admin@example.com"
    return {"sub": subject}


def send_push(
    user_id: str,
    title: str,
    body: str = "",
    url: str | None = None,
    icon: str | None = None,
) -> dict:
    """寄送推送訊息給指定使用者所有訂閱。

    回傳結構：
        {
            "configured": True/False,   # VAPID + pywebpush 是否齊全
            "sent": int,                # 成功寄出的訂閱數
            "failed": int,              # 失敗的訂閱數
            "expired": int,             # 因端點過期而被自動清掉的訂閱數
        }
    """
    result = {"configured": False, "sent": 0, "failed": 0, "expired": 0}

    private_key = _config_get("VAPID_PRIVATE_KEY", "").strip()
    public_key = _config_get("VAPID_PUBLIC_KEY", "").strip()

    if not private_key or not public_key:
        return result

    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-not-found]
    except ImportError:
        return result

    result["configured"] = True
    subscriptions = list_subscriptions(user_id)
    if not subscriptions:
        return result

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url or "/",
        "icon": icon or "/static/icons/icon-192.png",
    }, ensure_ascii=False)

    expired_endpoints: list[str] = []
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(_vapid_claims()),
            )
            result["sent"] += 1
        except WebPushException as exc:  # type: ignore[misc]
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                expired_endpoints.append(sub.get("endpoint", ""))
                result["expired"] += 1
            else:
                result["failed"] += 1
        except Exception:
            result["failed"] += 1

    # 清掉失效訂閱
    for ep in expired_endpoints:
        if ep:
            remove_subscription(user_id, ep)

    return result


def broadcast_push(user_ids: Iterable[str], title: str, body: str = "", url: str | None = None) -> dict:
    """對多個使用者廣播推送，回傳彙總結果。"""
    summary = {"users": 0, "sent": 0, "failed": 0, "expired": 0}
    for uid in user_ids:
        summary["users"] += 1
        r = send_push(uid, title=title, body=body, url=url)
        summary["sent"] += r.get("sent", 0)
        summary["failed"] += r.get("failed", 0)
        summary["expired"] += r.get("expired", 0)
    return summary
