"""Phase 39 T1.1：稽核查詢服務（篩選、排序、總數、facets、匯出）。

僅測服務層（純 DB，不經路由）；路由層的參數驗證與信封見 `test_audit_log.py`。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


from app.auth.password import hash_password
from app.models.favorite_audit_token import AuditLog
from app.models.user import User
from app.services import audit_service

UTC = timezone.utc


async def _user(session, username: str) -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _log(
    session,
    *,
    user_id=None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    meta: dict | None = None,
    at: datetime | None = None,
) -> AuditLog:
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
        created_at=at or datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    session.add(row)
    await session.flush()
    return row


def _query(**overrides) -> audit_service.AuditQuery:
    return audit_service.AuditQuery(**overrides)


async def test_query_filters_by_action(db_session):
    await _log(db_session, action="group.member_added", resource_type="group")
    await _log(db_session, action="backup.import", resource_type="backup")

    rows, total = await audit_service.query_logs(
        db_session, _query(action="group.member_added")
    )

    assert total == 1
    assert [r.log.action for r in rows] == ["group.member_added"]


async def test_query_filters_by_resource_type(db_session):
    await _log(db_session, action="group.member_added", resource_type="group")
    await _log(db_session, action="backup.import", resource_type="backup")

    rows, total = await audit_service.query_logs(
        db_session, _query(resource_type="backup")
    )

    assert total == 1
    assert rows[0].log.resource_type == "backup"


async def test_query_filters_by_user_id(db_session):
    alice = await _user(db_session, "alice")
    bob = await _user(db_session, "bob")
    await _log(db_session, user_id=alice.id, action="a.one", resource_type="user")
    await _log(db_session, user_id=bob.id, action="b.two", resource_type="user")

    rows, total = await audit_service.query_logs(
        db_session, _query(user_id=alice.id)
    )

    assert total == 1
    assert rows[0].log.action == "a.one"


async def test_query_filters_by_q_over_action_and_resource_id(db_session):
    await _log(
        db_session,
        action="group.member_added",
        resource_type="group",
        resource_id="grp-1234",
    )
    await _log(db_session, action="backup.import", resource_type="backup")

    by_action, _ = await audit_service.query_logs(db_session, _query(q="MEMBER_ADD"))
    by_resource, _ = await audit_service.query_logs(db_session, _query(q="grp-12"))

    assert [r.log.action for r in by_action] == ["group.member_added"]
    assert [r.log.action for r in by_resource] == ["group.member_added"]


async def test_query_filters_by_q_over_meta(db_session):
    """meta 以 JSON 文字比對（cast Text；SQLite 與 PG 皆需可用）。"""
    await _log(
        db_session,
        action="group.member_added",
        resource_type="group",
        meta={"member": "Alice", "role": "editor"},
    )
    await _log(
        db_session,
        action="group.member_added",
        resource_type="group",
        meta={"member": "Bob", "role": "viewer"},
    )

    rows, total = await audit_service.query_logs(db_session, _query(q="alice"))

    assert total == 1
    assert rows[0].log.meta["member"] == "Alice"


async def test_query_date_range_start_inclusive_end_exclusive(db_session):
    day = datetime(2026, 10, 1, tzinfo=UTC)
    await _log(db_session, action="before", resource_type="x", at=day - timedelta(seconds=1))
    await _log(db_session, action="inside", resource_type="x", at=day)
    await _log(db_session, action="edge", resource_type="x", at=day + timedelta(days=1))
    await _log(db_session, action="after", resource_type="x", at=day + timedelta(days=1, seconds=1))

    rows, total = await audit_service.query_logs(
        db_session,
        _query(created_from=day, created_to=day + timedelta(days=1)),
    )

    assert total == 1
    assert [r.log.action for r in rows] == ["inside"]


async def test_query_orders_desc_and_paginates_with_filtered_total(db_session):
    base = datetime(2026, 10, 1, tzinfo=UTC)
    for i in range(5):
        await _log(
            db_session,
            action=f"e.{i}",
            resource_type="x",
            at=base + timedelta(minutes=i),
        )
    await _log(db_session, action="other", resource_type="y", at=base)

    first, total = await audit_service.query_logs(
        db_session, _query(resource_type="x"), limit=2, offset=0
    )
    second, _ = await audit_service.query_logs(
        db_session, _query(resource_type="x"), limit=2, offset=2
    )

    assert total == 5
    assert [r.log.action for r in first] == ["e.4", "e.3"]
    assert [r.log.action for r in second] == ["e.2", "e.1"]


async def test_query_returns_user_email_and_null_when_no_user(db_session):
    alice = await _user(db_session, "alice")
    await _log(db_session, user_id=alice.id, action="a.one", resource_type="user")
    await _log(db_session, user_id=None, action="system", resource_type="backup")

    rows, _ = await audit_service.query_logs(db_session, _query())

    by_action = {r.log.action: r.user_email for r in rows}
    assert by_action["a.one"] == "alice@test.io"
    assert by_action["system"] is None


async def test_facets_are_global_and_sorted_by_count_then_value(db_session):
    alice = await _user(db_session, "alice")
    for _ in range(3):
        await _log(db_session, action="group.member_added", resource_type="group")
    await _log(db_session, user_id=alice.id, action="backup.import", resource_type="backup")
    await _log(db_session, user_id=alice.id, action="admin.user.set_active", resource_type="user")

    facets = await audit_service.facets(db_session)

    assert facets.actions[0] == ("group.member_added", 3)
    # 同為 1 次 → 依 value 遞增
    assert facets.actions[1:] == [
        ("admin.user.set_active", 1),
        ("backup.import", 1),
    ]
    assert facets.resource_types == [
        ("group", 3),
        ("backup", 1),
        ("user", 1),
    ]


async def test_facets_ignore_filters(db_session):
    """facets 為全域：即使查詢帶篩選，選單仍看到所有值。"""
    await _log(db_session, action="a.one", resource_type="x")
    await _log(db_session, action="b.two", resource_type="y")

    facets = await audit_service.facets(db_session)

    assert [value for value, _ in facets.actions] == ["a.one", "b.two"]


async def test_facets_capped_at_fifty_values(db_session):
    for i in range(60):
        await _log(db_session, action=f"act.{i:02d}", resource_type=f"rt.{i:02d}")

    facets = await audit_service.facets(db_session)

    assert len(facets.actions) == 50
    assert len(facets.resource_types) == 50


async def test_export_rows_respect_filters_and_max_rows(db_session):
    base = datetime(2026, 10, 1, tzinfo=UTC)
    for i in range(5):
        await _log(db_session, action="a.same", resource_type="x", at=base + timedelta(minutes=i))
    await _log(db_session, action="other", resource_type="x")

    rows = await audit_service.export_rows(
        db_session, _query(action="a.same"), max_rows=3
    )

    assert len(rows) == 3
    # 最新優先（DESC）；SQLite 回傳 naive、PG 回傳 aware → 統一補 UTC 再比
    def as_utc(value):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    assert [as_utc(r.log.created_at) for r in rows] == [
        base + timedelta(minutes=4),
        base + timedelta(minutes=3),
        base + timedelta(minutes=2),
    ]


async def test_query_q_escapes_like_wildcards(db_session):
    """`%`／`_` 為 LIKE 萬用字元，使用者輸入須轉義（否則 q="100%" 會全中）。"""
    await _log(db_session, action="a.one", resource_type="x", resource_id="SKU_100")
    await _log(db_session, action="b.two", resource_type="y", resource_id="SKU-200")

    by_percent, _ = await audit_service.query_logs(db_session, _query(q="100%"))
    by_underscore, _ = await audit_service.query_logs(db_session, _query(q="SKU_1"))

    assert by_percent == []
    assert [r.log.resource_id for r in by_underscore] == ["SKU_100"]


async def test_query_normalises_blank_filters(db_session):
    """空白字串／`None` 篩選視同未提供（不應把條件變成 LIKE '%%' 而漏掉 meta 為 null 的列）。"""
    await _log(db_session, action="a.one", resource_type="x", meta=None)
    await _log(db_session, action="b.two", resource_type="y", meta={"k": "v"})

    rows, total = await audit_service.query_logs(
        db_session, _query(q="   ", action="", resource_type=None)
    )

    assert total == 2
    assert len(rows) == 2
