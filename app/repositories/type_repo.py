"""物品類型資料存取模組"""
from typing import List
from flask import current_app

from app import mongo, db, get_db_type, cache
from app.models.item_type import ItemType


def list_types() -> List[dict]:
    db_type = get_db_type()
    cache_key = f"types_list_{db_type}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    if db_type == "postgres":
        types = db.session.query(ItemType).all()
        result = [{"id": t.id, "name": t.name} for t in types]
    else:
        types = mongo.db.type.find({})
        result = [{"id": t["_id"], "name": t["name"]} for t in types]

    cache.set(cache_key, result, timeout=300)  # 5 minutes cache
    return result


def insert_type(name: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        item_type = ItemType(name=name)
        db.session.add(item_type)
        db.session.commit()
    else:
        mongo.db.type.insert_one({"name": name})

    # Invalidate cache
    cache.delete(f"types_list_{db_type}")


def delete_type(name: str) -> bool:
    db_type = get_db_type()
    if db_type == "postgres":
        result = ItemType.query.filter_by(name=name).delete()
        db.session.commit()
    else:
        result = mongo.db.type.delete_one({"name": name})

    # Invalidate cache
    cache.delete(f"types_list_{db_type}")

    return result.deleted_count > 0 if db_type == "postgres" else result.deleted_count > 0


def get_type_by_name(name: str):
    db_type = get_db_type()
    if db_type == "postgres":
        return ItemType.query.filter_by(name=name).first()
    return mongo.db.type.find_one({"name": name})
