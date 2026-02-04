"""物品資料存取模組"""
from typing import Dict, Any, Iterable, Optional, List, Tuple
from datetime import datetime, date, timedelta

from sqlalchemy import or_, and_
from app import mongo, db, get_db_type
from app.models.item import Item


def list_items(
    filter_query: Dict[str, Any],
    projection: Dict[str, Any],
    sort: Optional[List[Tuple[str, int]]] = None,
    skip: int = 0,
    limit: int = 0,
) -> Iterable[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        query = db.session.query(Item)
        
        if "ItemName" in filter_query and filter_query["ItemName"]:
            query = query.filter(Item.ItemName.ilike(f"%{filter_query['ItemName']}%"))
        if "ItemStorePlace" in filter_query and filter_query["ItemStorePlace"]:
            query = query.filter(Item.ItemStorePlace.ilike(f"%{filter_query['ItemStorePlace']}%"))
        if "ItemType" in filter_query and filter_query["ItemType"]:
            query = query.filter(Item.ItemType == filter_query["ItemType"])
        if "ItemFloor" in filter_query and filter_query["ItemFloor"]:
            query = query.filter(Item.ItemFloor == filter_query["ItemFloor"])
        if "ItemRoom" in filter_query and filter_query["ItemRoom"]:
            query = query.filter(Item.ItemRoom == filter_query["ItemRoom"])
        if "ItemZone" in filter_query and filter_query["ItemZone"]:
            query = query.filter(Item.ItemZone == filter_query["ItemZone"])
        
        if sort:
            for field, direction in sort:
                attr = getattr(Item, field)
                query = query.order_by(attr.asc() if direction == 1 else attr.desc())
        
        if skip > 0:
            query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)
        
        return [item.to_dict() for item in query.all()]
    
    cursor = mongo.db.item.find(filter_query, projection)
    if sort:
        cursor = cursor.sort(sort)
    if skip > 0:
        cursor = cursor.skip(skip)
    if limit > 0:
        cursor = cursor.limit(limit)
    return cursor


def count_items(filter_query: Dict[str, Any]) -> int:
    db_type = get_db_type()
    if db_type == "postgres":
        query = db.session.query(Item)
        
        if "ItemName" in filter_query and filter_query["ItemName"]:
            query = query.filter(Item.ItemName.ilike(f"%{filter_query['ItemName']}%"))
        if "ItemStorePlace" in filter_query and filter_query["ItemStorePlace"]:
            query = query.filter(Item.ItemStorePlace.ilike(f"%{filter_query['ItemStorePlace']}%"))
        if "ItemType" in filter_query and filter_query["ItemType"]:
            query = query.filter(Item.ItemType == filter_query["ItemType"])
        if "ItemFloor" in filter_query and filter_query["ItemFloor"]:
            query = query.filter(Item.ItemFloor == filter_query["ItemFloor"])
        if "ItemRoom" in filter_query and filter_query["ItemRoom"]:
            query = query.filter(Item.ItemRoom == filter_query["ItemRoom"])
        if "ItemZone" in filter_query and filter_query["ItemZone"]:
            query = query.filter(Item.ItemZone == filter_query["ItemZone"])
        
        return query.count()
    
    return mongo.db.item.count_documents(filter_query)


def insert_item(item: Dict[str, Any]) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        new_item = Item(**item)
        db.session.add(new_item)
        db.session.commit()
    else:
        mongo.db.item.insert_one(item)


def update_item_by_id(item_id: str, updates: Dict[str, Any]) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        Item.query.filter_by(ItemID=item_id).update(updates)
        db.session.commit()
    else:
        mongo.db.item.update_one({"ItemID": item_id}, {"$set": updates})


