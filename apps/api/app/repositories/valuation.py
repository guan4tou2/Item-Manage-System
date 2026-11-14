"""統計與報表共用的物品估值／未定價定義（Phase 49 D3／D4）。"""

from sqlalchemy import case, func, select

from app.models.item import Item
from app.models.item_batch import ItemBatch


def item_value():
    """批次依有效單價加總；一般物品沿用單價乘數量。"""
    batch_value = (
        select(
            func.sum(
                ItemBatch.quantity * func.coalesce(ItemBatch.unit_cost, Item.cost, 0)
            )
        )
        .where(ItemBatch.item_id == Item.id, ItemBatch.is_depleted.is_(False))
        .correlate(Item)
        .scalar_subquery()
    )
    return case(
        (Item.track_batches.is_(True), func.coalesce(batch_value, 0)),
        else_=func.coalesce(Item.cost * Item.quantity, 0),
    )


def item_unpriced():
    """批次物品須有未耗盡且未定價的批次；空批次不算未定價。"""
    unpriced_batch = (
        select(ItemBatch.id)
        .where(
            ItemBatch.item_id == Item.id,
            ItemBatch.is_depleted.is_(False),
            ItemBatch.unit_cost.is_(None),
            Item.cost.is_(None),
        )
        .correlate(Item)
        .exists()
    )
    return case(
        (Item.track_batches.is_(True), unpriced_batch), else_=Item.cost.is_(None)
    )
