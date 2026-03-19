from typing import List, Dict, Any, Tuple, Optional

from app.repositories import location_repo
from bson import ObjectId
from app import get_db_type


def list_locations() -> List[Dict[str, Any]]:
    locs = []
    for l in location_repo.list_locations():
        l = dict(l)
        l["_id"] = str(l["_id"])
        locs.append(l)
    return locs


def list_choices() -> Tuple[List[str], List[str], List[str]]:
    locs = list_locations()
    floors = sorted({l.get("floor", "") for l in locs if l.get("floor")})
    rooms = sorted({l.get("room", "") for l in locs if l.get("room")})
    zones = sorted({l.get("zone", "") for l in locs if l.get("zone")})
    return floors, rooms, zones


def create_location(doc: Dict[str, Any]) -> Tuple[bool, str]:
    """建立新位置選項，回傳 (成功, 訊息)"""
    # 檢查是否有至少一個欄位
    if not any([doc.get("floor"), doc.get("room"), doc.get("zone")]):
        return False, "請至少填寫一個欄位"
    
    # 重複檢查
    existing = list_locations()
    for loc in existing:
        if (loc.get("floor") == doc.get("floor") and 
            loc.get("room") == doc.get("room") and 
            loc.get("zone") == doc.get("zone")):
            return False, "該位置選項已存在"
    
    location_repo.insert_location(doc)
    return True, "位置選項已新增"


def delete_location(loc_id: str) -> None:
    try:
        oid = ObjectId(loc_id)
    except Exception:
        return
    location_repo.delete_location(oid)


def update_location(loc_id: str, doc: Dict[str, Any]) -> None:
    try:
        oid = ObjectId(loc_id)
    except Exception:
        return
    location_repo.update_location(oid, doc)


def update_order(order_list: List[Dict[str, Any]]) -> None:
    """更新位置排序"""
    for item in order_list:
        try:
            oid = ObjectId(item.get("id"))
            order = item.get("order", 0)
            location_repo.update_order(oid, order)
        except Exception:
            continue


# ------------------------------------------------------------------
# Feature 18: Location Map Visualization helpers
# ------------------------------------------------------------------

def get_floor_plan_image(floor: str) -> Optional[str]:
    """回傳指定樓層的平面圖檔名（或 None）。"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app import db
        from app.models.location import Location

        loc = (
            db.session.query(Location)
            .filter(Location.floor == floor, Location.floor_plan_image != None)
            .first()
        )
        return loc.floor_plan_image if loc else None
    else:
        from app import mongo

        doc = mongo.db.locations.find_one(
            {"floor": floor, "floor_plan_image": {"$exists": True, "$ne": None}}
        )
        return doc.get("floor_plan_image") if doc else None


def set_floor_plan_image(floor: str, filename: str) -> bool:
    """更新指定樓層第一個位置記錄的平面圖，回傳是否成功。"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app import db
        from app.models.location import Location

        loc = db.session.query(Location).filter(Location.floor == floor).first()
        if not loc:
            return False
        loc.floor_plan_image = filename
        db.session.commit()
        return True
    else:
        from app import mongo

        result = mongo.db.locations.update_one(
            {"floor": floor},
            {"$set": {"floor_plan_image": filename}},
        )
        return result.matched_count > 0


def update_item_position(item_id: str, x: int, y: int) -> bool:
    """更新物品在平面圖上的座標，回傳是否成功。"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app import db
        from app.models.item import Item

        item = db.session.query(Item).filter(Item.ItemID == item_id).first()
        if not item:
            return False
        item.map_x = x
        item.map_y = y
        db.session.commit()
        return True
    else:
        from app import mongo

        result = mongo.db.item.update_one(
            {"ItemID": item_id},
            {"$set": {"map_x": x, "map_y": y}},
        )
        return result.matched_count > 0


def get_items_with_positions(floor: str) -> List[Dict[str, Any]]:
    """回傳指定樓層所有有座標的物品清單。"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app import db
        from app.models.item import Item

        items = (
            db.session.query(Item)
            .filter(
                Item.ItemFloor == floor,
                Item.map_x != None,
                Item.map_y != None,
            )
            .all()
        )
        return [
            {
                "ItemID": item.ItemID,
                "ItemName": item.ItemName,
                "map_x": item.map_x,
                "map_y": item.map_y,
            }
            for item in items
        ]
    else:
        from app import mongo

        cursor = mongo.db.item.find(
            {"ItemFloor": floor, "map_x": {"$ne": None}, "map_y": {"$ne": None}},
            {"ItemID": 1, "ItemName": 1, "map_x": 1, "map_y": 1, "_id": 0},
        )
        return list(cursor)

