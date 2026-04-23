from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.notification import (
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)


def test_notification_read_serialises_minimal():
    n = NotificationRead(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type="system.welcome",
        title="歡迎",
        body=None,
        link="/dashboard",
        read_at=None,
        created_at=datetime.now(timezone.utc),
    )
    dumped = n.model_dump()
    assert dumped["type"] == "system.welcome"
    assert dumped["body"] is None


def test_notification_list_response_shape():
    resp = NotificationListResponse(items=[], total=0, unread_count=0)
    assert resp.items == []
    assert resp.total == 0
    assert resp.unread_count == 0


def test_unread_count_response_shape():
    resp = UnreadCountResponse(count=3)
    assert resp.count == 3
