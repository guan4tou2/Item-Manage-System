from typing import Dict, Any, Iterable

from app import mongo


def list_types() -> Iterable[Dict[str, Any]]:
    return mongo.db.type.find({}, {"_id": 0, "name": 1})


def insert_type(type_data: Dict[str, Any]) -> None:
    mongo.db.type.insert_one(type_data)

