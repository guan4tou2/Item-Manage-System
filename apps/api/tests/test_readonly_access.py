from __future__ import annotations

import pytest
from sqlalchemy import select

from app.auth.password import hash_password
from app.models.group import Group, GroupMember
from app.models.user import User
from app.services import visibility_service as vis


async def _user(db_session, name: str) -> User:
    u = User(email=f"{name}@t.io", username=name, password_hash=hash_password("secret1234"))
    db_session.add(u)
    await db_session.flush()
    return u


async def _group(db_session, owner: User, name: str, members=()) -> Group:
    g = Group(owner_id=owner.id, name=name)
    db_session.add(g)
    await db_session.flush()
    db_session.add(GroupMember(group_id=g.id, user_id=owner.id))
    for member, role in members:
        db_session.add(GroupMember(group_id=g.id, user_id=member.id, role=role))
    await db_session.commit()
    return g


# ---------- 判定表（service） ----------


async def test_read_only_when_all_memberships_viewer(db_session):
    owner = await _user(db_session, "own1")
    viewer = await _user(db_session, "vw1")
    await _group(db_session, owner, "fam", [(viewer, "viewer")])
    assert await vis.is_read_only(db_session, viewer.id) is True


async def test_not_read_only_with_any_non_viewer_membership(db_session):
    a = await _user(db_session, "a1")
    b = await _user(db_session, "b1")
    await _group(db_session, a, "g1", [(b, "viewer")])
    await _group(db_session, a, "g2", [(b, "editor")])
    assert await vis.is_read_only(db_session, b.id) is False


async def test_owner_is_never_read_only(db_session):
    owner = await _user(db_session, "own2")
    await _group(db_session, owner, "g")
    assert await vis.is_read_only(db_session, owner.id) is False


async def test_user_without_groups_is_not_read_only(db_session):
    u = await _user(db_session, "solo")
    assert await vis.is_read_only(db_session, u.id) is False


async def test_leaving_all_groups_restores_writable(db_session):
    owner = await _user(db_session, "own3")
    viewer = await _user(db_session, "vw3")
    g = await _group(db_session, owner, "fam", [(viewer, "viewer")])
    assert await vis.is_read_only(db_session, viewer.id) is True
    row = (await db_session.execute(
        select(GroupMember).where(
            GroupMember.group_id == g.id, GroupMember.user_id == viewer.id
        )
    )).scalar_one()
    await db_session.delete(row)
    await db_session.commit()
    assert await vis.is_read_only(db_session, viewer.id) is False


async def test_read_only_user_ids_batch(db_session):
    owner = await _user(db_session, "own4")
    v = await _user(db_session, "vw4")
    e = await _user(db_session, "ed4")
    s = await _user(db_session, "solo4")
    await _group(db_session, owner, "fam", [(v, "viewer"), (e, "editor")])
    ids = await vis.read_only_user_ids(db_session, [owner.id, v.id, e.id, s.id])
    assert ids == {v.id}


# ---------- 暴露（routes） ----------


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_auth_responses_expose_is_read_only(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "n@t.io", "username": "n_user", "password": "secret1234"},
    )
    assert r.json()["user"]["is_read_only"] is False
    headers = await _login(client, "n_user")
    login = await client.post(
        "/api/auth/login", json={"username": "n_user", "password": "secret1234"}
    )
    assert login.json()["user"]["is_read_only"] is False
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["is_read_only"] is False
    users_me = await client.get("/api/users/me", headers=headers)
    assert users_me.json()["is_read_only"] is False


async def test_viewer_sees_is_read_only_true_on_me(client):
    owner_auth = await _login(client, "v_owner")
    guest_auth = await _login(client, "v_guest")
    gid = (await client.post("/api/groups", headers=owner_auth, json={"name": "fam"})).json()["id"]
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=owner_auth,
        json={"username": "v_guest", "role": "viewer"},
    )
    assert r.status_code == 201
    assert (await client.get("/api/users/me", headers=guest_auth)).json()["is_read_only"] is True
    # owner 自身仍可寫
    assert (await client.get("/api/users/me", headers=owner_auth)).json()["is_read_only"] is False


async def test_patch_me_keeps_is_read_only_true(client):
    owner_auth = await _login(client, "p_owner")
    guest_auth = await _login(client, "p_guest")
    gid = (await client.post("/api/groups", headers=owner_auth, json={"name": "fam"})).json()["id"]
    await client.post(
        f"/api/groups/{gid}/members",
        headers=owner_auth,
        json={"username": "p_guest", "role": "viewer"},
    )
    r = await client.patch("/api/users/me", headers=guest_auth, json={"username": "p_guest2"})
    assert r.status_code == 200
    assert r.json()["is_read_only"] is True


async def test_admin_users_list_includes_is_read_only(client):
    admin_auth = await _login(client, "ro_admin")
    assert (await client.post("/api/auth/bootstrap-admin", headers=admin_auth)).status_code == 200
    await _login(client, "ro_guest")
    gid = (await client.post("/api/groups", headers=admin_auth, json={"name": "fam"})).json()["id"]
    await client.post(
        f"/api/groups/{gid}/members",
        headers=admin_auth,
        json={"username": "ro_guest", "role": "viewer"},
    )
    rows = (await client.get("/api/admin/users", headers=admin_auth)).json()
    by_name = {u["username"]: u["is_read_only"] for u in rows}
    assert by_name["ro_guest"] is True
    assert by_name["ro_admin"] is False


async def test_preferences_viewer_notice_roundtrip(client):
    headers = await _login(client, "pref_user")
    await client.put("/api/users/me/preferences", headers=headers, json={"currency": "USD"})
    r = await client.put(
        "/api/users/me/preferences", headers=headers, json={"viewer_notice_dismissed": True}
    )
    assert r.status_code == 200
    assert r.json()["viewer_notice_dismissed"] is True
    assert r.json()["currency"] == "USD"  # merge 不覆蓋
    got = await client.get("/api/users/me/preferences", headers=headers)
    assert got.json()["viewer_notice_dismissed"] is True
    assert got.json()["currency"] == "USD"
