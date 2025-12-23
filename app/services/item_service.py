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
    "ItemThumb": 1,  # 縮圖
    "ItemPics": 1,  # 多圖支援
    "ItemStorePlace": 1,
    "ItemType": 1,
    "ItemOwner": 1,
    "ItemGetDate": 1,
    "ItemFloor": 1,
    "ItemRoom": 1,
    "ItemZone": 1,
    "WarrantyExpiry": 1,
    "UsageExpiry": 1,
    "move_history": 1,  # 移動歷史
    "favorites": 1,  # 收藏使用者列表
    "related_items": 1,  # 關聯物品
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
    """更新物品位置，並記錄移動歷史"""
    # 取得現有位置
    existing = item_repo.find_item_by_id(item_id)
    if existing:
        old_location = existing.get("ItemStorePlace", "")
        new_location = updates.get("ItemStorePlace", "")
        
        # 如果位置有變更，記錄移動歷史
        if new_location and old_location != new_location:
            item_repo.add_move_history(item_id, old_location, new_location)
    
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
            # 刪除舊圖片與縮圖
            if existing.get("ItemPic"):
                storage.delete_file(existing["ItemPic"])
            if existing.get("ItemThumb"):
                storage.delete_file(existing["ItemThumb"])
                
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
    
    # 刪除圖片檔案
    if existing.get("ItemPic"):
        storage.delete_file(existing["ItemPic"])
    if existing.get("ItemThumb"):
        storage.delete_file(existing["ItemThumb"])
    
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


def get_expiring_items(days_threshold: int = 30) -> Dict[str, Any]:
    """
    取得即將到期和已過期的物品
    
    回傳格式:
    {
        "expired": [...],       # 已過期物品
        "near_expiry": [...],   # 即將到期物品（30天內）
        "expired_count": 數量,
        "near_count": 數量,
        "total_alerts": 總警報數量,
    }
    """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # 計算 N 天後的日期
    from datetime import timedelta
    threshold_date = today + timedelta(days=days_threshold)
    threshold_str = threshold_date.strftime("%Y-%m-%d")
    
    projection = ITEM_PROJECTION.copy()
    
    # 查詢所有有設定到期日的物品
    all_items = list(item_repo.list_items({}, projection))
    _annotate_expiry(all_items)
    
    expired_items = []
    near_expiry_items = []
    
    for item in all_items:
        warranty_status = item.get("WarrantyStatus", "none")
        usage_status = item.get("UsageStatus", "none")
        
        # 標記到期類型
        item["expiry_types"] = []
        
        if warranty_status == "expired":
            item["expiry_types"].append("warranty_expired")
        elif warranty_status == "near":
            item["expiry_types"].append("warranty_near")
            
        if usage_status == "expired":
            item["expiry_types"].append("usage_expired")
        elif usage_status == "near":
            item["expiry_types"].append("usage_near")
        
        # 分類
        if warranty_status == "expired" or usage_status == "expired":
            expired_items.append(item)
        elif warranty_status == "near" or usage_status == "near":
            near_expiry_items.append(item)
    
    # 按到期日期排序
    def get_earliest_expiry(item):
        dates = []
        for field in ["WarrantyExpiry", "UsageExpiry"]:
            val = item.get(field)
            if val:
                try:
                    dates.append(val)
                except:
                    pass
        return min(dates) if dates else "9999-12-31"
    
    expired_items.sort(key=get_earliest_expiry)
    near_expiry_items.sort(key=get_earliest_expiry)
    
    return {
        "expired": expired_items,
        "near_expiry": near_expiry_items,
        "expired_count": len(expired_items),
        "near_count": len(near_expiry_items),
        "total_alerts": len(expired_items) + len(near_expiry_items),
    }


def get_notification_count() -> Dict[str, int]:
    """
    快速取得通知數量（用於導航欄顯示）
    """
    result = get_expiring_items()
    return {
        "expired": result["expired_count"],
        "near": result["near_count"],
        "total": result["total_alerts"],
    }


def get_stats() -> Dict[str, int]:
    """取得物品統計資訊"""
    return item_repo.get_stats()


def get_all_items_for_export() -> List[Dict[str, Any]]:
    """取得所有物品用於匯出"""
    return item_repo.get_all_items_for_export()


