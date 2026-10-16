from __future__ import annotations

import pytest
from sqlalchemy import select

from app.auth.password import hash_password
from app.models.external_channels import LineUserLink, WebPushSubscription
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.services import notification_prefs as svc


@pytest.fixture
async def user(db_session):
    u = User(
        email="pref@t.io", username="pref_user", password_hash=hash_password("secret1234")
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _cells(db_session) -> list[NotificationPreference]:
    return list(
        (await db_session.execute(select(NotificationPreference))).scalars().all()
    )


def test_default_enabled_matrix():
    assert svc.default_enabled("expired", "email") is False
    assert svc.default_enabled("expiring_soon", "telegram") is False
    assert svc.default_enabled("expired", "in_app") is True
    assert svc.default_enabled("low_stock", "email") is True
    assert svc.default_enabled("unknown", "email") is True


def test_emit_type_map_targets_locked_system():
    assert svc.EMIT_TYPE_MAP["system.welcome"] in svc.LOCKED_TYPES
    assert svc.EMIT_TYPE_MAP["admin.test"] in svc.LOCKED_TYPES


async def test_snapshot_defaults(db_session, user):
    snap = await svc.get_snapshot(db_session, user.id)

    assert [t["key"] for t in snap["types"]] == list(svc.TYPE_KEYS)
    assert len(snap["types"]) == 11
    locked = {t["key"]: t["locked"] for t in snap["types"]}
    assert locked["group_invite"] is True
    assert locked["system"] is True
    assert locked["low_stock"] is False
    groups = {t["key"]: t["group"] for t in snap["types"]}
    assert groups["low_stock"] == "items"
    assert groups["transfer.request"] == "collab"
    assert groups["report_ready"] == "system"

    assert snap["channels"] == list(svc.CHANNELS)
    assert snap["has_custom"] is False

    # 預設全開，唯 expired／expiring_soon 的 email／line／telegram 關
    assert snap["matrix"]["low_stock"] == {
        "in_app": True,
        "email": True,
        "line": True,
        "telegram": True,
        "web_push": True,
    }
    assert snap["matrix"]["expired"]["in_app"] is True
    assert snap["matrix"]["expired"]["web_push"] is True
    for ch in ("email", "line", "telegram"):
        assert snap["matrix"]["expired"][ch] is False
        assert snap["matrix"]["expiring_soon"][ch] is False
    # 鎖定列恆開
    assert snap["matrix"]["system"] == {ch: True for ch in svc.CHANNELS}


async def test_snapshot_channel_availability(db_session, user):
    snap = await svc.get_snapshot(db_session, user.id)
    assert snap["channel_availability"] == {
        "in_app": True,
        "email": True,
        "line": False,
        "telegram": False,
        "web_push": False,
    }

    db_session.add(LineUserLink(user_id=user.id, line_user_id="U123"))
    db_session.add(
        WebPushSubscription(
            user_id=user.id, endpoint="https://push/1", p256dh="p", auth="a"
        )
    )
    await db_session.commit()

    snap = await svc.get_snapshot(db_session, user.id)
    assert snap["channel_availability"]["line"] is True
    assert snap["channel_availability"]["web_push"] is True
    assert snap["channel_availability"]["telegram"] is False


async def test_apply_updates_override_then_revert_to_default(db_session, user):
    snap = await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "email", "enabled": False}],
    )
    assert snap["matrix"]["low_stock"]["email"] is False
    assert snap["has_custom"] is True
    assert len(await _cells(db_session)) == 1

    # 切回預設值 → 覆寫列被刪除
    snap = await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "email", "enabled": True}],
    )
    assert snap["matrix"]["low_stock"]["email"] is True
    assert snap["has_custom"] is False
    assert await _cells(db_session) == []


async def test_apply_updates_expired_email_on_stores_override(db_session, user):
    # expired.email 預設關 → 開啟需存覆寫列
    snap = await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "expired", "channel": "email", "enabled": True}],
    )
    assert snap["matrix"]["expired"]["email"] is True
    assert snap["has_custom"] is True


