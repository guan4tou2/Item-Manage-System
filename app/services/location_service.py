from typing import List, Dict, Any, Tuple

from app.repositories import location_repo
from bson import ObjectId


def list_locations() -> List[Dict[str, Any]]:
    locs = []
    for l in location_repo.list_locations():
        l["_id"] = str(l["_id"])
        locs.append(l)
    return locs


def list_choices() -> Tuple[List[str], List[str], List[str]]:
    locs = list_locations()
    floors = sorted({l.get("floor", "") for l in locs if l.get("floor")})
    rooms = sorted({l.get("room", "") for l in locs if l.get("room")})
    zones = sorted({l.get("zone", "") for l in locs if l.get("zone")})
    return floors, rooms, zones


def create_location(doc: Dict[str, Any]) -> None:
    # simple dedup check
    location_repo.insert_location(doc)


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

