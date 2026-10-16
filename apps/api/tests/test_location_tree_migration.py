from __future__ import annotations

import sqlalchemy as sa
import pytest
from sqlalchemy import text

from app.services.location_tree_migration import analyze_flat, migrate_flat

OLD_SCHEMA_DDL = [
    """
    CREATE TABLE locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id VARCHAR(36) NOT NULL,
        floor VARCHAR(50),
        room VARCHAR(50),
        zone VARCHAR(50),
        sort_order INTEGER NOT NULL DEFAULT 0,
        floor_plan_image_id VARCHAR(36),
        parent_id INTEGER,
        name VARCHAR(50),
        kind VARCHAR(20)
    )
    """,
    """
    CREATE TABLE items (
        id VARCHAR(36) PRIMARY KEY,
        owner_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        location_id INTEGER
    )
    """,
]

OWNER_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
OWNER_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"


@pytest.fixture
def legacy_engine():
    """舊平面 schema（＋新欄位並存）——模擬 Alembic 0020「加欄＋放寬 floor NOT NULL」後、
    資料遷移前的狀態。"""
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        for ddl in OLD_SCHEMA_DDL:
            conn.execute(text(ddl))
    yield engine
    engine.dispose()


def _add_location(conn, owner, floor, room, zone, *, sort_order=0):
    return conn.execute(
        text(
            "INSERT INTO locations (owner_id, floor, room, zone, sort_order) "
            "VALUES (:o, :f, :r, :z, :s)"
        ),
        {"o": owner, "f": floor, "r": room, "z": zone, "s": sort_order},
    ).lastrowid


def _add_item(conn, owner, name, location_id):
    conn.execute(
        text(
            "INSERT INTO items (id, owner_id, name, location_id) "
            "VALUES (:i, :o, :n, :l)"
        ),
        {"i": f"{name}-uuid", "o": owner, "n": name, "l": location_id},
    )


def _nodes(conn, owner=OWNER_A):
    rows = conn.execute(
        text(
            "SELECT id, parent_id, name, kind, sort_order FROM locations "
            "WHERE owner_id = :o ORDER BY id"
        ),
        {"o": owner},
    ).all()
    return [
        {
            "id": r[0],
            "parent_id": r[1],
            "name": r[2],
            "kind": r[3],
            "sort_order": r[4],
        }
        for r in rows
    ]


def _items_by_location(conn):
    return dict(
        conn.execute(
            text("SELECT name, location_id FROM items")
        ).all()
    )


def test_migrate_builds_tree_from_flat_rows(legacy_engine):
    with legacy_engine.begin() as conn:
        shelf = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        fridge = _add_location(conn, OWNER_A, "1F", "廚房", "冰箱")
        study = _add_location(conn, OWNER_A, "2F", "書房", None)
        _add_item(conn, OWNER_A, "牛奶", shelf)
        _add_item(conn, OWNER_A, "雞蛋", shelf)
        _add_item(conn, OWNER_A, "水餃", fridge)
        _add_item(conn, OWNER_A, "螺絲起子", study)

        report = migrate_flat(conn)

        assert report.source_rows == 3
        assert report.created_nodes == 6  # 1F, 廚房, 上櫃, 冰箱, 2F, 書房
        nodes = {n["name"]: n for n in _nodes(conn)}
        # 樹形狀
        assert nodes["1F"]["parent_id"] is None and nodes["1F"]["kind"] == "floor"
        assert nodes["廚房"]["parent_id"] == nodes["1F"]["id"]
        assert nodes["廚房"]["kind"] == "room"
        assert nodes["上櫃"]["parent_id"] == nodes["廚房"]["id"]
        assert nodes["上櫃"]["kind"] == "other"
        assert nodes["冰箱"]["parent_id"] == nodes["廚房"]["id"]
        assert nodes["2F"]["parent_id"] is None
        assert nodes["書房"]["parent_id"] == nodes["2F"]["id"]
        # 物品重新指向最深節點
        items = _items_by_location(conn)
        assert items["牛奶"] == nodes["上櫃"]["id"]
        assert items["雞蛋"] == nodes["上櫃"]["id"]
        assert items["水餃"] == nodes["冰箱"]["id"]
        assert items["螺絲起子"] == nodes["書房"]["id"]
        # 舊列已刪除（只剩 canonical 節點）
        assert len(_nodes(conn)) == 6


