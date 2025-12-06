from typing import Dict, Any, Iterable, Optional, List, Tuple

from app import mongo


def list_items(
    filter_query: Dict[str, Any],
    projection: Dict[str, Any],
    sort: Optional[List[Tuple[str, int]]] = None,
) -> Iterable[Dict[str, Any]]:
    cursor = mongo.db.item.find(filter_query, projection)
    if sort:
        cursor = cursor.sort(sort)
    return cursor


def insert_item(item: Dict[str, Any]) -> None:
    mongo.db.item.insert_one(item)


def update_item_by_id(item_id: str, updates: Dict[str, Any]) -> None:
    mongo.db.item.update_one({"ItemID": item_id}, {"$set": updates})


def find_item_by_id(item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    return mongo.db.item.find_one({"ItemID": item_id}, projection)