def import_items(items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """匯入物品
    
    回傳 (成功數, 失敗數)
    """
    success = 0
    failed = 0
    
    for item_data in items:
        try:
            # 確保有必要欄位
            if not item_data.get("ItemID") or not item_data.get("ItemName"):
                failed += 1
                continue
            
            # 檢查是否已存在
            existing = item_repo.find_item_by_id(item_data["ItemID"])
            if existing:
                # 更新現有物品
                item_repo.update_item_by_id(item_data["ItemID"], item_data)
            else:
                # 新增物品
                item_repo.insert_item(item_data)
            success += 1
        except Exception:
            failed += 1
    
    return success, failed


def count_by_type(item_type: str) -> int:
    """依類型計算物品數量"""
    return item_repo.count_items({"ItemType": item_type})


def count_by_floor(floor: str) -> int:
    """依樓層計算物品數量"""
    return item_repo.count_items({"ItemFloor": floor})


def toggle_favorite(item_id: str, user_id: str) -> Tuple[bool, bool]:
    """切換收藏狀態
    
    回傳 (成功與否, 新的收藏狀態)
    """
    item = item_repo.find_item_by_id(item_id)
    if not item:
        return False, False
    
    is_now_favorite = item_repo.toggle_favorite(item_id, user_id)
    return True, is_now_favorite


def get_favorites(user_id: str) -> List[Dict[str, Any]]:
    """取得使用者收藏的物品"""
    items = item_repo.get_favorites(user_id, ITEM_PROJECTION)
    _annotate_expiry(items)
    return items


def is_favorite(item_id: str, user_id: str) -> bool:
    """檢查物品是否被使用者收藏"""
    return item_repo.is_favorite(item_id, user_id)


def add_related_item(item_id: str, related_id: str, relation_type: str = "配件") -> Tuple[bool, str]:
    """新增物品關聯
    
    relation_type: 配件、組合、替代品等
    """
    item = item_repo.find_item_by_id(item_id)
    related = item_repo.find_item_by_id(related_id)
    
    if not item or not related:
        return False, "找不到物品"
    
    if item_id == related_id:
        return False, "不可關聯自己"
    
    # 新增關聯（雙向）
    item_repo.add_related_item(item_id, related_id, relation_type)
    item_repo.add_related_item(related_id, item_id, relation_type)
    
    return True, "已新增關聯"


def remove_related_item(item_id: str, related_id: str) -> Tuple[bool, str]:
    """移除物品關聯"""
    item_repo.remove_related_item(item_id, related_id)
    item_repo.remove_related_item(related_id, item_id)
    return True, "已移除關聯"


def get_related_items(item_id: str) -> List[Dict[str, Any]]:
    """取得物品的關聯物品"""
    item = item_repo.find_item_by_id(item_id)
    if not item:
        return []
    
    related_ids = item.get("related_items", [])
    related_items = []
    
    for relation in related_ids:
        rid = relation.get("id") if isinstance(relation, dict) else relation
        rtype = relation.get("type", "配件") if isinstance(relation, dict) else "配件"
        
        related = item_repo.find_item_by_id(rid, ITEM_PROJECTION)
        if related:
            related["relation_type"] = rtype
            related_items.append(related)
    
    return related_items


def bulk_delete_items(item_ids: List[str]) -> Tuple[int, List[str]]:
    """批量刪除物品
    
    Returns:
        (成功的數量, 失敗的 ID 列表)
    """
    success_count = 0
    failed_ids = []
    
    for item_id in item_ids:
        # 這裡的 delete_item 已經包含了刪除檔案的邏輯
        success, _ = delete_item(item_id)
        if success:
            success_count += 1
        else:
            failed_ids.append(item_id)
            
    return success_count, failed_ids


def bulk_move_items(item_ids: List[str], target_location: str) -> Tuple[int, List[str]]:
    """批量移動物品
    
    Returns:
        (成功的數量, 失敗的 ID 列表)
    """
    success_count = 0
    failed_ids = []
    
    # 避免在此處引用 log_service 造成循環引用 (如果 routes 也引用了 item_service)
    # 但為了完整性，我們先確保可以運行 (通常 service 層互相引用要小心)
    from app.services import log_service
    
    for item_id in item_ids:
        # 重用 update_item 邏輯，或者直接調用 quick_update_location (如果有的話)
        # 這裡簡單調用 repo 更新，因為 update_item 比較重
        # 但為了保持一致性，我們還是模擬 update_item 的一部分邏輯 (如記錄歷史)
        
        # 取得舊資料
        old_item = item_repo.find_item_by_id(item_id)
        if not old_item:
            failed_ids.append(item_id)
            continue
            
        old_loc = old_item.get("ItemStorePlace", "")
        
        # 如果位置沒變，直接算成功
        if old_loc == target_location:
            success_count += 1
            continue
            
        # 更新位置
        success = item_repo.update_item_field(item_id, "ItemStorePlace", target_location)
        if success:
            success_count += 1
            # 記錄移動日誌
            item_repo.add_move_history(item_id, old_loc, target_location)
            # 記錄操作日誌
            log_service.log_move(item_id, old_item.get("ItemName", ""), old_loc, target_location)
        else:
            failed_ids.append(item_id)
            
    return success_count, failed_ids