def test_migrate_merges_duplicate_combinations(legacy_engine):
    with legacy_engine.begin() as conn:
        first = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        duplicate = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        _add_item(conn, OWNER_A, "牛奶", first)

        report = migrate_flat(conn)

        assert report.source_rows == 2
        assert report.merged_rows == 1
        assert len(_nodes(conn)) == 3  # 1F / 廚房 / 上櫃
        assert len(_items_by_location(conn)) == 1
        # 重複列本身已被吸收（無殘留節點）
        assert duplicate not in {n["id"] for n in _nodes(conn)}


def test_report_counts_orphan_nodes_and_unassigned_items(legacy_engine):
    with legacy_engine.begin() as conn:
        shelf = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        _add_location(conn, OWNER_A, "3F", None, None)  # 無物品的孤立層
        _add_item(conn, OWNER_A, "牛奶", shelf)
        _add_item(conn, OWNER_A, "未指派品", None)

        report = migrate_flat(conn)

        assert report.orphan_nodes == 1  # 3F
        assert report.unassigned_items == 1  # 未指派品


def test_migrate_is_owner_scoped(legacy_engine):
    with legacy_engine.begin() as conn:
        a1 = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        b1 = _add_location(conn, OWNER_B, "1F", "廚房", "上櫃")
        _add_item(conn, OWNER_A, "A 牛奶", a1)
        _add_item(conn, OWNER_B, "B 牛奶", b1)

        report = migrate_flat(conn)

        # 兩個 owner 各自的節點互不共用
        nodes_a = _nodes(conn, OWNER_A)
        nodes_b = _nodes(conn, OWNER_B)
        assert len(nodes_a) == 3 and len(nodes_b) == 3
        assert {n["id"] for n in nodes_a}.isdisjoint({n["id"] for n in nodes_b})
        assert report.source_rows == 2
        assert report.created_nodes == 6
        items = _items_by_location(conn)
        assert items["A 牛奶"] != items["B 牛奶"]


def test_no_orphan_items_after_migration(legacy_engine):
    with legacy_engine.begin() as conn:
        shelf = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        _add_item(conn, OWNER_A, "牛奶", shelf)

        migrate_flat(conn)

        dangling = conn.execute(
            text(
                "SELECT count(*) FROM items i WHERE i.location_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM locations l WHERE l.id = i.location_id)"
            )
        ).scalar_one()
        assert dangling == 0


def test_analyze_flat_is_read_only_and_matches_migrate(legacy_engine):
    with legacy_engine.begin() as conn:
        shelf = _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")
        _add_location(conn, OWNER_A, "1F", "廚房", "上櫃")  # duplicate
        _add_location(conn, OWNER_A, "3F", None, None)  # orphan
        _add_item(conn, OWNER_A, "牛奶", shelf)
        _add_item(conn, OWNER_A, "未指派", None)

        before_locations = conn.execute(text("SELECT count(*) FROM locations")).scalar_one()
        before_null_names = (
            conn.execute(
                text("SELECT count(*) FROM locations WHERE name IS NULL")
            ).scalar_one()
        )

        analyzed = analyze_flat(conn)

        assert (
            conn.execute(text("SELECT count(*) FROM locations")).scalar_one()
            == before_locations
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM locations WHERE name IS NULL")
            ).scalar_one()
            == before_null_names
        )

        migrated = migrate_flat(conn)

        assert analyzed.as_dict() == migrated.as_dict()
        assert analyzed.source_rows == 3
        assert analyzed.merged_rows == 1
        assert analyzed.orphan_nodes == 1
        assert analyzed.unassigned_items == 1


def test_degenerate_row_without_usable_parts_is_removed(legacy_engine):
    """floor 為空字串的列（資料異常）：舊列移除、其物品變成未指派，不產生節點。"""
    with legacy_engine.begin() as conn:
        bad = _add_location(conn, OWNER_A, "", None, None)
        _add_item(conn, OWNER_A, "孤兒品", bad)

        report = migrate_flat(conn)

        assert report.source_rows == 1
        assert report.created_nodes == 0
        assert len(_nodes(conn)) == 0
        assert _items_by_location(conn)["孤兒品"] is None
