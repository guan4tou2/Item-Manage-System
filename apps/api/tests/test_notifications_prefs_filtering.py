from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.services import notification_prefs as prefs
from app.services import notifications_service as svc


@pytest.fixture
async def user(db_session):
    u = User(
        email="flt@t.io", username="flt_user", password_hash=hash_password("secret1234")
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
def recorded(monkeypatch):
    """攔截四個外送管道，記錄 (channel, target, title)。"""
    from app.services import external_notifications as ext

    calls: list[tuple[str, str, str]] = []

    async def fake_email(to_email, subject, body):
        calls.append(("email", to_email, subject))
        return True

    async def fake_line(line_user_id, text):
        calls.append(("line", line_user_id, text))
        return True

    async def fake_telegram(chat_id, text):
        calls.append(("telegram", chat_id, text))
        return True

    def fake_web_push(sub, title, body, link):
        calls.append(("web_push", sub.endpoint, title))
        return True

    monkeypatch.setattr(ext, "deliver_email", fake_email)
    monkeypatch.setattr(ext, "deliver_line", fake_line)
    monkeypatch.setattr(ext, "deliver_telegram", fake_telegram)
    monkeypatch.setattr(ext, "deliver_web_push", fake_web_push)
    return calls


async def _link_all_channels(db_session, user):
    from app.models.external_channels import (
        LineUserLink,
        TelegramUserLink,
        WebPushSubscription,
    )

    db_session.add(LineUserLink(user_id=user.id, line_user_id="U1"))
    db_session.add(TelegramUserLink(user_id=user.id, chat_id="C1"))
    db_session.add(
        WebPushSubscription(
            user_id=user.id, endpoint="https://push/1", p256dh="p", auth="a"
        )
    )
    await db_session.commit()


def _channels(recorded) -> list[str]:
    return [c[0] for c in recorded]


async def _in_app_count(db_session, user) -> int:
    from sqlalchemy import func, select

    from app.models.notification import Notification

    return int(
        (
            await db_session.execute(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user.id
                )
            )
        ).scalar_one()
    )


async def test_defaults_deliver_everywhere(db_session, user, recorded):
    await _link_all_channels(db_session, user)

    n = await svc.emit(db_session, user_id=user.id, type="low_stock", title="庫存不足")
    assert n is not None
    assert _channels(recorded) == ["email", "line", "telegram", "web_push"]
    assert await _in_app_count(db_session, user) == 1


async def test_email_off_skips_email_keeps_in_app(db_session, user, recorded):
    await _link_all_channels(db_session, user)
    await prefs.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "email", "enabled": False}],
    )

    n = await svc.emit(db_session, user_id=user.id, type="low_stock", title="庫存不足")
    assert n is not None
    assert "email" not in _channels(recorded)
    assert _channels(recorded) == ["line", "telegram", "web_push"]
    assert await _in_app_count(db_session, user) == 1


async def test_in_app_off_keeps_external_delivery(db_session, user, recorded):
    await _link_all_channels(db_session, user)
    await prefs.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "in_app", "enabled": False}],
    )

    n = await svc.emit(db_session, user_id=user.id, type="low_stock", title="庫存不足")
    assert n is None
    assert _channels(recorded) == ["email", "line", "telegram", "web_push"]
    assert await _in_app_count(db_session, user) == 0


async def test_all_channels_off_emits_nothing(db_session, user, recorded):
    await _link_all_channels(db_session, user)
    await prefs.apply_updates(
        db_session,
        user.id,
        [
            {"type": "low_stock", "channel": ch, "enabled": False}
            for ch in prefs.CHANNELS
        ],
    )

    n = await svc.emit(db_session, user_id=user.id, type="low_stock", title="庫存不足")
    assert n is None
    assert recorded == []
    assert await _in_app_count(db_session, user) == 0


async def test_locked_group_invite_always_delivers(db_session, user, recorded):
    await _link_all_channels(db_session, user)
    # 無關的覆寫不影響鎖定類型
    await prefs.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "in_app", "enabled": False}],
    )

    n = await svc.emit(db_session, user_id=user.id, type="group_invite", title="群組邀請")
    assert n is not None
    assert _channels(recorded) == ["email", "line", "telegram", "web_push"]


async def test_system_welcome_delivers_via_locked_system(db_session, user, recorded):
    n = await svc.emit(db_session, user_id=user.id, type="system.welcome", title="歡迎")
    assert n is not None
    assert _channels(recorded) == ["email"]


async def test_admin_test_delivers_via_mapping(db_session, user, recorded):
    n = await svc.emit(db_session, user_id=user.id, type="admin.test", title="測試")
    assert n is not None
    assert _channels(recorded) == ["email"]


async def test_unmapped_type_fails_open(db_session, user, recorded):
    n = await svc.emit(db_session, user_id=user.id, type="future.thing", title="未來")
    assert n is not None
    assert _channels(recorded) == ["email"]
    assert await _in_app_count(db_session, user) == 1


async def test_expired_defaults_skip_external_email_line_telegram(
    db_session, user, recorded
):
    await _link_all_channels(db_session, user)

    n = await svc.emit(db_session, user_id=user.id, type="expired", title="已過期")
    assert n is not None
    # 預設例外：expired 只走站內＋web_push
    assert _channels(recorded) == ["web_push"]
    assert await _in_app_count(db_session, user) == 1


async def test_expired_email_opt_in_restores_delivery(db_session, user, recorded):
    await _link_all_channels(db_session, user)
    await prefs.apply_updates(
        db_session,
        user.id,
        [{"type": "expired", "channel": "email", "enabled": True}],
    )

    n = await svc.emit(db_session, user_id=user.id, type="expired", title="已過期")
    assert n is not None
    assert _channels(recorded) == ["email", "web_push"]
