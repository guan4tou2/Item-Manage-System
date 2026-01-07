"""MongoDB repository implementations"""
from typing import List, Dict, Any, Optional, Generator, Tuple
from datetime import date, timedelta

from app import mongo, cache
from app.models.item import Item
from app.repositories.base import BaseRepository, TypeRepository, LocationRepository


class MongoItemRepository(BaseRepository):
    """MongoDB implementation for Item repository"""

    def find_by_id(self, item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        result = mongo.db.item.find_one({"ItemID": item_id}, projection)
        if result:
            result["_id"] = str(result["_id"])
        return result

    def insert(self, item: Dict[str, Any]) -> None:
        mongo.db.item.insert_one(item)

    def update(self, item_id: str, updates: Dict[str, Any]) -> None:
        mongo.db.item.update_one({"ItemID": item_id}, {"$set": updates})

    def delete(self, item_id: str) -> bool:
        result = mongo.db.item.delete_one({"ItemID": item_id})
        return result.deleted_count > 0

    def list_all(
        self,
        filter_query: Dict[str, Any],
        sort: Optional[List[Tuple[str, int]]] = None,
        skip: int = 0,
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        cursor = mongo.db.item.find(filter_query)
        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)

    def count(self, filter_query: Dict[str, Any]) -> int:
        return mongo.db.item.count_documents(filter_query)

    def get_expiring_items(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        from pymongo import ASCENDING

        today = date.today()
        threshold_date = today + timedelta(days=days_threshold)
        today_str = today.strftime("%Y-%m-%d")
        threshold_str = threshold_date.strftime("%Y-%m-%d")

        expired_items = list(mongo.db.item.find({
            "$or": [
                {"WarrantyExpiry": {"$lt": today_str}},
                {"UsageExpiry": {"$lt": today_str}}
            ]
        }))

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


class MongoTypeRepository(TypeRepository):
    """MongoDB implementation for Type repository"""

    def list_all(self) -> List[Dict[str, Any]]:
        cache_key = "types_list_mongo"

        cached = cache.get(cache_key)
        if cached:
            return cached

        types = mongo.db.type.find({})
        result = [{"id": t["_id"], "name": t["name"]} for t in types]

        cache.set(cache_key, result, timeout=300)
        return result

    def insert(self, name: str) -> None:
        mongo.db.type.insert_one({"name": name})
        cache.delete("types_list_mongo")

    def delete(self, name: str) -> bool:
        result = mongo.db.type.delete_one({"name": name})
        cache.delete("types_list_mongo")
        return result.deleted_count > 0

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cache_key = f"type_by_name_{name}"

        cached = cache.get(cache_key)
        if cached:
            return cached

        result = mongo.db.type.find_one({"name": name})
        if result:
            result["_id"] = str(result["_id"])

        if result:
            cache.set(cache_key, result, timeout=300)

        return result


class MongoLocationRepository(LocationRepository):
    """MongoDB implementation for Location repository"""

    def list_all(self) -> Generator[Dict[str, Any], None, None]:
        cache_key = "locations_list_mongo"

        cached = cache.get(cache_key)
        if cached:
            for loc in cached:
                yield loc
            return

        result = list(mongo.db.locations.find().sort("order", 1))
        cache.set(cache_key, result, timeout=300)

        for loc in result:
            yield loc

    def insert(self, doc: Dict[str, Any]) -> None:
        mongo.db.locations.insert_one(doc)
        cache.delete("locations_list_mongo")

    def delete(self, loc_id) -> None:
        mongo.db.locations.delete_one({"_id": loc_id})
        cache.delete("locations_list_mongo")

    def update(self, loc_id, doc: Dict[str, Any]) -> None:
        mongo.db.locations.update_one({"_id": loc_id}, {"$set": doc})
        cache.delete("locations_list_mongo")

    def update_order(self, loc_id, order: int) -> None:
        mongo.db.locations.update_one({"_id": loc_id}, {"$set": {"order": order}})
        cache.delete("locations_list_mongo")

    def list_choices(self) -> Tuple[List[str], List[str], List[str]]:
        floors = mongo.db.item.distinct("ItemFloor")
        rooms = mongo.db.item.distinct("ItemRoom")
        zones = mongo.db.item.distinct("ItemZone")

        return (floors, rooms, zones)
