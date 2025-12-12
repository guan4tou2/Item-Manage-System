from typing import Dict, Any, List, Optional, Tuple
from datetime import date

from app.repositories import item_repo, type_repo
from app.utils import storage, image
from app.validators import items as item_validator

ITEM_PROJECTION = {
    "_id": 0,
    "ItemName": 1,
    "ItemID": 1,
    "ItemDesc": 1,
    "ItemPic": 1,
    "ItemStorePlace": 1,
    "ItemType": 1,
    "ItemOwner": 1,
    "ItemGetDate": 1,
    "ItemFloor": 1,
    "ItemRoom": 1,
    "ItemZone": 1,
    "WarrantyExpiry": 1,
    "UsageExpiry": 1,
}


def _filter_valid_types() -> List[str]:
    return [t.get("name") for t in type_repo.list_types()]


def build_search_filter(
    name: str = "",
    place: str = "",
    item_type: str = "",
    floor: str = "",
    room: str = "",
    zone: str = "",
) -> Dict[str, Any]:
    search_filter: Dict[str, Any] = {}
    if name:
        search_filter["ItemName"] = {"$regex": name, "$options": "i"}
    if place:
        search_filter["ItemStorePlace"] = {"$regex": place, "$options": "i"}
    if item_type:
        search_filter["ItemType"] = item_type
    if floor:
        search_filter["ItemFloor"] = floor
    if room:
        search_filter["ItemRoom"] = room
    if zone:
        search_filter["ItemZone"] = zone
    return search_filter


DEFAULT_PAGE_SIZE = 12


def list_items(
    filters: Dict[str, str],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    查詢物品列表，支援分頁
    
    回傳格式:
    {
        "items": [...],
        "total": 總數量,
        "page": 當前頁碼,
        "page_size": 每頁數量,
        "total_pages": 總頁數,
        "has_prev": 是否有上一頁,
        "has_next": 是否有下一頁,
    }
    """
    search_filter = build_search_filter(
        name=filters.get("q", ""),
        place=filters.get("place", ""),
        item_type=filters.get("type", ""),
        floor=filters.get("floor", ""),
        room=filters.get("room", ""),
        zone=filters.get("zone", ""),
    )
    projection = ITEM_PROJECTION.copy()
    sort = None
    sort_param = filters.get("sort")
    if sort_param == "warranty":
        sort = [("WarrantyExpiry", 1)]
    elif sort_param == "usage":
        sort = [("UsageExpiry", 1)]
    elif sort_param == "name":
        sort = [("ItemName", 1)]
    
    # 計算總數和分頁
    total = item_repo.count_items(search_filter)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    items = list(item_repo.list_items(
        search_filter, projection, sort=sort, skip=skip, limit=page_size
    ))
    _annotate_expiry(items)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def create_item(form_data: Dict[str, Any], file_storage) -> Tuple[bool, str]:
    valid_types = _filter_valid_types()
    from app.services import location_service

    floors, rooms, zones = location_service.list_choices()
    ok, msg = item_validator.validate_item_fields(
        form_data,
        valid_types=valid_types,
        valid_floors=floors,
        valid_rooms=rooms,
        valid_zones=zones,
    )
    if not ok:
        return False, msg

    filename = storage.save_upload(file_storage) if file_storage else None
    if filename:
        thumb = image.create_thumbnail(filename)
        form_data["ItemPic"] = filename
        if thumb:
            form_data["ItemThumb"] = thumb
    else:
        form_data["ItemPic"] = ""

    item_repo.insert_item(form_data)
    return True, "物品新增成功"


def update_item_place(item_id: str, updates: Dict[str, Any]) -> None:
    item_repo.update_item_by_id(item_id, updates)


def update_item(item_id: str, form_data: Dict[str, Any], file_storage=None) -> Tuple[bool, str]:
    """更新物品完整資訊"""
    # 檢查物品是否存在
    existing = item_repo.find_item_by_id(item_id)
    if not existing:
        return False, "找不到該物品"
    
    valid_types = _filter_valid_types()
    from app.services import location_service
    floors, rooms, zones = location_service.list_choices()
    
    ok, msg = item_validator.validate_item_fields(
        form_data,
        valid_types=valid_types,
        valid_floors=floors,
        valid_rooms=rooms,
        valid_zones=zones,
    )
    if not ok:
        return False, msg
    
    # 處理圖片上傳
    if file_storage and file_storage.filename:
        filename = storage.save_upload(file_storage)
        if filename:
            thumb = image.create_thumbnail(filename)
            form_data["ItemPic"] = filename
            if thumb:
                form_data["ItemThumb"] = thumb
    
    # 移除不應該更新的欄位
    form_data.pop("csrf_token", None)
    form_data.pop("ItemID", None)  # ItemID 不可更改
    
    item_repo.update_item_by_id(item_id, form_data)
    return True, "物品更新成功"


def delete_item(item_id: str) -> Tuple[bool, str]:
    """刪除物品"""
    existing = item_repo.find_item_by_id(item_id)
    if not existing:
        return False, "找不到該物品"
    
    if item_repo.delete_item_by_id(item_id):
        return True, "物品已刪除"
    return False, "刪除失敗"


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    item = item_repo.find_item_by_id(item_id, ITEM_PROJECTION)
    if item:
        _annotate_expiry([item])
    return item


def _annotate_expiry(items: List[Dict[str, Any]]) -> None:
    today = date.today()
    for it in items:
        for field, key in [("WarrantyExpiry", "WarrantyStatus"), ("UsageExpiry", "UsageStatus")]:
            status = "none"
            val = it.get(field)
            if val:
                try:
                    y, m, d = map(int, val.split("-"))
                    dt = date(y, m, d)
                    if dt < today:
                        status = "expired"
                    elif (dt - today).days <= 30:
                        status = "near"
                    else:
                        status = "ok"
                except Exception:
                    status = "invalid"
            it[key] = status

