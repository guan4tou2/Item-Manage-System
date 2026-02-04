"""位置資料存取模組"""
from typing import List, Generator, Dict, Any, Optional
from flask import current_app

from app import mongo, db, get_db_type, cache


def list_locations() -> Generator[Dict[str, Any], None, None]:
    """列出所有位置"""
    db_type = get_db_type()
    cache_key = f"locations_list_{db_type}"

    cached = cache.get(cache_key)
    if cached:
        for loc in cached:
            yield loc
        return

    if db_type == "postgres":
        from app.models.location import Location

        locations = db.session.query(Location).order_by(Location.order).all()
        result = [loc.to_dict() for loc in locations]
    else:
        result = list(mongo.db.locations.find().sort("order", 1))

    cache.set(cache_key, result, timeout=300)  # 5 minutes cache
    for loc in result:
        yield loc


def insert_location(doc: Dict[str, Any]) -> None:
    """插入新位置"""
    db_type = get_db_type()

    if db_type == "postgres":
        from app.models.location import Location

        location = Location(
            floor=doc.get("floor"),
            room=doc.get("room"),
            zone=doc.get("zone"),
            order=doc.get("order", 0),
        )
        db.session.add(location)
        db.session.commit()
    else:
        mongo.db.locations.insert_one(doc)


def delete_location(loc_id) -> None:
    """刪除位置"""
    db_type = get_db_type()

    if db_type == "postgres":
        from app.models.location import Location

        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            db.session.delete(location)
            db.session.commit()
    else:
        mongo.db.locations.delete_one({"_id": loc_id})


def update_location(loc_id, doc: Dict[str, Any]) -> None:
    """更新位置"""
    db_type = get_db_type()

    if db_type == "postgres":
        from app.models.location import Location

        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            if "floor" in doc:
                location.floor = doc["floor"]
            if "room" in doc:
                location.room = doc["room"]
            if "zone" in doc:
                location.zone = doc["zone"]
            if "order" in doc:
                location.order = doc["order"]
            db.session.commit()
    else:
        mongo.db.locations.update_one({"_id": loc_id}, {"$set": doc})


def update_order(loc_id, order: int) -> None:
    """更新位置排序"""
    db_type = get_db_type()

    if db_type == "postgres":
        from app.models.location import Location

        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            location.order = order
            db.session.commit()
    else:
        mongo.db.locations.update_one({"_id": loc_id}, {"$set": {"order": order}})


def list_choices() -> tuple:
    """列出所有樓層、房間、區域選項"""
    db_type = get_db_type()

    if db_type == "postgres":
        from app.models.item import Item
        from app.models.location import Location

        floors = [i[0] for i in db.session.query(Item.ItemFloor).distinct().filter(Item.ItemFloor != None).all()]
        rooms = [i[0] for i in db.session.query(Item.ItemRoom).distinct().filter(Item.ItemRoom != None).all()]
        zones = [i[0] for i in db.session.query(Item.ItemZone).distinct().filter(Item.ItemZone != None).all()]
    else:
        floors = mongo.db.item.distinct("ItemFloor")
        rooms = mongo.db.item.distinct("ItemRoom")
        zones = mongo.db.item.distinct("ItemZone")

    return (floors, rooms, zones)


def get_all_locations_for_backup() -> List[Dict[str, Any]]:
    """取得所有位置資料（用於備份）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.location import Location
        return [loc.to_dict() for loc in Location.query.all()]
    else:
        return list(mongo.db.locations.find({}, {"_id": 0}))


def find_location(floor: str, room: str, zone: str) -> Optional[Dict[str, Any]]:
    """根據樓層/房間/區域尋找位置"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.location import Location
        loc = Location.query.filter_by(floor=floor, room=room, zone=zone).first()
        return loc.to_dict() if loc else None
    else:
        return mongo.db.locations.find_one({"floor": floor, "room": room, "zone": zone})


def restore_locations(locations: List[Dict[str, Any]], mode: str = "merge") -> int:
    """還原位置資料"""
    count = 0

    for loc in locations:
        floor = loc.get("floor", "")
        room = loc.get("room", "")
        zone = loc.get("zone", "")

        existing = find_location(floor, room, zone)
        if not existing:
            insert_location(loc)
            count += 1

    return count
