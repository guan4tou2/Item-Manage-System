from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, item_tags


def normalize(name: str) -> str:
    return name.strip().lower()


async def list_for_owner(session: AsyncSession, owner_id: UUID, q: str | None = None) -> list[Tag]:
    stmt = select(Tag).where(Tag.owner_id == owner_id).order_by(Tag.name)
    if q:
        needle = normalize(q)
        stmt = stmt.where(Tag.name.ilike(f"{needle}%"))
    return list((await session.execute(stmt)).scalars().all())


async def list_with_counts(
    session: AsyncSession, owner_id: UUID
) -> list[tuple[Tag, int]]:
    """Return (tag, item_count) for every tag owned by owner_id.

    Tags with zero items are included (LEFT OUTER JOIN).
    """
    stmt = (
        select(Tag, func.count(item_tags.c.item_id).label("item_count"))
        .outerjoin(item_tags, item_tags.c.tag_id == Tag.id)
        .where(Tag.owner_id == owner_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], int(row[1])) for row in rows]


async def get_by_id(session: AsyncSession, owner_id: UUID, tag_id: int) -> Tag | None:
    stmt = select(Tag).where(Tag.owner_id == owner_id, Tag.id == tag_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_name(session: AsyncSession, owner_id: UUID, name: str) -> Tag | None:
    stmt = select(Tag).where(Tag.owner_id == owner_id, Tag.name == normalize(name))
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_items(session: AsyncSession, tag_id: int) -> int:
    stmt = select(func.count()).where(item_tags.c.tag_id == tag_id)
    return int((await session.execute(stmt)).scalar_one())


async def rename(session: AsyncSession, tag: Tag, new_name: str) -> Tag:
    tag.name = normalize(new_name)
    await session.commit()
    await session.refresh(tag)
    return tag


async def merge(
    session: AsyncSession, source: Tag, target: Tag
) -> int:
    """Merge source tag into target tag.

    Reassigns all item_tags rows pointing at source to point at target
    (deduping any rows where the item was already tagged with target),
    then deletes source. Returns the number of item_tags rows that
    actually got moved to target (excluding the deduped overlaps).
    """
    # 1. Find items already tagged with target — their source row is a
    #    duplicate and must be deleted, not reassigned.
    already_stmt = (
        select(item_tags.c.item_id)
        .where(item_tags.c.tag_id == target.id)
    )
    already_ids = set(
        r[0] for r in (await session.execute(already_stmt)).all()
    )

    # 2. Count how many items currently point at source.
    src_stmt = select(item_tags.c.item_id).where(item_tags.c.tag_id == source.id)
    src_ids = set(r[0] for r in (await session.execute(src_stmt)).all())

    # 3. Delete duplicate source rows (item had both tags).
    overlap = already_ids & src_ids
    if overlap:
        await session.execute(
            delete(item_tags).where(
                item_tags.c.tag_id == source.id,
                item_tags.c.item_id.in_(overlap),
            )
        )

    # 4. Reassign the remaining source rows to target.
    reassignable = src_ids - already_ids
    if reassignable:
        await session.execute(
            update(item_tags)
            .where(item_tags.c.tag_id == source.id)
            .values(tag_id=target.id)
        )

    # 5. Remove the source tag.
    await session.delete(source)
    await session.commit()
    return len(reassignable)


async def delete_tag(session: AsyncSession, tag: Tag) -> None:
    """Unconditional delete. Callers are expected to check usage first."""
    await session.delete(tag)
    await session.commit()


async def prune_orphans(session: AsyncSession, owner_id: UUID) -> int:
    """Delete every tag owned by owner_id that has zero items linked.

    Returns the number of tags deleted.
    """
    subq = select(item_tags.c.tag_id).distinct().subquery()
    stmt = (
        select(Tag)
        .where(Tag.owner_id == owner_id, Tag.id.notin_(select(subq.c.tag_id)))
    )
    orphans = list((await session.execute(stmt)).scalars().all())
    for tag in orphans:
        await session.delete(tag)
    if orphans:
        await session.commit()
    return len(orphans)


async def get_or_create_many(
    session: AsyncSession, owner_id: UUID, names: list[str]
) -> list[Tag]:
    result: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        n = normalize(raw)
        if not n or n in seen:
            continue
        seen.add(n)
        existing = await get_by_name(session, owner_id, n)
        if existing:
            result.append(existing)
        else:
            tag = Tag(owner_id=owner_id, name=n)
            session.add(tag)
            await session.flush()
            result.append(tag)
    return result
