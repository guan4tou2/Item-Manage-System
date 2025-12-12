from typing import Dict, Any, Iterable

from app import mongo


def list_locations() -> Iterable[Dict[str, Any]]:
    return mongo.db.locations.find({}, {"floor": 1, "room": 1, "zone": 1, "order": 1}).sort("order", 1)


def insert_location(doc: Dict[str, Any]) -> None:
    mongo.db.locations.insert_one(doc)


def delete_location(loc_id) -> None:
    mongo.db.locations.delete_one({"_id": loc_id})


def update_location(loc_id, doc: Dict[str, Any]) -> None:
    mongo.db.locations.update_one({"_id": loc_id}, {"$set": doc})


def update_order(loc_id, order: int) -> None:
    mongo.db.locations.update_one({"_id": loc_id}, {"$set": {"order": order}})

