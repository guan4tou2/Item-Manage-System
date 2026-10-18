from __future__ import annotations

from uuid import uuid4

import pytest


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _group(client, headers, name="g") -> str:
    r = await client.post("/api/groups", headers=headers, json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _add(client, headers, gid, username, role="editor"):
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=headers,
        json={"username": username, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()["user_id"]


async def _set_role(client, headers, gid, user_id, role):
    return await client.patch(
        f"/api/groups/{gid}/members/{user_id}", headers=headers, json={"role": role}
    )


@pytest.fixture
async def owner_auth(client):
    return await _login(client, "grp_owner")


@pytest.fixture
async def editor_auth(client):
    return await _login(client, "grp_editor")


@pytest.fixture
async def viewer_auth(client):
    return await _login(client, "grp_viewer")


@pytest.fixture
async def stranger_auth(client):
    return await _login(client, "grp_stranger")


@pytest.fixture
async def setup(client, owner_auth, editor_auth, viewer_auth):
    """owner 建群；editor/viewer 入群。回 (gid, editor_user_id, viewer_user_id)。"""
    gid = await _group(client, owner_auth, "fam")
    editor_id = await _add(client, owner_auth, gid, "grp_editor", role="editor")
    viewer_id = await _add(client, owner_auth, gid, "grp_viewer", role="viewer")
    return gid, editor_id, viewer_id


async def test_viewer_cannot_create_group(client, viewer_auth, setup):
    r = await client.post("/api/groups", headers=viewer_auth, json={"name": "mine"})
    assert r.status_code == 403


async def test_editor_and_viewer_cannot_manage(client, owner_auth, editor_auth, viewer_auth, setup):
    gid, editor_id, viewer_id = setup
    for headers in (editor_auth, viewer_auth):
        assert (await client.patch(f"/api/groups/{gid}", headers=headers, json={"name": "x"})).status_code == 403
        assert (
            await client.post(
                f"/api/groups/{gid}/members", headers=headers, json={"username": "ghost"}
            )
        ).status_code == 403
    assert (await _set_role(client, editor_auth, gid, viewer_id, "editor")).status_code == 403
    assert (
        await client.delete(f"/api/groups/{gid}/members/{viewer_id}", headers=editor_auth)
    ).status_code == 403


async def test_non_member_gets_404(client, owner_auth, stranger_auth, setup):
    gid, _, _ = setup
    assert (await client.patch(f"/api/groups/{gid}", headers=stranger_auth, json={"name": "x"})).status_code == 404
    assert (
        await client.post(
            f"/api/groups/{gid}/members", headers=stranger_auth, json={"username": "ghost"}
        )
    ).status_code == 404
    assert (await _set_role(client, stranger_auth, gid, uuid4(), "editor")).status_code == 404


async def test_admin_can_manage_group(client, owner_auth, editor_auth, setup):
    gid, editor_id, _ = setup
    r = await _set_role(client, owner_auth, gid, editor_id, "admin")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

    # admin 可改名、加成員、改角色、移除成員
    assert (await client.patch(f"/api/groups/{gid}", headers=editor_auth, json={"name": "renamed"})).status_code == 200
    await client.post("/api/auth/register", json={"email": "grp_third@t.io", "username": "grp_third", "password": "secret1234"})
    third_id = await _add(client, editor_auth, gid, "grp_third", role="viewer")
    assert (await _set_role(client, editor_auth, gid, third_id, "editor")).status_code == 200
    assert (await client.delete(f"/api/groups/{gid}/members/{third_id}", headers=editor_auth)).status_code == 204


async def test_admin_cannot_delete_group(client, owner_auth, editor_auth, setup):
    gid, editor_id, _ = setup
    assert (await _set_role(client, owner_auth, gid, editor_id, "admin")).status_code == 200
    assert (await client.delete(f"/api/groups/{gid}", headers=editor_auth)).status_code == 403
    assert (await client.delete(f"/api/groups/{gid}", headers=owner_auth)).status_code == 204


async def test_admin_can_manage_other_admin(client, owner_auth, editor_auth, viewer_auth, setup):
    gid, editor_id, viewer_id = setup
    await _set_role(client, owner_auth, gid, editor_id, "admin")
    r = await _set_role(client, editor_auth, gid, viewer_id, "admin")
    assert r.status_code == 200
    r = await _set_role(client, editor_auth, gid, viewer_id, "viewer")
    assert r.status_code == 200


async def test_owner_role_is_protected(client, owner_auth, editor_auth, setup):
    gid, editor_id, _ = setup
    await _set_role(client, owner_auth, gid, editor_id, "admin")
    owner_user_id = (await client.get("/api/users/me", headers=owner_auth)).json()["id"]
    # admin 不得變更 owner
    assert (await _set_role(client, editor_auth, gid, owner_user_id, "viewer")).status_code == 409
    # owner 亦不得變更自己的角色列（owner 由 owner_id 判定）
    assert (await _set_role(client, owner_auth, gid, owner_user_id, "admin")).status_code == 409
    # role=owner 不合法（422）
    assert (await _set_role(client, owner_auth, gid, editor_id, "owner")).status_code == 422
    # 加入成員時指定 owner 亦不合法
    r = await client.post(
        f"/api/groups/{gid}/members", headers=owner_auth, json={"username": "grp_viewer", "role": "owner"}
    )
    assert r.status_code == 422


async def test_patch_role_target_must_be_member(client, owner_auth, setup):
    gid, _, _ = setup
    assert (await _set_role(client, owner_auth, gid, uuid4(), "editor")).status_code == 404


async def test_viewer_and_editor_self_leave(client, owner_auth, editor_auth, viewer_auth, setup):
    gid, editor_id, viewer_id = setup
    assert (await client.delete(f"/api/groups/{gid}/members/{viewer_id}", headers=viewer_auth)).status_code == 204
    assert (await client.delete(f"/api/groups/{gid}/members/{editor_id}", headers=editor_auth)).status_code == 204


async def test_role_change_writes_audit_logs(client, owner_auth, editor_auth, setup):
    gid, editor_id, viewer_id = setup
    assert (await client.post("/api/auth/bootstrap-admin", headers=owner_auth)).status_code == 200
    await _set_role(client, owner_auth, gid, editor_id, "admin")
    await client.delete(f"/api/groups/{gid}/members/{viewer_id}", headers=owner_auth)

    logs = (
        await client.get(
            "/api/admin/audit-logs", headers=owner_auth, params={"resource_type": "group"}
        )
    ).json()

    def rows(action: str) -> list[dict]:
        return [r for r in logs if r["action"] == action]

    assert any(r["meta"]["role"] == "editor" for r in rows("group.member_added"))
    changed = rows("group.member_role_changed")[0]["meta"]
    assert changed["from"] == "editor" and changed["to"] == "admin"
    assert rows("group.member_removed")[0]["meta"]["username"] == "grp_viewer"
    assert all(r["resource_id"] == gid for r in logs)
