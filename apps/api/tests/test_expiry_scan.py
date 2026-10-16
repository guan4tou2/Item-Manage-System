from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.auth.password import hash_password
from app.clock import today_taipei
from app.models.expiry_alert import ExpiryAlert
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.repositories import expiry_alerts_repository as alerts_repo
from app.services import expiry_scan, jobs_service

TODAY = date(2026, 10, 16)


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


async def _user(session, name="u1") -> User:
    u = User(
        email=f"{name}@t.io", username=name, password_hash=hash_password("secret1234")
    )
    session.add(u)
    await session.flush()
    return u


async def _batch(
    session,
    owner,
    *,
    expiry_in: int | None,
    name="牛奶",
    is_depleted=False,
    base: date | None = None,
) -> ItemBatch:
    item = Item(owner_id=owner.id, name=name)
    session.add(item)
    await session.flush()
    origin = base if base is not None else TODAY
    batch = ItemBatch(
        item_id=item.id,
        quantity=1,
        expiry_date=None if expiry_in is None else origin + timedelta(days=expiry_in),
        is_depleted=is_depleted,
    )
    session.add(batch)
    await session.flush()
    return batch


async def _levels(session, batch_id) -> set[str]:
    rows = (
        await session.execute(
            select(ExpiryAlert.level).where(ExpiryAlert.batch_id == batch_id)
        )
    ).scalars()
    return set(rows.all())


async def _notifications(session, user_id) -> list[Notification]:
    rows = (
        await session.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
    ).scalars()
    return list(rows.all())


async def test_scan_empty_and_skips_non_eligible(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=None)  # 無到期日
    await _batch(db_session, u, expiry_in=-1, is_depleted=True)  # 已耗盡
    item = Item(owner_id=u.id, name="無批次")
    db_session.add(item)
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.as_dict() == {"processed": 0, "emitted": 0, "errors": []}
    assert await _notifications(db_session, u.id) == []


@pytest.mark.parametrize(
    ("remaining", "expected"),
    [
        (31, set()),
        (30, {"d30"}),
        (8, {"d30"}),
        (7, {"d30", "d7"}),
        (1, {"d30", "d7"}),
        (0, {"d30", "d7", "d0"}),
        (-1, {"expired"}),
        (-14, {"expired"}),
        (-15, set()),
    ],
)
async def test_threshold_levels(db_session, remaining, expected):
    u = await _user(db_session)
    batch = await _batch(db_session, u, expiry_in=remaining)
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert await _levels(db_session, batch.id) == expected
    assert result.processed == len(expected)


async def test_digest_content_expiring(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=2, name="草莓牛奶")
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.emitted == 1
    (n,) = await _notifications(db_session, u.id)
    assert n.type == "expiring_soon"
    assert n.title == "1 件物品即將到期"
    assert n.body == "最急：草莓牛奶（剩 2 天）"
    assert n.link == "/items?sort=expiry_asc"


async def test_digest_content_expiring_today(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=0, name="優格")
    await db_session.commit()

    await expiry_scan.scan(db_session, today=TODAY)

    (n,) = await _notifications(db_session, u.id)
    assert n.body == "最急：優格（今天到期）"


async def test_digest_content_expired(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=-3, name="豆腐")
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.emitted == 1
    (n,) = await _notifications(db_session, u.id)
    assert n.type == "expired"
    assert n.title == "1 件物品已過期"
    assert n.body == "最急：豆腐（已過期 3 天）"
    assert n.link == "/items?expiry=expired&sort=expiry_asc"


async def test_same_day_rerun_idempotent(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=5)
    await db_session.commit()

    first = await expiry_scan.scan(db_session, today=TODAY)
    second = await expiry_scan.scan(db_session, today=TODAY)

    assert first.processed == 2 and first.emitted == 1
    assert second.as_dict() == {"processed": 0, "emitted": 0, "errors": []}
    assert len(await _notifications(db_session, u.id)) == 1


async def test_advance_not_repeated_next_day(db_session):
    u = await _user(db_session)
    batch = await _batch(db_session, u, expiry_in=5)
    await db_session.commit()

    await expiry_scan.scan(db_session, today=TODAY)
    result = await expiry_scan.scan(db_session, today=TODAY + timedelta(days=1))

    assert result.processed == 0
    assert await _levels(db_session, batch.id) == {"d30", "d7"}
    assert len(await _notifications(db_session, u.id)) == 1


