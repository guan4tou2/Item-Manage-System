"""Phase 41：伺服器端物品標籤 PDF。

除了檔頭／頁數／headers，QR 與 Code128 都以 PDF raster 後真值解碼（zxing-cpp），
避免「圖有出來但內容錯／密度太高掃不到」。
"""
from __future__ import annotations

import io
import re
from uuid import uuid4

import pypdfium2 as pdfium
import pytest
import zxingcpp

from app.services.labels_service import _deep_link_for

PDF_MAGIC = b"%PDF"
QR_FORMAT = zxingcpp.BarcodeFormat.QRCode
CODE128_FORMAT = zxingcpp.BarcodeFormat.Code128


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "lblpdf@t.io", "username": "label_pdf_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "label_pdf_user", "password": "secret1234"}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _item(client, auth, **extra) -> dict:
    payload = {"name": "widget"}
    payload.update(extra)
    r = await client.post("/api/items", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def _another_user_auth(client, username: str = "label_pdf_other") -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _pdf_params(ids, start: int | None = None):
    params = [("ids", item_id) for item_id in ids]
    if start is not None:
        params.append(("start", str(start)))
    return params


def _doc(pdf: bytes) -> pdfium.PdfDocument:
    return pdfium.PdfDocument(io.BytesIO(pdf))


def _decode(pdf: bytes, page: int = 0) -> list:
    image = _doc(pdf)[page].render(scale=4).to_pil()
    return list(zxingcpp.read_barcodes(image))


def _decoded_texts(pdf: bytes, page: int = 0, fmt=None) -> list[str]:
    return [
        result.text
        for result in _decode(pdf, page)
        if fmt is None or result.format == fmt
    ]


def _page_text(pdf: bytes, page: int = 0) -> str:
    return _doc(pdf)[page].get_textpage().get_text_range()


async def _get(client, auth, params):
    return await client.get("/api/items/labels.pdf", headers=auth, params=params)


async def test_labels_pdf_returns_a4_pdf(client, auth):
    item = await _item(client, auth, name="路由器")

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(PDF_MAGIC)
    assert re.search(
        r'attachment; filename="item-labels-\d{8}\.pdf"',
        r.headers["content-disposition"],
    )
    assert r.headers["cache-control"] == "private, no-store"
    # 字型必須內嵌（TrueType 子集），否則部分檢視器／印表機會缺繁中字形
    assert b"/FontFile2" in r.content

    doc = _doc(r.content)
    assert len(doc) == 1
    width, height = doc[0].get_size()
    assert abs(width - 595.28) < 1 and abs(height - 841.89) < 1


async def test_labels_pdf_qr_and_barcode_decode(client, auth):
    item = await _item(client, auth, name="舊電風扇", barcode="4710085200016", quantity=2)

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 200

    assert _decoded_texts(r.content, fmt=QR_FORMAT) == [_deep_link_for(item["id"])]
    assert _decoded_texts(r.content, fmt=CODE128_FORMAT) == ["4710085200016"]

    text = _page_text(r.content)
    assert "舊電風扇" in text
    assert f"#{item['id'][:8]}" in text
    assert "x2" in text
    assert "4710085200016" in text


async def test_labels_pdf_404_when_any_item_is_missing(client, auth):
    item = await _item(client, auth)

    r = await _get(client, auth, _pdf_params([item["id"], str(uuid4())]))
    assert r.status_code == 404
    assert not r.content.startswith(PDF_MAGIC)


async def test_labels_pdf_404_for_other_users_item(client, auth):
    other = await _another_user_auth(client)
    item = await _item(client, other)

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 404


async def test_labels_pdf_404_for_deleted_item(client, auth):
    item = await _item(client, auth)
    assert (await client.delete(f"/api/items/{item['id']}", headers=auth)).status_code == 204

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 404


async def test_labels_pdf_requires_auth(client):
    r = await client.get(
        "/api/items/labels.pdf", params=_pdf_params([str(uuid4())])
    )
    assert r.status_code == 401


async def test_labels_pdf_validation(client, auth):
    assert (await _get(client, auth, [])).status_code == 422
    assert (
        await _get(client, auth, _pdf_params([str(uuid4()) for _ in range(101)]))
    ).status_code == 422
    item = await _item(client, auth)
    assert (await _get(client, auth, _pdf_params([item["id"]], start=-1))).status_code == 422
    assert (await _get(client, auth, _pdf_params([item["id"]], start=21))).status_code == 422


async def test_labels_pdf_paginates_every_21_labels(client, auth):
    items = [await _item(client, auth, name=f"a{i}") for i in range(21)]
    r = await _get(client, auth, _pdf_params([item["id"] for item in items]))
    assert r.status_code == 200
    assert len(_doc(r.content)) == 1

    extra = await _item(client, auth, name="a21")
    r = await _get(
        client, auth, _pdf_params([item["id"] for item in items] + [extra["id"]])
    )
    assert r.status_code == 200
    assert len(_doc(r.content)) == 2


async def test_labels_pdf_start_skips_slots(client, auth):
    items = [await _item(client, auth, name=f"s{i}") for i in range(2)]

    r = await _get(
        client, auth, _pdf_params([item["id"] for item in items], start=20)
    )
    assert r.status_code == 200
    assert len(_doc(r.content)) == 2
    assert len(_decoded_texts(r.content, page=0, fmt=QR_FORMAT)) == 1
    assert len(_decoded_texts(r.content, page=1, fmt=QR_FORMAT)) == 1


async def test_labels_pdf_dedupes_repeated_ids(client, auth):
    item = await _item(client, auth, name="重複")

    r = await _get(client, auth, _pdf_params([item["id"], item["id"]]))
    assert r.status_code == 200
    assert len(_decoded_texts(r.content, fmt=QR_FORMAT)) == 1


async def test_labels_pdf_without_barcode_keeps_qr(client, auth):
    item = await _item(client, auth, name="無條碼")

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 200
    assert len(_decoded_texts(r.content, fmt=QR_FORMAT)) == 1
    assert _decoded_texts(r.content, fmt=CODE128_FORMAT) == []
    assert "無條碼" in _page_text(r.content)


async def test_labels_pdf_non_ascii_barcode_is_skipped(client, auth):
    item = await _item(client, auth, name="中文條碼", barcode="電風扇")

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 200
    assert _decoded_texts(r.content, fmt=CODE128_FORMAT) == []
    # 條碼值仍以文字呈現，可供手動輸入
    assert "電風扇" in _page_text(r.content)


async def test_labels_pdf_long_name_is_truncated(client, auth):
    long_name = "超長名稱" * 20
    item = await _item(client, auth, name=long_name)

    r = await _get(client, auth, _pdf_params([item["id"]]))
    assert r.status_code == 200
    text = _page_text(r.content)
    assert "…" in text
    # 不應把完整 80 字全部塞進標籤
    assert len(text.replace("\n", "")) < len(long_name)
