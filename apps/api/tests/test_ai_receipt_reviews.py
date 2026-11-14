"""收據人工核對、整張收據與批次查詢的行為契約。"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import event

from app.models.ai_draft import AiDraftItem
from app.services.ai_drafts_service import empty_payload


async def login(client, username):
    await client.post(
        "/api/auth/register",
        json={
            "email": f"{username}@t.io",
            "username": username,
            "password": "secret1234",
        },
    )
    response = await client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "secret1234",
        },
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    user = (await client.get("/api/users/me", headers=headers)).json()
    return headers, UUID(user["id"])


@pytest.fixture
async def receipt(client, db_session):
    headers, owner = await login(client, "review_owner")
    receipt_id = uuid4()
    rows = []
    for index, status in enumerate(
        ["pending", "processing", "ready", "failed", "accepted", "discarded"]
    ):
        payload = empty_payload()
        payload.update(
            receipt={"merchant": "測試商店"},
            receipt_item={
                "index": 5 - index,
                "quantity": 2,
                "unit_price": "5.00",
                "subtotal": "10.00",
            },
        )
        # 整張收據容忍早期缺少 AI 建議的資料。
        row = AiDraftItem(
            owner_id=owner,
            receipt_id=receipt_id,
            source="receipt",
            status=status,
            payload=payload,
        )
        db_session.add(row)
        rows.append(row)
    await db_session.commit()
    return headers, receipt_id, rows


async def test_review_idempotence_and_snapshot(client, receipt, db_session):
    headers, rid, rows = receipt
    path = f"/api/ai/receipts/{rid}"
    first = await client.put(
        path + "/review", headers=headers, json={"note": "已對紙本"}
    )
    assert first.status_code == 200
    second = await client.put(path + "/review", headers=headers, json={"note": "更新"})
    assert second.json()["verified_at"] == first.json()["verified_at"]
    assert second.json()["note"] == "更新"
    third = await client.put(path + "/review", headers=headers, json={})
    assert third.json()["verified_at"] == first.json()["verified_at"]
    assert third.json()["note"] is None
    detail = await client.get(path, headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["review"] == third.json()
    assert body["snapshot"]["merchant"] == "測試商店"
    assert body["snapshot"]["total"] is None
    assert body["image_id"] is None
    assert [line["index"] for line in body["lines"]] == list(range(6))
    assert {line["status"] for line in body["lines"]} == {
        "pending",
        "processing",
        "ready",
        "failed",
        "accepted",
        "discarded",
    }
    assert all(line["name"] is None and line["quantity"] == 2 for line in body["lines"])
    assert all(
        line["unit_price"] == "5.00" and line["subtotal"] == "10.00"
        for line in body["lines"]
    )
    for row in rows:
        await db_session.refresh(row)
        assert row.payload["receipt"] == {"merchant": "測試商店"}
    for _ in range(2):
        response = await client.delete(path + "/review", headers=headers)
        assert response.status_code == 204 and response.content == b""
    assert (await client.get(path, headers=headers)).json()["review"] is None


@pytest.mark.parametrize(
    "method,suffix,body",
    [("get", "", None), ("put", "/review", {}), ("delete", "/review", None)],
)
async def test_receipt_not_found_or_other_owner(client, receipt, method, suffix, body):
    _, rid, _ = receipt
    headers, _ = await login(client, "review_other")
    for target in [rid, uuid4()]:
        response = await client.request(
            method,
            f"/api/ai/receipts/{target}{suffix}",
            headers=headers,
            **({"json": body} if body is not None else {}),
        )
        assert response.status_code == 404


async def test_review_note_limit(client, receipt):
    headers, rid, _ = receipt
    path = f"/api/ai/receipts/{rid}/review"
    assert (
        await client.put(path, headers=headers, json={"note": "字" * 200})
    ).status_code == 200
    assert (
        await client.put(path, headers=headers, json={"note": "字" * 201})
    ).status_code == 422


async def test_receipt_viewer_forbidden(client, receipt):
    owner, rid, _ = receipt
    viewer, _ = await login(client, "review_viewer")
    group = (
        await client.post("/api/groups", headers=owner, json={"name": "測試群組"})
    ).json()
    await client.post(
        f"/api/groups/{group['id']}/members",
        headers=owner,
        json={"username": "review_viewer", "role": "viewer"},
    )
    for method, suffix in [("get", ""), ("put", "/review"), ("delete", "/review")]:
        response = await client.request(
            method,
            f"/api/ai/receipts/{rid}{suffix}",
            headers=viewer,
            **({"json": {}} if method == "put" else {}),
        )
        assert response.status_code == 403


async def test_lines_name_item_link_and_deleted_item(client, db_session):
    headers, owner = await login(client, "review_accept")
    rid = uuid4()
    payload = empty_payload()
    payload["ai"] = {
        "name": "紙本名稱",
        "description": None,
        "category": None,
        "tags": [],
        "confidence": 0.9,
    }
    payload["receipt_item"] = {
        "index": 0,
        "quantity": 3,
        "unit_price": "10",
        "subtotal": "30",
    }
    draft = AiDraftItem(
        owner_id=owner,
        receipt_id=rid,
        source="receipt",
        status="ready",
        payload=payload,
    )
    db_session.add(draft)
    await db_session.commit()
    path = f"/api/ai/receipts/{rid}"
    review = (await client.put(path + "/review", headers=headers, json={})).json()
    result = await client.post(
        f"/api/ai/drafts/{draft.id}/accept", headers=headers, json={"name": "編輯名稱"}
    )
    assert result.status_code == 200, result.text
    accepted = result.json()
    assert accepted["draft"]["receipt_review"] == review
    line = (await client.get(path, headers=headers)).json()["lines"][0]
    assert line["name"] == "紙本名稱" and line["quantity"] == 3
    assert line["item_id"] == accepted["item"]["id"]
    assert (
        await client.delete(f"/api/items/{line['item_id']}", headers=headers)
    ).status_code == 204
    assert (await client.get(path, headers=headers)).json()["lines"][0][
        "item_id"
    ] is None


async def test_list_reviews_constant_query_count(client, db_session, test_engine):
    headers, owner = await login(client, "review_queries")
    rid = uuid4()
    for index in range(12):
        db_session.add(
            AiDraftItem(
                owner_id=owner,
                receipt_id=rid if index < 10 else uuid4(),
                source="receipt",
                status="ready",
                payload=empty_payload(),
            )
        )
    photo = AiDraftItem(
        owner_id=owner, source="batch_photo", status="ready", payload=empty_payload()
    )
    db_session.add(photo)
    await db_session.commit()
    review = (
        await client.put(f"/api/ai/receipts/{rid}/review", headers=headers, json={})
    ).json()
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(test_engine.sync_engine, "before_cursor_execute", count)
    try:
        sizes = []
        for limit in [2, 50]:
            statements.clear()
            response = await client.get(
                f"/api/ai/drafts?limit={limit}", headers=headers
            )
            assert response.status_code == 200
            sizes.append(len(statements))
            assert sum("FROM ai_receipt_reviews" in sql for sql in statements) == 1
        assert sizes[0] == sizes[1]
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", count)
    drafts = response.json()["items"]
    assert all(
        row["receipt_review"] == review
        for row in drafts
        if row["receipt_id"] == str(rid)
    )
    assert all(
        row["receipt_review"] is None for row in drafts if row["receipt_id"] != str(rid)
    )
    target = next(row for row in drafts if row["receipt_id"] == str(rid))
    discarded = await client.post(
        f"/api/ai/drafts/{target['id']}/discard", headers=headers
    )
    assert discarded.json()["receipt_review"] == review
    processed = await client.post(f"/api/ai/drafts/{photo.id}/process", headers=headers)
    assert processed.json()["receipt_review"] is None


async def test_receipt_missing_payload_keys(client, db_session):
    headers, owner = await login(client, "review_legacy")
    rid = uuid4()
    db_session.add(
        AiDraftItem(
            owner_id=owner,
            receipt_id=rid,
            source="receipt",
            status="discarded",
            payload={},
        )
    )
    await db_session.commit()
    body = (await client.get(f"/api/ai/receipts/{rid}", headers=headers)).json()
    assert body["snapshot"] is None
    assert body["lines"][0] == {
        "draft_id": body["lines"][0]["draft_id"],
        "index": 0,
        "name": None,
        "quantity": None,
        "unit_price": None,
        "subtotal": None,
        "status": "discarded",
        "item_id": None,
    }


async def test_stub_receipt_full_journey(client, monkeypatch, tmp_path):
    """真實 stub 抽取與多頁上傳後仍只回傳第一頁，已接受行持續保留。"""
    from app.config import get_settings
    from tests.test_ai_receipts import _upload

    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.setenv("AI_MODE", "stub")
    get_settings.cache_clear()
    try:
        headers, _ = await login(client, "review_stub")
        pages = [
            await _upload(client, headers, f"page-{index}.png") for index in range(2)
        ]
        created = await client.post(
            "/api/ai/receipts", headers=headers, json={"image_ids": pages}
        )
        assert created.status_code == 201
        body = created.json()
        assert all(row["receipt_review"] is None for row in body["created"])
        path = f"/api/ai/receipts/{body['receipt_id']}"
        detail = (await client.get(path, headers=headers)).json()
        assert detail["image_id"] == pages[0]
        assert detail["snapshot"]["page_count"] == 2
        assert detail["snapshot"]["balance_status"] == "balanced"
        assert detail["snapshot"]["total"] == "135.00"
        assert [line["name"] for line in detail["lines"]] == [
            "測試品項甲",
            "測試品項乙",
        ]
        assert [line["quantity"] for line in detail["lines"]] == [2, 1]
        assert [line["unit_price"] for line in detail["lines"]] == ["50.00", "40.00"]
        review = (
            await client.put(
                path + "/review", headers=headers, json={"note": "紙本無誤"}
            )
        ).json()
        first = detail["lines"][0]["draft_id"]
        accepted = await client.post(
            f"/api/ai/drafts/{first}/accept", headers=headers, json={"name": "入庫名稱"}
        )
        assert accepted.status_code == 200
        detail = (await client.get(path, headers=headers)).json()
        assert detail["review"] == review
        assert len(detail["lines"]) == 2
        assert detail["lines"][0]["status"] == "accepted"
        assert detail["lines"][0]["name"] == "測試品項甲"
        assert detail["lines"][0]["item_id"] == accepted.json()["item"]["id"]
        assert (
            await client.delete(path + "/review", headers=headers)
        ).status_code == 204
        assert (await client.get(path, headers=headers)).json()["review"] is None
    finally:
        get_settings.cache_clear()