async def test_expired_fires_daily_until_stop(db_session):
    u = await _user(db_session)
    batch = await _batch(db_session, u, expiry_in=-1)
    await db_session.commit()

    first = await expiry_scan.scan(db_session, today=TODAY)
    second = await expiry_scan.scan(db_session, today=TODAY + timedelta(days=1))

    assert first.processed == 1 and second.processed == 1
    rows = (
        await db_session.execute(
            select(ExpiryAlert.sent_on).where(ExpiryAlert.batch_id == batch.id)
        )
    ).scalars()
    assert set(rows.all()) == {TODAY, TODAY + timedelta(days=1)}
    assert len(await _notifications(db_session, u.id)) == 2


async def test_distinct_batch_digest_count(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=6, name="A")
    await _batch(db_session, u, expiry_in=5, name="B")
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.processed == 4  # 2 批 × (d30 + d7)
    assert result.emitted == 1
    (n,) = await _notifications(db_session, u.id)
    assert n.title == "2 件物品即將到期"
    assert n.body == "最急：B（剩 5 天）"


async def test_same_user_two_types_two_digests(db_session):
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=3, name="鮮奶")
    await _batch(db_session, u, expiry_in=-1, name="麵包")
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.emitted == 2
    types = {n.type for n in await _notifications(db_session, u.id)}
    assert types == {"expiring_soon", "expired"}


async def test_multi_user_isolation_and_prefs(db_session, recorded):
    a = await _user(db_session, "alice")
    b = await _user(db_session, "bob")

    from app.models.external_channels import LineUserLink, WebPushSubscription

    db_session.add(LineUserLink(user_id=a.id, line_user_id="U1"))
    db_session.add(
        WebPushSubscription(
            user_id=a.id, endpoint="https://push/a", p256dh="p", auth="a"
        )
    )
    db_session.add(
        WebPushSubscription(
            user_id=b.id, endpoint="https://push/b", p256dh="p", auth="a"
        )
    )
    # B：expiring_soon 全通道關（in_app + web_push；其餘預設關）
    db_session.add(
        NotificationPreference(
            user_id=b.id, type="expiring_soon", channel="in_app", enabled=False
        )
    )
    db_session.add(
        NotificationPreference(
            user_id=b.id, type="expiring_soon", channel="web_push", enabled=False
        )
    )
    await _batch(db_session, a, expiry_in=3)
    await _batch(db_session, b, expiry_in=3)
    await db_session.commit()

    result = await expiry_scan.scan(db_session, today=TODAY)

    assert result.emitted == 2  # 兩位使用者各有新 alert → 各 dispatch 一次
    assert len(await _notifications(db_session, a.id)) == 1
    assert await _notifications(db_session, b.id) == []
    # B 關閉的通道確實沒有外送；A 的 web_push 有
    assert [c for c in recorded if c[1] == "https://push/b"] == []
    assert [c for c in recorded if c[1] == "https://push/a"] != []


async def test_partial_failure_isolated_and_retry_fills_gap(db_session, monkeypatch):
    a = await _user(db_session, "alice")
    b = await _user(db_session, "bob")
    batch_a = await _batch(db_session, a, expiry_in=5, name="A")
    batch_b = await _batch(db_session, b, expiry_in=5, name="B")
    await db_session.commit()

    real_create = alerts_repo.create

    async def flaky(session, *, batch_id, level, sent_on):
        if batch_id == batch_b.id:
            raise RuntimeError("boom")
        return await real_create(
            session, batch_id=batch_id, level=level, sent_on=sent_on
        )

    monkeypatch.setattr(alerts_repo, "create", flaky)

    first = await expiry_scan.scan(db_session, today=TODAY)

    assert len(first.errors) == 1 and "boom" in first.errors[0]
    assert first.processed == 2 and first.emitted == 1
    assert await _levels(db_session, batch_a.id) == {"d30", "d7"}
    assert await _levels(db_session, batch_b.id) == set()
    assert len(await _notifications(db_session, a.id)) == 1
    assert await _notifications(db_session, b.id) == []

    monkeypatch.setattr(alerts_repo, "create", real_create)
    second = await expiry_scan.scan(db_session, today=TODAY)

    assert second.processed == 2 and second.emitted == 1
    assert await _levels(db_session, batch_b.id) == {"d30", "d7"}
    assert len(await _notifications(db_session, a.id)) == 1  # A 不重複
    assert len(await _notifications(db_session, b.id)) == 1


async def test_registered_and_runs_via_registry(db_session):
    today = today_taipei()
    u = await _user(db_session)
    await _batch(db_session, u, expiry_in=3, base=today)
    await db_session.commit()

    assert "expiry-scan" in jobs_service.JOBS
    row = await jobs_service.run_job(db_session, "expiry-scan")

    assert row.status == "succeeded"
    assert row.result["processed"] == 2
    assert row.result["emitted"] == 1