def find_item_by_id(item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        item = Item.query.filter_by(ItemID=item_id).first()
        return item.to_dict() if item else None
    return mongo.db.item.find_one({"ItemID": item_id}, projection)


def delete_item_by_id(item_id: str) -> bool:
    db_type = get_db_type()
    if db_type == "postgres":
        result = Item.query.filter_by(ItemID=item_id).delete()
        db.session.commit()
        return result > 0
    result = mongo.db.item.delete_one({"ItemID": item_id})
    return result.deleted_count > 0


def ensure_indexes() -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        db.create_all()
    else:
        mongo.db.item.create_index("ItemID", unique=True, background=True)
        mongo.db.item.create_index("ItemName", background=True)
        mongo.db.item.create_index("ItemType", background=True)
        mongo.db.item.create_index("ItemFloor", background=True)
        mongo.db.item.create_index("ItemRoom", background=True)
        mongo.db.item.create_index("ItemZone", background=True)
        mongo.db.item.create_index([("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)], background=True)
        mongo.db.item.create_index("WarrantyExpiry", background=True)
        mongo.db.item.create_index("UsageExpiry", background=True)


def get_stats() -> Dict[str, int]:
    db_type = get_db_type()
    if db_type == "postgres":
        total = db.session.query(Item).count()
        with_photo = db.session.query(Item).filter(Item.ItemPic != "", Item.ItemPic.isnot(None)).count()
        with_location = db.session.query(Item).filter(Item.ItemStorePlace != "", Item.ItemStorePlace.isnot(None)).count()
        with_type = db.session.query(Item).filter(Item.ItemType != "", Item.ItemType.isnot(None)).count()
    else:
        total = mongo.db.item.count_documents({})
        with_photo = mongo.db.item.count_documents({"ItemPic": {"$ne": "", "$exists": True}})
        with_location = mongo.db.item.count_documents({"ItemStorePlace": {"$ne": "", "$exists": True}})
        with_type = mongo.db.item.count_documents({"ItemType": {"$ne": "", "$exists": True}})
    
    return {
        "total": total,
        "with_photo": with_photo,
        "with_location": with_location,
        "with_type": with_type,
    }


def get_all_items_for_export(
    filters: Optional[Dict[str, Any]] = None,
    projection: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    query = filters or {}
    if db_type == "postgres":
        items_query = db.session.query(Item)
        for key, value in query.items():
            if value is not None:
                items_query = items_query.filter(getattr(Item, key) == value)
        items = items_query.all()
        return [item.to_dict() for item in items]
    if projection is None:
        projection = {"_id": 0}
    return list(mongo.db.item.find(query, projection))


def toggle_favorite(item_id: str, user_id: str) -> bool:
    db_type = get_db_type()
    if db_type == "postgres":
        item = Item.query.filter_by(ItemID=item_id).first()
        if not item:
            return False
        
        favorites = item.favorites or []
        if user_id in favorites:
            favorites.remove(user_id)
            is_fav = False
        else:
            favorites.append(user_id)
            is_fav = True
        
        item.favorites = favorites
        db.session.commit()
        return is_fav
    
    item = mongo.db.item.find_one({"ItemID": item_id})
    if not item:
        return False
    
    favorites = item.get("favorites", [])
    if user_id in favorites:
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$pull": {"favorites": user_id}}
        )
        return False
    else:
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$addToSet": {"favorites": user_id}}
        )
        return True


def get_favorites(user_id: str, projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        from sqlalchemy import text

        items = Item.query.filter(
            text("favorites @> :pattern")
        ).params(pattern=f'["{user_id}"]').all()
        return [item.to_dict() for item in items]
    if projection is None:
        projection = {"_id": 0}
    return list(mongo.db.item.find({"favorites": user_id}, projection))


def is_favorite(item_id: str, user_id: str) -> bool:
    db_type = get_db_type()
    if db_type == "postgres":
        from sqlalchemy import text

        item = Item.query.filter(
            Item.ItemID == item_id,
            text("favorites @> :pattern")
        ).params(pattern=f'["{user_id}"]').first()
        return item is not None
    item = mongo.db.item.find_one({"ItemID": item_id, "favorites": user_id})
    return item is not None


def add_move_history(item_id: str, from_location: str, to_location: str) -> None:
    db_type = get_db_type()
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "from_location": from_location,
        "to_location": to_location,
    }
    
    if db_type == "postgres":
        item = Item.query.filter_by(ItemID=item_id).first()
        if item:
            item.move_history = (item.move_history or []) + [record]
            db.session.commit()
    else:
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$push": {"move_history": record}}
        )


def add_related_item(item_id: str, related_id: str, relation_type: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        item = Item.query.filter_by(ItemID=item_id).first()
        if item:
            existing = any(r["id"] == related_id for r in (item.related_items or []))
            if not existing:
                item.related_items = (item.related_items or []) + [{"id": related_id, "type": relation_type}]
                db.session.commit()
    else:
        item = mongo.db.item.find_one({"ItemID": item_id, "related_items.id": related_id})
        if not item:
            mongo.db.item.update_one(
                {"ItemID": item_id},
                {"$addToSet": {"related_items": {"id": related_id, "type": relation_type}}}
            )


def remove_related_item(item_id: str, related_id: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        item = Item.query.filter_by(ItemID=item_id).first()
        if item:
            item.related_items = [r for r in (item.related_items or []) if r["id"] != related_id]
            db.session.commit()
    else:
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$pull": {"related_items": {"id": related_id}}}
        )


def update_item_field(item_id: str, field: str, value: Any) -> bool:
    db_type = get_db_type()
    if db_type == "postgres":
        result = Item.query.filter_by(ItemID=item_id).update({field: value})
        db.session.commit()
        return result > 0
    result = mongo.db.item.update_one(
        {"ItemID": item_id},
        {"$set": {field: value}}
    )
    return result.modified_count > 0


def get_expiring_items(days_threshold: int = 30) -> List[Dict[str, Any]]:
    """Get items expiring within the specified number of days

    This query is optimized to filter at the database level instead of
    loading all items and filtering in Python.
    """
    db_type = get_db_type()
    today = date.today()
    threshold_date = today + timedelta(days=days_threshold)

    if db_type == "postgres":
        expired_items = Item.query.filter(
            or_(
                Item.WarrantyExpiry < today,
                Item.UsageExpiry < today
            )
        ).all()

        near_expiry_items = Item.query.filter(
            and_(
                Item.WarrantyExpiry >= today,
                Item.WarrantyExpiry <= threshold_date
            )
        ).union(
            Item.query.filter(
                and_(
                    Item.UsageExpiry >= today,
                    Item.UsageExpiry <= threshold_date
                )
            )
        ).all()

        items = expired_items + near_expiry_items
        return [item.to_dict() for item in items]
    else:
        from pymongo import ASCENDING

        expired_items = list(mongo.db.item.find({
            "$or": [
                {"WarrantyExpiry": {"$lt": today.strftime("%Y-%m-%d")}},
                {"UsageExpiry": {"$lt": today.strftime("%Y-%m-%d")}}
            ]
        }))

        threshold_str = threshold_date.strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        near_expiry_items = list(mongo.db.item.find({
            "$or": [
                {
                    "WarrantyExpiry": {"$gte": today_str, "$lte": threshold_str}
                },
                {
                    "UsageExpiry": {"$gte": today_str, "$lte": threshold_str}
                }
            ]
        }))

        items = expired_items + near_expiry_items
        for item in items:
            item["_id"] = str(item["_id"])
        return items


def search_suggestions(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """取得搜尋自動完成建議"""
    db_type = get_db_type()
    suggestions = []

    if db_type == "postgres":
        name_results = db.session.query(
            Item.ItemName, Item.ItemID, Item.ItemType
        ).filter(
            Item.ItemName.ilike(f"%{query}%")
        ).limit(5).all()

        for item in name_results:
            suggestions.append({
                "text": item.ItemName,
                "id": item.ItemID,
                "type": item.ItemType or "",
                "category": "name"
            })

        id_results = db.session.query(
            Item.ItemName, Item.ItemID, Item.ItemType
        ).filter(
            Item.ItemID.ilike(f"%{query}%")
        ).limit(3).all()

        for item in id_results:
            if not any(s["id"] == item.ItemID for s in suggestions):
                suggestions.append({
                    "text": item.ItemID,
                    "id": item.ItemID,
                    "name": item.ItemName,
                    "type": item.ItemType or "",
                    "category": "id"
                })
    else:
        name_results = mongo.db.item.find(
            {"ItemName": {"$regex": query, "$options": "i"}},
            {"ItemName": 1, "ItemID": 1, "ItemType": 1, "_id": 0}
        ).limit(5)

        for item in name_results:
            suggestions.append({
                "text": item.get("ItemName", ""),
                "id": item.get("ItemID", ""),
                "type": item.get("ItemType", ""),
                "category": "name"
            })

        id_results = mongo.db.item.find(
            {"ItemID": {"$regex": query, "$options": "i"}},
            {"ItemName": 1, "ItemID": 1, "ItemType": 1, "_id": 0}
        ).limit(3)

        for item in id_results:
            if not any(s["id"] == item.get("ItemID") for s in suggestions):
                suggestions.append({
                    "text": item.get("ItemID", ""),
                    "id": item.get("ItemID", ""),
                    "name": item.get("ItemName", ""),
                    "type": item.get("ItemType", ""),
                    "category": "id"
                })

    return suggestions[:limit]


def get_all_items_for_backup() -> List[Dict[str, Any]]:
    """取得所有物品資料（用於備份）"""
    db_type = get_db_type()
    if db_type == "postgres":
        return [item.to_dict() for item in Item.query.all()]
    else:
        items = list(mongo.db.item.find({}, {"_id": 0}))
        return items


def restore_items(items: List[Dict[str, Any]], mode: str = "merge") -> int:
    """還原物品資料"""
    db_type = get_db_type()
    count = 0

    if db_type == "postgres":
        for item_data in items:
            item_id = item_data.get("ItemID")
            if not item_id:
                continue

            existing = Item.query.filter_by(ItemID=item_id).first()

            if mode == "replace" and existing:
                db.session.delete(existing)
                db.session.commit()
                existing = None

            if not existing:
                item = Item(
                    ItemID=item_id,
                    ItemName=item_data.get("ItemName", ""),
                    ItemDesc=item_data.get("ItemDesc", ""),
                    ItemPic=item_data.get("ItemPic", ""),
                    ItemThumb=item_data.get("ItemThumb", ""),
                    ItemPics=item_data.get("ItemPics", []),
                    ItemStorePlace=item_data.get("ItemStorePlace", ""),
                    ItemType=item_data.get("ItemType", ""),
                    ItemOwner=item_data.get("ItemOwner", ""),
                    ItemGetDate=item_data.get("ItemGetDate", ""),
                    ItemFloor=item_data.get("ItemFloor", ""),
                    ItemRoom=item_data.get("ItemRoom", ""),
                    ItemZone=item_data.get("ItemZone", ""),
                    Quantity=item_data.get("Quantity", 0),
                    SafetyStock=item_data.get("SafetyStock", 0),
                    ReorderLevel=item_data.get("ReorderLevel", 0),
                )
                db.session.add(item)
                count += 1
            elif mode == "merge":
                for key, value in item_data.items():
                    if hasattr(existing, key) and key != "ItemID":
                        setattr(existing, key, value)
                count += 1

        db.session.commit()
    else:
        for item_data in items:
            item_id = item_data.get("ItemID")
            if not item_id:
                continue

            if mode == "replace":
                mongo.db.item.delete_one({"ItemID": item_id})

            if not mongo.db.item.find_one({"ItemID": item_id}):
                mongo.db.item.insert_one(item_data)
                count += 1
            elif mode == "merge":
                mongo.db.item.update_one(
                    {"ItemID": item_id},
                    {"$set": item_data}
                )
                count += 1

    return count
