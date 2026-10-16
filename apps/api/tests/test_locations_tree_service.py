from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.auth.password import hash_password
from app.models.item import Item
from app.models.location import Location
from app.models.user import User
from app.repositories import locations_repository as repo
from app.schemas.location import LocationCreate, LocationUpdate
from app.services import locations_service


async def _user(session, username: str = "loc_svc") -> User:
    u = User(
        email=f"{username}@t.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(u)
    await session.flush()
    return u


async def _create(
    session, owner_id, name: str, parent_id: int | None = None, **extra
) -> dict:
    return await locations_service.create(
        session,
        owner_id,
        LocationCreate(parent_id=parent_id, name=name, **extra),
    )


async def _tree_fixture(session, owner_id) -> dict[str, dict]:
    """1F > 廚房 > {上櫃, 冰箱}；2F > 書房（sort_order 依序）。"""
    f1 = await _create(session, owner_id, "1F", kind="floor")
    f2 = await _create(session, owner_id, "2F", kind="floor")
    kitchen = await _create(session, owner_id, "廚房", f1["id"], kind="room", sort_order=1)
    shelf = await _create(session, owner_id, "上櫃", kitchen["id"], sort_order=1)
    fridge = await _create(session, owner_id, "冰箱", kitchen["id"], sort_order=2)
    study = await _create(session, owner_id, "書房", f2["id"], kind="room")
    return {
        "1F": f1,
        "2F": f2,
        "廚房": kitchen,
        "上櫃": shelf,
        "冰箱": fridge,
        "書房": study,
    }


async def _item(session, owner_id, name: str, location_id: int | None) -> Item:
    item = Item(owner_id=owner_id, name=name, location_id=location_id)
    session.add(item)
    await session.commit()
    return item


def _status(exc: HTTPException) -> int:
    return exc.status_code


# ---------- 讀取：走訪序、路徑、樹、CTE ----------


async def test_list_all_is_walk_ordered_with_paths(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    rows = await locations_service.list_all(db_session, u.id)

    assert [r["name"] for r in rows] == ["1F", "廚房", "上櫃", "冰箱", "2F", "書房"]
    by_name = {r["name"]: r for r in rows}
    assert by_name["上櫃"]["path"] == "1F / 廚房 / 上櫃"
    assert by_name["書房"]["path"] == "2F / 書房"
    assert by_name["1F"]["parent_id"] is None
    assert by_name["廚房"]["parent_id"] == nodes["1F"]["id"]


async def test_list_all_respects_sort_order_within_parent(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    await _create(db_session, u.id, "B", root["id"], sort_order=2)
    await _create(db_session, u.id, "A", root["id"], sort_order=1)

    rows = await locations_service.list_all(db_session, u.id)

    assert [r["name"] for r in rows] == ["1F", "A", "B"]


async def test_descendant_ids_includes_self_and_subtree(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    everything = await repo.descendant_ids(db_session, u.id, [nodes["1F"]["id"]])
    assert everything == {
        nodes["1F"]["id"],
        nodes["廚房"]["id"],
        nodes["上櫃"]["id"],
        nodes["冰箱"]["id"],
    }
    leaves = await repo.descendant_ids(db_session, u.id, [nodes["上櫃"]["id"]])
    assert leaves == {nodes["上櫃"]["id"]}
    empty = await repo.descendant_ids(db_session, u.id, [])
    assert empty == set()


async def test_tree_is_nested_with_direct_item_counts(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)
    await _item(db_session, u.id, "牛奶", nodes["上櫃"]["id"])
    await _item(db_session, u.id, "雞蛋", nodes["上櫃"]["id"])
    await _item(db_session, u.id, "水餃", nodes["冰箱"]["id"])

    roots = await locations_service.tree(db_session, u.id)

    assert [r["name"] for r in roots] == ["1F", "2F"]
    floor_one = roots[0]
    assert floor_one["item_count"] == 0  # 只計直接物品
    kitchen = floor_one["children"][0]
    assert kitchen["name"] == "廚房"
    assert [c["name"] for c in kitchen["children"]] == ["上櫃", "冰箱"]
    assert {c["name"]: c["item_count"] for c in kitchen["children"]} == {
        "上櫃": 2,
        "冰箱": 1,
    }
    assert [c["name"] for c in roots[1]["children"]] == ["書房"]


async def test_path_of_returns_breadcrumb(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    payload = await locations_service.path_of(db_session, u.id, nodes["上櫃"]["id"])

    assert payload["path"] == "1F / 廚房 / 上櫃"
    assert [n["name"] for n in payload["nodes"]] == ["1F", "廚房", "上櫃"]
    assert payload["nodes"][0]["kind"] == "floor"

    with pytest.raises(HTTPException) as exc:
        await locations_service.path_of(db_session, u.id, 99999)
    assert _status(exc.value) == 404


# ---------- 建立 ----------


async def test_create_rejects_duplicate_sibling_name(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    await _create(db_session, u.id, "廚房", root["id"])

    with pytest.raises(HTTPException) as exc:
        await _create(db_session, u.id, "廚房", root["id"])
    assert _status(exc.value) == 409
    assert exc.value.detail["code"] == "duplicate_name"

    # 不同 parent 同名 OK
    other = await _create(db_session, u.id, "2F")
    await _create(db_session, u.id, "廚房", other["id"])


async def test_create_rejects_root_duplicate_name(db_session):
    u = await _user(db_session)
    await _create(db_session, u.id, "1F")

    with pytest.raises(HTTPException) as exc:
        await _create(db_session, u.id, "1F")
    assert _status(exc.value) == 409


async def test_create_rejects_unknown_or_foreign_parent(db_session):
    owner = await _user(db_session, "loc_owner")
    other = await _user(db_session, "loc_other")
    foreign = await _create(db_session, other.id, "別人的樓層")

    with pytest.raises(HTTPException) as exc:
        await _create(db_session, owner.id, "廚房", 99999)
    assert _status(exc.value) == 404

    with pytest.raises(HTTPException) as exc:
        await _create(db_session, owner.id, "廚房", foreign["id"])
    assert _status(exc.value) == 404


# ---------- 更新／搬移 ----------


async def test_update_renames_and_moves_subtree(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    renamed = await locations_service.update(
        db_session, u.id, nodes["廚房"]["id"], LocationUpdate(name="餐廳", kind="room")
    )
    assert renamed["name"] == "餐廳"
    assert renamed["path"] == "1F / 餐廳"

    moved = await locations_service.update(
        db_session, u.id, nodes["上櫃"]["id"], LocationUpdate(parent_id=nodes["2F"]["id"])
    )
    assert moved["path"] == "2F / 上櫃"

    # 子樹一起跟著搬
    rows = await locations_service.list_all(db_session, u.id)
    by_name = {r["name"]: r for r in rows}
    assert by_name["冰箱"]["path"] == "1F / 餐廳 / 冰箱"

    to_root = await locations_service.update(
        db_session, u.id, nodes["上櫃"]["id"], LocationUpdate(parent_id=None)
    )
    assert to_root["path"] == "上櫃"


async def test_move_to_self_or_descendant_is_rejected(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    with pytest.raises(HTTPException) as exc:
        await locations_service.update(
            db_session, u.id, nodes["廚房"]["id"], LocationUpdate(parent_id=nodes["廚房"]["id"])
        )
    assert _status(exc.value) == 422
    assert exc.value.detail["code"] == "cycle"

    with pytest.raises(HTTPException) as exc:
        await locations_service.update(
            db_session,
            u.id,
            nodes["1F"]["id"],
            LocationUpdate(parent_id=nodes["上櫃"]["id"]),
        )
    assert _status(exc.value) == 422


async def test_rename_to_existing_sibling_name_rejected(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    await _create(db_session, u.id, "廚房", root["id"])
    living = await _create(db_session, u.id, "客廳", root["id"])

    with pytest.raises(HTTPException) as exc:
        await locations_service.update(
            db_session, u.id, living["id"], LocationUpdate(name="廚房")
        )
    assert _status(exc.value) == 409


async def test_move_to_unknown_parent_404(db_session):
    u = await _user(db_session)
    node = await _create(db_session, u.id, "1F")

    with pytest.raises(HTTPException) as exc:
        await locations_service.update(
            db_session, u.id, node["id"], LocationUpdate(parent_id=99999)
        )
    assert _status(exc.value) == 404


# ---------- 排序 ----------


async def test_reorder_rewrites_sibling_positions(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    a = await _create(db_session, u.id, "A", root["id"], sort_order=0)
    b = await _create(db_session, u.id, "B", root["id"], sort_order=1)
    c = await _create(db_session, u.id, "C", root["id"], sort_order=2)

    await locations_service.reorder(
        db_session, u.id, root["id"], [c["id"], a["id"], b["id"]]
    )

    rows = await locations_service.list_all(db_session, u.id)
    assert [r["name"] for r in rows] == ["1F", "C", "A", "B"]

    # root 層排序（parent_id=None）
    other = await _create(db_session, u.id, "2F")
    await locations_service.reorder(db_session, u.id, None, [other["id"], root["id"]])
    rows = await locations_service.list_all(db_session, u.id)
    assert [r["name"] for r in rows][:2] == ["2F", "1F"]


async def test_reorder_requires_complete_sibling_set(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    a = await _create(db_session, u.id, "A", root["id"])
    b = await _create(db_session, u.id, "B", root["id"])
    await _create(db_session, u.id, "C", root["id"])

    with pytest.raises(HTTPException) as exc:
        await locations_service.reorder(db_session, u.id, root["id"], [a["id"], b["id"]])
    assert _status(exc.value) == 422

    with pytest.raises(HTTPException) as exc:
        await locations_service.reorder(
            db_session, u.id, root["id"], [a["id"], a["id"]]
        )
    assert _status(exc.value) == 422


async def test_reorder_rejects_cross_parent_ids(db_session):
    u = await _user(db_session)
    root = await _create(db_session, u.id, "1F")
    child = await _create(db_session, u.id, "廚房", root["id"])
    other = await _create(db_session, u.id, "2F")
    grandchild = await _create(db_session, u.id, "上櫃", child["id"])

    with pytest.raises(HTTPException) as exc:
        await locations_service.reorder(
            db_session, u.id, root["id"], [child["id"], grandchild["id"]]
        )
    assert _status(exc.value) == 422

    with pytest.raises(HTTPException) as exc:
        await locations_service.reorder(db_session, u.id, other["id"], [child["id"]])
    assert _status(exc.value) == 422


# ---------- 刪除限制 ----------


async def test_delete_blocked_when_node_has_children(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)

    with pytest.raises(HTTPException) as exc:
        await locations_service.delete(db_session, u.id, nodes["廚房"]["id"])
    assert _status(exc.value) == 409
    assert exc.value.detail == {"code": "has_children", "items": 0, "children": 2}


async def test_delete_blocked_when_node_has_items(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)
    await _item(db_session, u.id, "牛奶", nodes["上櫃"]["id"])

    with pytest.raises(HTTPException) as exc:
        await locations_service.delete(db_session, u.id, nodes["上櫃"]["id"])
    assert _status(exc.value) == 409
    assert exc.value.detail == {"code": "has_items", "items": 1, "children": 0}


async def test_delete_leaf_after_moving_items_out(db_session):
    u = await _user(db_session)
    nodes = await _tree_fixture(db_session, u.id)
    item = await _item(db_session, u.id, "牛奶", nodes["上櫃"]["id"])

    with pytest.raises(HTTPException):
        await locations_service.delete(db_session, u.id, nodes["上櫃"]["id"])

    # 搬走物品（重用既有集合端點語義：直接改 location_id）
    item.location_id = nodes["冰箱"]["id"]
    await db_session.commit()

    await locations_service.delete(db_session, u.id, nodes["上櫃"]["id"])
    remaining = (
        await db_session.execute(
            select(Location).where(Location.id == nodes["上櫃"]["id"])
        )
    ).scalar_one_or_none()
    assert remaining is None


async def test_delete_unknown_location_404(db_session):
    u = await _user(db_session)
    with pytest.raises(HTTPException) as exc:
        await locations_service.delete(db_session, u.id, 424242)
    assert _status(exc.value) == 404
