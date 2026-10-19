"""Phase 34 T1.1：既有搜尋 API 擴充（loan／數量區間／排序）。

`loan` 為新篩選維度；數量區間與 `name_asc`／`created_desc` 為 AI filters 所需。
省略新參數時行為必須與現在完全相同（回歸）。
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.clock import today_taipei


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "loanf@t.io", "username": "loan_filter", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "loan_filter", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _item(client, headers, *, name: str, quantity: int = 1) -> str:
    r = await client.post(
        "/api/items", headers=headers, json={"name": name, "quantity": quantity}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _loan(client, headers, item_id: str, *, expected_return: str | None = None):
    body: dict = {"borrower_label": "小明"}
    if expected_return is not None:
        body["expected_return"] = expected_return
    r = await client.post(f"/api/items/{item_id}/loans", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _names(client, headers, params: str = "") -> list[str]:
    r = await client.get(f"/api/items{params}", headers=headers)
    assert r.status_code == 200, r.text
    return [i["name"] for i in r.json()["items"]]


async def test_loan_borrowed_returns_only_unreturned(client, auth):
    drill = await _item(client, auth, name="電鑽")
    ladder = await _item(client, auth, name="梯子")
    await _item(client, auth, name="螺絲起子")
    await _loan(client, auth, drill)
    loan = await _loan(client, auth, ladder)
    await client.post(f"/api/items/{ladder}/loans/{loan['id']}/return", headers=auth)

    names = await _names(client, auth, "?loan=borrowed")

    assert names == ["電鑽"]


async def test_loan_overdue_requires_expected_return_in_the_past(client, auth):
    overdue = await _item(client, auth, name="逾期工具")
    future = await _item(client, auth, name="未到期工具")
    no_date = await _item(client, auth, name="未填歸還日")
    await _loan(
        client, auth, overdue,
        expected_return=(today_taipei() - timedelta(days=3)).isoformat(),
    )
    await _loan(
        client, auth, future,
        expected_return=(today_taipei() + timedelta(days=5)).isoformat(),
    )
    await _loan(client, auth, no_date)

    names = await _names(client, auth, "?loan=overdue")

    # 無 expected_return 不算逾期
    assert names == ["逾期工具"]


async def test_loan_filter_ignores_returned_loans(client, auth):
    item = await _item(client, auth, name="已歸還")
    loan = await _loan(
        client, auth, item,
        expected_return=(today_taipei() - timedelta(days=10)).isoformat(),
    )
    await client.post(f"/api/items/{item}/loans/{loan['id']}/return", headers=auth)

    assert await _names(client, auth, "?loan=overdue") == []
    assert await _names(client, auth, "?loan=borrowed") == []


async def test_loan_filter_combines_with_keyword_and_expiry(client, auth):
    target = await _item(client, auth, name="露營燈")
    other = await _item(client, auth, name="營燈備品")
    await _item(client, auth, name="帳篷")
    await _loan(client, auth, target)
    await _loan(client, auth, other)

    names = await _names(client, auth, "?q=露營&loan=borrowed")

    assert names == ["露營燈"]


async def test_omitting_loan_keeps_existing_behaviour(client, auth):
    borrowed = await _item(client, auth, name="借出中")
    await _item(client, auth, name="在庫")
    await _loan(client, auth, borrowed)

    names = await _names(client, auth)

    assert sorted(names) == ["借出中", "在庫"]


async def test_quantity_range_inclusive(client, auth):
    await _item(client, auth, name="零", quantity=0)
    await _item(client, auth, name="一", quantity=1)
    await _item(client, auth, name="五", quantity=5)
    await _item(client, auth, name="十", quantity=10)

    assert sorted(await _names(client, auth, "?min_quantity=1&max_quantity=5")) == ["一", "五"]
    assert sorted(await _names(client, auth, "?min_quantity=5")) == ["五", "十"]
    assert sorted(await _names(client, auth, "?max_quantity=1")) == ["一", "零"]


async def test_quantity_range_rejects_negative(client, auth):
    r = await client.get("/api/items?min_quantity=-1", headers=auth)

    assert r.status_code == 422


async def test_sort_name_asc(client, auth):
    await _item(client, auth, name="C 物品")
    await _item(client, auth, name="A 物品")
    await _item(client, auth, name="B 物品")

    assert await _names(client, auth, "?sort=name_asc") == ["A 物品", "B 物品", "C 物品"]


async def test_sort_created_desc(client, auth):
    await _item(client, auth, name="最早")
    await _item(client, auth, name="中間")
    await _item(client, auth, name="最新")

    assert await _names(client, auth, "?sort=created_desc") == ["最新", "中間", "最早"]


async def test_sort_default_is_created_desc(client, auth):
    """省略 sort 時與現在相同（建立時間降冪）。"""
    await _item(client, auth, name="先")
    await _item(client, auth, name="後")

    assert await _names(client, auth) == ["後", "先"]


async def test_invalid_sort_is_422(client, auth):
    r = await client.get("/api/items?sort=bogus", headers=auth)

    assert r.status_code == 422
