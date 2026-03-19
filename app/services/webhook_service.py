"""Webhook 服務模組"""
import hashlib
import hmac
import json
import secrets
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from app.repositories import webhook_repo


ALL_EVENTS = [
    "item.created",
    "item.updated",
    "item.deleted",
    "item.quantity.changed",
]


def _send_webhook(wh: Dict[str, Any], event_name: str, payload: Dict[str, Any]) -> bool:
    """實際傳送 HTTP POST 到 webhook URL，回傳是否成功"""
    body = json.dumps({
        "event": event_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": payload,
    }, ensure_ascii=False)

    secret = wh.get("secret", "")
    sig = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()

    try:
        resp = requests.post(
            wh["url"],
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={sig}",
                "X-Webhook-Event": event_name,
            },
            timeout=10,
        )
        return resp.status_code < 400
    except Exception:
        return False


def _fire_single(wh: Dict[str, Any], event_name: str, payload: Dict[str, Any]) -> None:
    """Fire one webhook in the background and update its status."""
    success = _send_webhook(wh, event_name, payload)
    try:
        wh_id = wh.get("id")
        if wh_id is not None:
            new_failures = 0 if success else (wh.get("failure_count", 0) + 1)
            webhook_repo.update_webhook_status(wh_id, datetime.utcnow(), new_failures)
    except Exception:
        pass


def fire_event(event_name: str, payload: Dict[str, Any]) -> None:
    """找出所有訂閱 event_name 的啟用 webhooks，非同步各自觸發。"""
    try:
        webhooks = webhook_repo.get_webhooks_for_event(event_name)
    except Exception:
        return
    for wh in webhooks:
        t = threading.Thread(
            target=_fire_single,
            args=(wh, event_name, payload),
            daemon=True,
        )
        t.start()


def create_webhook(user_id: str, url: str, events: List[str], secret: str) -> int:
    """建立 webhook，回傳 id"""
    events_json = json.dumps(events)
    return webhook_repo.create_webhook({
        "user_id": user_id,
        "url": url,
        "events": events_json,
        "secret": secret,
        "is_active": True,
    })


def delete_webhook(webhook_id: int, user_id: str) -> bool:
    """刪除 webhook"""
    return webhook_repo.delete_webhook(webhook_id, user_id)


def test_webhook(webhook_id: int, user_id: str) -> bool:
    """傳送測試事件到指定 webhook"""
    wh = webhook_repo.get_webhook_by_id(webhook_id, user_id)
    if not wh:
        return False
    payload = {"test": True, "message": "This is a test event from Item Management System"}
    success = _send_webhook(wh, "test", payload)
    try:
        new_failures = wh.get("failure_count", 0) if not success else 0
        webhook_repo.update_webhook_status(webhook_id, datetime.utcnow(), new_failures)
    except Exception:
        pass
    return success
