"""收據整體檢視與人工核對；擁有權來自本人任一狀態的草稿。"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.ai_draft import AiDraftItem
from app.models.ai_receipt_review import AiReceiptReview
from app.models.item import Item
from app.schemas.ai import ReceiptSnapshot
from app.schemas.ai_draft import ReceiptLineRead, ReceiptRead, ReceiptReviewRead


async def owned_lines(
    session: AsyncSession, owner_id: UUID, receipt_id: UUID
) -> list[AiDraftItem]:
    rows = list(
        (
            await session.scalars(
                select(AiDraftItem)
                .where(
                    AiDraftItem.owner_id == owner_id,
                    AiDraftItem.receipt_id == receipt_id,
                )
                .order_by(AiDraftItem.created_at, AiDraftItem.id)
            )
        ).all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="receipt not found")
    return rows


async def reviews_for(
    session: AsyncSession, owner_id: UUID, receipt_ids: Iterable[UUID | None]
) -> dict[UUID, ReceiptReviewRead]:
    """當頁所有收據一次查詢；非收據頁不查詢。"""
    ids = {value for value in receipt_ids if value is not None}
    if not ids:
        return {}
    rows = (
        await session.scalars(
            select(AiReceiptReview).where(
                AiReceiptReview.owner_id == owner_id,
                AiReceiptReview.receipt_id.in_(ids),
            )
        )
    ).all()
    return {row.receipt_id: ReceiptReviewRead.model_validate(row) for row in rows}


async def get_receipt(
    session: AsyncSession, owner_id: UUID, receipt_id: UUID
) -> ReceiptRead:
    rows = await owned_lines(session, owner_id, receipt_id)
    reviews = await reviews_for(session, owner_id, [receipt_id])
    # 物品採軟刪除；已刪除或失去對應的物品不提供連結。
    item_ids = {row.item_id for row in rows if row.item_id is not None}
    existing = (
        set(
            (
                await session.scalars(
                    select(Item.id).where(
                        Item.id.in_(item_ids), Item.is_deleted.is_(False)
                    )
                )
            ).all()
        )
        if item_ids
        else set()
    )
    lines = []
    for row in rows:
        payload = row.payload or {}
        item = payload.get("receipt_item") or {}
        ai = payload.get("ai") or {}
        lines.append(
            ReceiptLineRead(
                draft_id=row.id,
                index=item.get("index") or 0,
                name=ai.get("name"),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price"),
                subtotal=item.get("subtotal"),
                status=row.status,
                item_id=row.item_id
                if row.status == "accepted" and row.item_id in existing
                else None,
            )
        )
    snapshot = next(
        (
            row.payload.get("receipt")
            for row in rows
            if row.payload and row.payload.get("receipt")
        ),
        None,
    )
    if snapshot is not None:
        # 舊快照可能缺少原先必填欄位，僅補合理預設，不更寫資料庫。
        snapshot = ReceiptSnapshot.model_validate(
            {
                "merchant": None,
                "purchased_at": None,
                "currency": None,
                "total": None,
                "item_total": None,
                "discrepancy": None,
                "page_count": 1,
                "truncated": False,
                **snapshot,
            }
        )
    return ReceiptRead(
        receipt_id=receipt_id,
        snapshot=snapshot,
        review=reviews.get(receipt_id),
        image_id=rows[0].image_id,
        lines=sorted(lines, key=lambda line: line.index),
    )


async def put_review(
    session: AsyncSession, owner_id: UUID, receipt_id: UUID, note: str | None
) -> ReceiptReviewRead:
    await owned_lines(session, owner_id, receipt_id)
    # 原子 upsert：重送與並行請求皆保留第一次的 verified_at。
    insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
    stmt = (
        insert(AiReceiptReview)
        .values(
            receipt_id=receipt_id,
            owner_id=owner_id,
            verified_at=_utcnow(),
            note=note,
        )
        .on_conflict_do_update(index_elements=["receipt_id"], set_={"note": note})
    )
    await session.execute(stmt)
    await session.commit()
    return (await reviews_for(session, owner_id, [receipt_id]))[receipt_id]


async def delete_review(
    session: AsyncSession, owner_id: UUID, receipt_id: UUID
) -> None:
    await owned_lines(session, owner_id, receipt_id)
    await session.execute(
        delete(AiReceiptReview).where(
            AiReceiptReview.owner_id == owner_id,
            AiReceiptReview.receipt_id == receipt_id,
        )
    )
    await session.commit()
