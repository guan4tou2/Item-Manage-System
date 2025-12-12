from typing import List, Dict, Any, Tuple, Optional

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

