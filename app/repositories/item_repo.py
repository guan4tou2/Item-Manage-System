from typing import Dict, Any, Iterable, Optional, List, Tuple

from app import mongo


def list_items(
    filter_query: Dict[str, Any],
    projection: Dict[str, Any],
    sort: Optional[List[Tuple[str, int]]] = None,
    skip: int = 0,
    limit: int = 0,
) -> Iterable[Dict[str, Any]]:
    """查詢物品列表，支援分頁"""
    cursor = mongo.db.item.find(filter_query, projection)
    if sort:
        cursor = cursor.sort(sort)
    if skip > 0:
        cursor = cursor.skip(skip)
    if limit > 0:
        cursor = cursor.limit(limit)
    return cursor


def count_items(filter_query: Dict[str, Any]) -> int:
    """計算符合條件的物品數量"""
    return mongo.db.item.count_documents(filter_query)


def insert_item(item: Dict[str, Any]) -> None:
    mongo.db.item.insert_one(item)


def update_item_by_id(item_id: str, updates: Dict[str, Any]) -> None:
    mongo.db.item.update_one({"ItemID": item_id}, {"$set": updates})


def find_item_by_id(item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    return mongo.db.item.find_one({"ItemID": item_id}, projection)


def delete_item_by_id(item_id: str) -> bool:
    """刪除物品，回傳是否成功"""
    result = mongo.db.item.delete_one({"ItemID": item_id})
    return result.deleted_count > 0


def ensure_indexes() -> None:
    """建立資料庫索引"""
    # ItemID 唯一索引
    mongo.db.item.create_index("ItemID", unique=True, background=True)
    # 常用搜尋欄位索引
    mongo.db.item.create_index("ItemName", background=True)
    mongo.db.item.create_index("ItemType", background=True)
    mongo.db.item.create_index("ItemFloor", background=True)
    mongo.db.item.create_index("ItemRoom", background=True)
    mongo.db.item.create_index("ItemZone", background=True)
    # 複合索引 - 位置層級搜尋
    mongo.db.item.create_index(
        [("ItemFloor", 1), ("ItemRoom", 1), ("ItemZone", 1)],
        background=True
    )
    # 到期日期索引
    mongo.db.item.create_index("WarrantyExpiry", background=True)
    mongo.db.item.create_index("UsageExpiry", background=True)


def get_stats() -> Dict[str, int]:
    """取得物品統計資訊"""
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


def get_all_items_for_export(projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """取得所有物品用於匯出"""
    if projection is None:
        projection = {"_id": 0}
    return list(mongo.db.item.find({}, projection))


def toggle_favorite(item_id: str, user_id: str) -> bool:
    """切換收藏狀態，回傳新的收藏狀態"""
    item = mongo.db.item.find_one({"ItemID": item_id})
    if not item:
        return False
    
    favorites = item.get("favorites", [])
    if user_id in favorites:
        # 取消收藏
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$pull": {"favorites": user_id}}
        )
        return False
    else:
        # 加入收藏
        mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$addToSet": {"favorites": user_id}}
        )
        return True


def get_favorites(user_id: str, projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """取得使用者收藏的物品"""
    if projection is None:
        projection = {"_id": 0}
    return list(mongo.db.item.find({"favorites": user_id}, projection))


def is_favorite(item_id: str, user_id: str) -> bool:
    """檢查物品是否被收藏"""
    item = mongo.db.item.find_one({"ItemID": item_id, "favorites": user_id})
    return item is not None


def add_move_history(item_id: str, from_location: str, to_location: str) -> None:
    """新增移動歷史記錄"""
    from datetime import datetime
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "from_location": from_location,
        "to_location": to_location,
    }
    mongo.db.item.update_one(
        {"ItemID": item_id},
        {"$push": {"move_history": record}}
    )