async def test_apply_updates_empty_is_noop(db_session, user):
    snap = await svc.apply_updates(db_session, user.id, [])
    assert snap["has_custom"] is False
    assert await _cells(db_session) == []


async def test_apply_updates_duplicate_last_wins(db_session, user):
    snap = await svc.apply_updates(
        db_session,
        user.id,
        [
            {"type": "low_stock", "channel": "email", "enabled": False},
            {"type": "low_stock", "channel": "email", "enabled": True},
        ],
    )
    assert snap["matrix"]["low_stock"]["email"] is True
    assert snap["has_custom"] is False


async def test_apply_updates_locked_cannot_disable(db_session, user):
    with pytest.raises(svc.PreferenceUpdateError):
        await svc.apply_updates(
            db_session,
            user.id,
            [{"type": "system", "channel": "in_app", "enabled": False}],
        )
    with pytest.raises(svc.PreferenceUpdateError):
        await svc.apply_updates(
            db_session,
            user.id,
            [{"type": "group_invite", "channel": "email", "enabled": False}],
        )
    assert await _cells(db_session) == []


async def test_apply_updates_locked_enabled_true_is_noop(db_session, user):
    snap = await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "system", "channel": "in_app", "enabled": True}],
    )
    assert snap["matrix"]["system"]["in_app"] is True
    assert snap["has_custom"] is False
    assert await _cells(db_session) == []


async def test_apply_updates_unknown_type_channel_rejected(db_session, user):
    with pytest.raises(svc.PreferenceUpdateError):
        await svc.apply_updates(
            db_session,
            user.id,
            [{"type": "bogus", "channel": "email", "enabled": False}],
        )
    with pytest.raises(svc.PreferenceUpdateError):
        await svc.apply_updates(
            db_session,
            user.id,
            [{"type": "low_stock", "channel": "sms", "enabled": False}],
        )


async def test_apply_updates_validates_all_before_writing(db_session, user):
    with pytest.raises(svc.PreferenceUpdateError):
        await svc.apply_updates(
            db_session,
            user.id,
            [
                {"type": "low_stock", "channel": "email", "enabled": False},
                {"type": "bogus", "channel": "email", "enabled": False},
            ],
        )
    assert await _cells(db_session) == []


async def test_reset_clears_overrides(db_session, user):
    await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "low_stock", "channel": "line", "enabled": False}],
    )
    snap = await svc.reset(db_session, user.id)
    assert snap["has_custom"] is False
    assert snap["matrix"]["low_stock"]["line"] is True
    assert await _cells(db_session) == []


async def test_is_enabled_defaults_and_overrides(db_session, user):
    assert (
        await svc.is_enabled(db_session, user.id, type="low_stock", channel="email")
        is True
    )
    await svc.apply_updates(
        db_session,
        user.id,
        [{"type": "expired", "channel": "email", "enabled": False}],
    )
    assert (
        await svc.is_enabled(db_session, user.id, type="expired", channel="email")
        is False
    )
    assert (
        await svc.is_enabled(db_session, user.id, type="expired", channel="in_app")
        is True
    )


async def test_is_enabled_emit_mapping_and_locked(db_session, user):
    # system.welcome／admin.test → system（鎖定）→ 恆開
    assert (
        await svc.is_enabled(db_session, user.id, type="system.welcome", channel="email")
        is True
    )
    assert (
        await svc.is_enabled(db_session, user.id, type="admin.test", channel="telegram")
        is True
    )
    # 未映射字串 → 視為開啟
    assert (
        await svc.is_enabled(db_session, user.id, type="future.thing", channel="email")
        is True
    )


async def test_is_enabled_fail_soft(db_session, user, monkeypatch):
    from app.repositories import notification_preferences_repository as repo

    async def boom(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(repo, "get_cell", boom)
    assert (
        await svc.is_enabled(db_session, user.id, type="low_stock", channel="email")
        is True
    )
