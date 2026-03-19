from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.repositories import item_repo, type_repo
from app.repositories import quantity_log_repo
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
    "visibility": 1,
    "shared_with": 1,
    "WarrantyExpiry": 1,
    "UsageExpiry": 1,
    "MaintenanceCategory": 1,
    "MaintenanceIntervalDays": 1,
    "LastMaintenanceDate": 1,
    "move_history": 1,  # 移動歷史
    "favorites": 1,  # 收藏使用者列表
    "related_items": 1,  # 關聯物品
    "size_notes": 1,
    "condition": 1,
    "purchase_price": 1,
    "current_value": 1,
    "depreciation_method": 1,
    "depreciation_rate": 1,
}


def get_maintenance_suggestion(item_name: str = "", item_type: str = "") -> Optional[Dict[str, Any]]:
    searchable_text = f"{(item_name or '').strip()} {(item_type or '').strip()}"
    for rule in DEFAULT_KEYWORD_REPLACEMENT_RULES:
        if any(keyword in searchable_text for keyword in rule["keywords"]):
            return {
                "category": str(rule["rule_name"]),
                "interval_days": int(rule["days"]),
                "source": "suggested",
            }
    return None


def _extract_maintenance(item: Dict[str, Any]) -> Dict[str, Any]:
    interval_raw = item.get("MaintenanceIntervalDays")
    interval_days = None
    if interval_raw not in ("", None):
        try:
            interval_days = int(interval_raw)
        except (TypeError, ValueError):
            interval_days = None
    last_date = str(item.get("LastMaintenanceDate") or "").strip()
    category = str(item.get("MaintenanceCategory") or "").strip()
    if category or interval_days or last_date:
        return {
            "category": category,
            "interval_days": interval_days,
            "last_date": last_date,
            "source": "manual",
        }

    size_notes = item.get("size_notes")
    if not isinstance(size_notes, dict):
        return {}
    maintenance = size_notes.get("maintenance")
    if not isinstance(maintenance, dict):
        return {}
    interval_raw = maintenance.get("interval_days")
    interval_days = None
    if interval_raw not in ("", None):
        try:
            interval_days = int(interval_raw)
        except (TypeError, ValueError):
            interval_days = None
    return {
        "category": str(maintenance.get("category") or "").strip(),
        "interval_days": interval_days,
        "last_date": str(maintenance.get("last_date") or "").strip(),
        "source": str(maintenance.get("source") or "manual").strip() or "manual",
    }


def _annotate_maintenance_fields(items: List[Dict[str, Any]]) -> None:
    for item in items:
        maintenance = _extract_maintenance(item)
        suggestion = get_maintenance_suggestion(item.get("ItemName", ""), item.get("ItemType", ""))
        item["MaintenanceCategory"] = maintenance.get("category", "")
        interval_days = maintenance.get("interval_days")
        item["MaintenanceIntervalDays"] = "" if interval_days in (None, "") else str(interval_days)
        item["LastMaintenanceDate"] = maintenance.get("last_date", "")
        item["MaintenanceSuggestionCategory"] = suggestion.get("category", "") if suggestion else ""
        item["MaintenanceSuggestionDays"] = suggestion.get("interval_days", "") if suggestion else ""


def _apply_maintenance_form_data(form_data: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> None:
    category = str(form_data.pop("MaintenanceCategory", "") or "").strip()
    interval_raw = str(form_data.pop("MaintenanceIntervalDays", "") or "").strip()
    last_date = str(form_data.pop("LastMaintenanceDate", "") or "").strip()

    if not category and not interval_raw and not last_date:
        form_data["MaintenanceCategory"] = ""
        form_data["MaintenanceIntervalDays"] = None
        form_data["LastMaintenanceDate"] = None
        return

    interval_days = int(interval_raw) if interval_raw else None
    form_data["MaintenanceCategory"] = category or "自訂保養"
    form_data["MaintenanceIntervalDays"] = interval_days
    form_data["LastMaintenanceDate"] = last_date or None


def _filter_valid_types() -> List[str]:
    return [t.get("name") or "" for t in type_repo.list_types() if t.get("name")]


def build_search_filter(
    name: str = "",
    place: str = "",
    item_type: str = "",
    floor: str = "",
    room: str = "",
    zone: str = "",
    visibility: str = "",
    condition: str = "",
) -> Dict[str, Any]:
    from app import get_db_type

    search_filter: Dict[str, Any] = {}
    db_type = get_db_type()
    if name:
        if db_type == "mongo":
            search_filter["ItemName"] = {"$regex": name, "$options": "i"}
        else:
            search_filter["ItemName"] = name
    if place:
        if db_type == "mongo":
            search_filter["ItemStorePlace"] = {"$regex": place, "$options": "i"}
        else:
            search_filter["ItemStorePlace"] = place
    if item_type:
        search_filter["ItemType"] = item_type
    if floor:
        search_filter["ItemFloor"] = floor
    if room:
        search_filter["ItemRoom"] = room
    if zone:
        search_filter["ItemZone"] = zone
    if visibility:
        search_filter["visibility"] = visibility
    if condition:
        search_filter["condition"] = condition
    return search_filter


DEFAULT_PAGE_SIZE = 12


def paginate_items(items: List[Dict[str, Any]], page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> Dict[str, Any]:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    paginated = items[start:end]
    return {
        "items": paginated,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def filter_items_by_maintenance(items: List[Dict[str, Any]], maintenance_filter: str) -> List[Dict[str, Any]]:
    if maintenance_filter == "due":
        return [item for item in items if item.get("MaintenanceAlertStatus") == "due"]
    if maintenance_filter == "upcoming":
        return [item for item in items if item.get("MaintenanceAlertStatus") == "upcoming"]
    if maintenance_filter == "all":
        return [item for item in items if item.get("MaintenanceAlertStatus") in {"due", "upcoming"}]
    return items


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
        visibility=filters.get("visibility", ""),
        condition=filters.get("condition", ""),
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
    _annotate_maintenance_fields(items)
    
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

    form_data["visibility"] = (form_data.get("visibility") or "private").strip().lower()
    _apply_maintenance_form_data(form_data)

    filename = storage.save_upload(file_storage) if file_storage else None
    if filename:
        compressed = image.compress_image(filename)
        if compressed:
            filename = compressed
        thumb = image.create_thumbnail(filename)
        form_data["ItemPic"] = filename
        if thumb:
            form_data["ItemThumb"] = thumb
    else:
        form_data["ItemPic"] = ""

    item_repo.insert_item(form_data)

    try:
        from app.services import webhook_service
        webhook_service.fire_event("item.created", {
            "item_id": form_data.get("ItemID", ""),
            "item_name": form_data.get("ItemName", ""),
        })
    except Exception:
        pass

    return True, "物品新增成功"


def update_item_place(item_id: str, updates: Dict[str, Any]) -> None:
    """更新物品位置，並記錄移動歷史"""
    # 取得現有位置
    existing = item_repo.find_item_by_id(item_id)
    if existing:
        floor = (updates.get("ItemFloor", existing.get("ItemFloor", "")) or "").strip()
        room = (updates.get("ItemRoom", existing.get("ItemRoom", "")) or "").strip()
        zone = (updates.get("ItemZone", existing.get("ItemZone", "")) or "").strip()
        derived_place = "/".join(part for part in [floor, room, zone] if part)
        if derived_place and not (updates.get("ItemStorePlace") or "").strip():
            updates["ItemStorePlace"] = derived_place

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

    form_data["visibility"] = (form_data.get("visibility") or existing.get("visibility") or "private").strip().lower()
    _apply_maintenance_form_data(form_data, existing=existing)
    
    # 處理圖片上傳
    if file_storage and file_storage.filename:
        filename = storage.save_upload(file_storage)
        if filename:
            # 壓縮圖片
            compressed = image.compress_image(filename)
            if compressed:
                filename = compressed
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

    try:
        from app.services import webhook_service
        webhook_service.fire_event("item.updated", {
            "item_id": item_id,
            "item_name": existing.get("ItemName", ""),
        })
    except Exception:
        pass

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
        try:
            from app.services import webhook_service
            webhook_service.fire_event("item.deleted", {
                "item_id": item_id,
                "item_name": existing.get("ItemName", ""),
            })
        except Exception:
            pass
        return True, "物品已刪除"
    return False, "刪除失敗"


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    item = item_repo.find_item_by_id(item_id, ITEM_PROJECTION)
    if item:
        _annotate_expiry([item])
        _annotate_maintenance_fields([item])
    return item


def _annotate_expiry(items: List[Dict[str, Any]]) -> None:
    today = date.today()
    for it in items:
        for field, key in [("WarrantyExpiry", "WarrantyStatus"), ("UsageExpiry", "UsageStatus")]:
            status = "none"
            val = it.get(field)
            if val:
                try:
                    if isinstance(val, datetime):
                        dt = val.date()
                    elif isinstance(val, date):
                        dt = val
                    elif isinstance(val, str):
                        dt = datetime.strptime(val.strip(), "%Y-%m-%d").date()
                    else:
                        raise ValueError("unsupported expiry type")
                    if dt < today:
                        status = "expired"
                    elif (dt - today).days <= 30:
                        status = "near"
                    else:
                        status = "ok"
                except Exception:
                    status = "invalid"
            it[key] = status


def get_expiring_items(days_threshold: int = 30, ladder: Optional[List[int]] = None) -> Dict[str, Any]:
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
    
    # 保留 ladder 參數以相容通知服務呼叫簽名。
    _ = ladder
    
    # 使用 DB 層級的優化查詢取得到期/即將到期物品
    db_items = item_repo.get_expiring_items(days_threshold)
    _annotate_expiry(db_items)
    all_items = db_items
    
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
    def _normalize_expiry_value(val: Any) -> str:
        if isinstance(val, datetime):
            return val.date().strftime("%Y-%m-%d")
        if isinstance(val, date):
            return val.strftime("%Y-%m-%d")
        if isinstance(val, str):
            txt = val.strip()
            if not txt:
                return "9999-12-31"
            try:
                return datetime.strptime(txt, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                return "9999-12-31"
        return "9999-12-31"

    def get_earliest_expiry(item):
        dates = []
        for field in ["WarrantyExpiry", "UsageExpiry"]:
            val = item.get(field)
            normalized = _normalize_expiry_value(val)
            if normalized != "9999-12-31":
                dates.append(normalized)
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


DEFAULT_REPLACEMENT_RULES = {
    "內衣": 90,
    "襪子": 180,
}

DEFAULT_KEYWORD_REPLACEMENT_RULES = [
    {"rule_name": "3C 電池補電", "days": 60, "keywords": ["行動電源", "備用相機電池", "相機電池", "備用手機", "備用平板", "鋰電"]},
    {"rule_name": "冷氣濾網保養", "days": 90, "keywords": ["冷氣濾網", "空調濾網"]},
    {"rule_name": "除濕機濾網保養", "days": 90, "keywords": ["除濕機濾網"]},
    {"rule_name": "掃地機濾網保養", "days": 90, "keywords": ["掃地機濾網", "掃地機集塵盒"]},
    {"rule_name": "空氣清淨機濾網保養", "days": 180, "keywords": ["空氣清淨機濾網", "清淨機濾網"]},
    {"rule_name": "飲水機濾芯更換", "days": 180, "keywords": ["飲水機濾芯", "濾水壺濾芯", "淨水器濾芯"]},
]


def _parse_replacement_rules(raw_rules: Any) -> Dict[str, int]:
    parsed: Dict[str, int] = {}
    if isinstance(raw_rules, list):
        for rule in raw_rules:
            if isinstance(rule, str) and "=" in rule:
                name, days = rule.split("=", 1)
                name = name.strip()
                days = days.strip()
                if name and days.isdigit():
                    parsed[name] = int(days)
            elif isinstance(rule, dict):
                name = str(rule.get("name", "")).strip()
                days = rule.get("days")
                if name and isinstance(days, int) and days > 0:
                    parsed[name] = days
    return {**DEFAULT_REPLACEMENT_RULES, **parsed}


def _match_default_keyword_rule(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    suggestion = get_maintenance_suggestion(item.get("ItemName", ""), item.get("ItemType", ""))
    if not suggestion:
        return None
    return {
        "rule_name": suggestion["category"],
        "days": suggestion["interval_days"],
    }


def get_replacement_items(settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = settings or {}
    enabled = bool(settings.get("replacement_enabled", True))
    if not enabled:
        return {
            "enabled": False,
            "due": [],
            "upcoming": [],
            "total_alerts": 0,
        }

    rules = _parse_replacement_rules(settings.get("replacement_intervals"))
    projection = {
        "_id": 0,
        "ItemID": 1,
        "ItemName": 1,
        "ItemType": 1,
        "ItemGetDate": 1,
        "size_notes": 1,
        "MaintenanceCategory": 1,
        "MaintenanceIntervalDays": 1,
        "LastMaintenanceDate": 1,
    }
    all_items = list(item_repo.list_items({}, projection))
    today = date.today()
    upcoming_window_days = 14
    due_items: List[Dict[str, Any]] = []
    upcoming_items: List[Dict[str, Any]] = []

    for item in all_items:
        name = str(item.get("ItemName") or "").strip()
        if not name:
            continue
        got_date_raw = item.get("ItemGetDate")
        if not isinstance(got_date_raw, str) or not got_date_raw:
            continue
        try:
            got_date = datetime.strptime(got_date_raw, "%Y-%m-%d").date()
        except ValueError:
            continue

        matched_rule_name = name
        base_date = got_date
        explicit_maintenance = _extract_maintenance(item)
        interval_days = explicit_maintenance.get("interval_days")
        if interval_days:
            matched_rule_name = explicit_maintenance.get("category") or "自訂保養"
            last_date_raw = explicit_maintenance.get("last_date")
            if last_date_raw:
                try:
                    base_date = datetime.strptime(last_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    base_date = got_date
        else:
            interval_days = rules.get(name)
        if interval_days is None:
            default_rule = _match_default_keyword_rule(item)
            if not default_rule:
                continue
            interval_days = int(default_rule["days"])
            matched_rule_name = str(default_rule["rule_name"])

        due_date = base_date.fromordinal(base_date.toordinal() + int(interval_days))
        days_left = (due_date - today).days
        enriched = dict(item)
        enriched["replacement_rule_name"] = matched_rule_name
        enriched["replacement_days"] = int(interval_days)
        enriched["replacement_due_date"] = due_date.strftime("%Y-%m-%d")

        if days_left <= 0:
            enriched["days_overdue"] = abs(days_left)
            due_items.append(enriched)
        elif days_left <= upcoming_window_days:
            enriched["days_left"] = days_left
            upcoming_items.append(enriched)

    due_items.sort(key=lambda x: x.get("replacement_due_date", "9999-12-31"))
    upcoming_items.sort(key=lambda x: x.get("replacement_due_date", "9999-12-31"))

    return {
        "enabled": True,
        "due": due_items,
        "upcoming": upcoming_items,
        "total_alerts": len(due_items) + len(upcoming_items),
    }


def annotate_maintenance_alerts(items: List[Dict[str, Any]], settings: Optional[Dict[str, Any]] = None) -> None:
    settings = settings or {}
    if not settings.get("replacement_enabled", True):
        return

    rules = _parse_replacement_rules(settings.get("replacement_intervals"))
    today = date.today()
    upcoming_window_days = 14

    for item in items:
        item["MaintenanceAlertStatus"] = ""
        item["MaintenanceAlertLabel"] = ""
        item["NextMaintenanceDate"] = ""

        name = str(item.get("ItemName") or "").strip()
        got_date_raw = item.get("ItemGetDate")
        if not name or not isinstance(got_date_raw, str) or not got_date_raw:
            continue

        try:
            got_date = datetime.strptime(got_date_raw, "%Y-%m-%d").date()
        except ValueError:
            continue

        base_date = got_date
        explicit_maintenance = _extract_maintenance(item)
        interval_days = explicit_maintenance.get("interval_days")
        rule_name = explicit_maintenance.get("category") or name
        if interval_days:
            last_date_raw = explicit_maintenance.get("last_date")
            if last_date_raw:
                try:
                    base_date = datetime.strptime(last_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    base_date = got_date
        else:
            interval_days = rules.get(name)
            if interval_days is None:
                default_rule = _match_default_keyword_rule(item)
                if not default_rule:
                    continue
                interval_days = int(default_rule["days"])
                rule_name = str(default_rule["rule_name"])
            else:
                rule_name = name

        due_date = base_date.fromordinal(base_date.toordinal() + int(interval_days))
        days_left = (due_date - today).days
        item["NextMaintenanceDate"] = due_date.strftime("%Y-%m-%d")
        item["MaintenanceRuleName"] = rule_name

        if days_left <= 0:
            item["MaintenanceAlertStatus"] = "due"
            item["MaintenanceAlertLabel"] = "需保養"
            item["MaintenanceDaysOverdue"] = abs(days_left)
        elif days_left <= upcoming_window_days:
            item["MaintenanceAlertStatus"] = "upcoming"
            item["MaintenanceAlertLabel"] = "即將保養"
            item["MaintenanceDaysLeft"] = days_left


def get_notification_count() -> Dict[str, int]:
    """
    快速取得通知數量（用於導航欄顯示）
    """
    try:
        result = get_expiring_items()
    except Exception:
        return {"expired": 0, "near": 0, "total": 0}
    return {
        "expired": result["expired_count"],
        "near": result["near_count"],
        "total": result["total_alerts"],
    }


def get_stats() -> Dict[str, int]:
    """取得物品統計資訊"""
    return item_repo.get_stats()


def get_all_items_for_export(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    return item_repo.get_all_items_for_export(filters=filters)


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


def full_text_search(query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Full-text search across ItemName, ItemDesc, ItemStorePlace.

    Delegates to item_repo.full_text_search and annotates expiry/maintenance
    fields on the returned items.

    Returns dict with 'items' list and 'total' count.
    """
    result = item_repo.full_text_search(query, page=page, page_size=page_size)
    _annotate_expiry(result["items"])
    _annotate_maintenance_fields(result["items"])
    return result


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
        
        if not rid:
            continue
        related = item_repo.find_item_by_id(str(rid), ITEM_PROJECTION)
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
            log_service.log_item_move("", item_id, old_item.get("ItemName", ""), old_loc, target_location)
        else:
            failed_ids.append(item_id)
            
    return success_count, failed_ids


def adjust_quantity(item_id: str, delta: int, user: str = "", reason: Optional[str] = None) -> Tuple[bool, int, str]:
    """調整物品數量

    Args:
        item_id: 物品 ID
        delta: 數量變化（正數增加，負數減少）
        user: 操作使用者
        reason: 調整原因（選填）

    Returns:
        (成功與否, 新數量, 訊息)
    """
    item = item_repo.find_item_by_id(item_id)
    if not item:
        return False, 0, "找不到該物品"

    current_qty = item.get("Quantity", 0) or 0
    new_qty = max(0, current_qty + delta)  # 不允許負數庫存

    success = item_repo.update_item_field(item_id, "Quantity", new_qty)
    if success:
        try:
            quantity_log_repo.insert_log(
                item_id=item_id,
                item_name=item.get("ItemName", ""),
                user=user,
                delta=new_qty - current_qty,
                old_qty=current_qty,
                new_qty=new_qty,
                reason=reason,
            )
        except Exception:
            pass
        try:
            from app.services import webhook_service
            webhook_service.fire_event("item.quantity.changed", {
                "item_id": item_id,
                "item_name": item.get("ItemName", ""),
                "old_quantity": current_qty,
                "new_quantity": new_qty,
                "delta": new_qty - current_qty,
            })
        except Exception:
            pass
        return True, new_qty, f"數量已更新為 {new_qty}"
    return False, current_qty, "更新失敗"


def get_low_stock_items() -> Dict[str, Any]:
    """取得低庫存和需補貨的物品
    
    低庫存: Quantity <= SafetyStock 且 SafetyStock > 0
    需補貨: Quantity <= ReorderLevel 且 ReorderLevel > 0
    
    Returns:
        {
            "low_stock": [...],      # 低庫存物品
            "need_reorder": [...],   # 需補貨物品
            "low_stock_count": 數量,
            "reorder_count": 數量,
            "total_alerts": 總警報數量,
        }
    """
    projection = ITEM_PROJECTION.copy()
    projection["Quantity"] = 1
    projection["SafetyStock"] = 1
    projection["ReorderLevel"] = 1
    
    all_items = list(item_repo.list_items({}, projection))
    
    low_stock_items = []
    need_reorder_items = []
    
    for item in all_items:
        qty = item.get("Quantity", 0) or 0
        safety = item.get("SafetyStock", 0) or 0
        reorder = item.get("ReorderLevel", 0) or 0
        
        # 標記庫存狀態
        item["stock_status"] = "ok"
        
        # 低於安全庫存
        if safety > 0 and qty <= safety:
            item["stock_status"] = "low"
            low_stock_items.append(item)
        
        # 低於補貨門檻（更嚴重）
        if reorder > 0 and qty <= reorder:
            item["stock_status"] = "critical"
            if item not in low_stock_items:
                low_stock_items.append(item)
            need_reorder_items.append(item)
    
    # 按數量排序（數量越少越前面）
    low_stock_items.sort(key=lambda x: x.get("Quantity", 0) or 0)
    need_reorder_items.sort(key=lambda x: x.get("Quantity", 0) or 0)
    
    return {
        "low_stock": low_stock_items,
        "need_reorder": need_reorder_items,
        "low_stock_count": len(low_stock_items),
        "reorder_count": len(need_reorder_items),
        "total_alerts": len(low_stock_items) + len(need_reorder_items),
    }


def bulk_update_quantity(updates: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """批量更新物品數量
    
    Args:
        updates: [{"item_id": "xxx", "quantity": 10}, ...]
    
    Returns:
        (成功的數量, 失敗的 ID 列表)
    """
    success_count = 0
    failed_ids = []
    
    for update in updates:
        item_id = update.get("item_id", "")
        quantity = update.get("quantity")
        
        if not item_id or quantity is None:
            continue
        
        try:
            qty = int(str(quantity))
            if qty < 0:
                failed_ids.append(item_id)
                continue
            
            success = item_repo.update_item_field(item_id, "Quantity", qty)
            if success:
                success_count += 1
            else:
                failed_ids.append(item_id)
        except (ValueError, TypeError):
            failed_ids.append(item_id)
    
    return success_count, failed_ids


def calculate_current_value(item: Dict[str, Any]) -> Optional[float]:
    """Calculate current depreciated value of an item.

    Supports two methods:
    - straight_line: purchase_price - (purchase_price * rate/100 * years)
    - declining_balance: purchase_price * (1 - rate/100) ^ years

    Returns the calculated value clamped to 0 minimum, or None if data is missing.
    """
    purchase_price = item.get("purchase_price")
    depreciation_rate = item.get("depreciation_rate")
    depreciation_method = item.get("depreciation_method") or ""
    get_date_raw = item.get("ItemGetDate") or ""

    if purchase_price is None or not depreciation_rate or not depreciation_method or not get_date_raw:
        return None

    try:
        purchase_price = float(purchase_price)
        rate = float(depreciation_rate)
        get_date = datetime.strptime(get_date_raw, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

    today = date.today()
    years = (today - get_date).days / 365.25
    if years < 0:
        years = 0

    if depreciation_method == "straight_line":
        value = purchase_price - (purchase_price * rate / 100 * years)
    elif depreciation_method == "declining_balance":
        value = purchase_price * ((1 - rate / 100) ** years)
    else:
        return None

    return max(0.0, round(value, 2))


def get_asset_report() -> Dict[str, Any]:
    """Return summary asset report for all items with purchase_price set.

    Returns:
        {
            "total_purchase_value": float,
            "total_current_value": float,
            "depreciation_this_year": float,
            "items_with_value": [...],  # sorted by current_value desc
        }
    """
    all_items = item_repo.get_all_items_for_export()
    items_with_value = []
    total_purchase = 0.0
    total_current = 0.0

    for item in all_items:
        price = item.get("purchase_price")
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        calculated = calculate_current_value(item)
        current = calculated if calculated is not None else price
        depreciation_amount = round(price - current, 2)

        enriched = dict(item)
        enriched["purchase_price"] = price
        enriched["calculated_current_value"] = current
        enriched["depreciation_amount"] = depreciation_amount
        items_with_value.append(enriched)
        total_purchase += price
        total_current += current

    items_with_value.sort(key=lambda x: x.get("calculated_current_value", 0), reverse=True)

    # Depreciation this year: approximate as total_purchase * avg_rate / 100
    depreciation_this_year = round(total_purchase - total_current, 2) if items_with_value else 0.0

    return {
        "total_purchase_value": round(total_purchase, 2),
        "total_current_value": round(total_current, 2),
        "depreciation_this_year": depreciation_this_year,
        "items_with_value": items_with_value,
    }


def bulk_update_last_maintenance(item_ids: List[str], maintenance_date: str) -> Tuple[int, List[str]]:
    """批量更新上次保養日"""
    success_count = 0
    failed_ids: List[str] = []

    try:
        datetime.strptime(maintenance_date, "%Y-%m-%d")
    except ValueError:
        return 0, item_ids

    for item_id in item_ids:
        item = item_repo.find_item_by_id(item_id)
        if not item:
            failed_ids.append(item_id)
            continue

        updates: Dict[str, Any] = {"LastMaintenanceDate": maintenance_date}
        if not str(item.get("MaintenanceCategory") or "").strip():
            suggestion = get_maintenance_suggestion(item.get("ItemName", ""), item.get("ItemType", ""))
            if suggestion:
                updates["MaintenanceCategory"] = suggestion["category"]
                updates["MaintenanceIntervalDays"] = suggestion["interval_days"]

        item_repo.update_item_by_id(item_id, updates)
        success_count += 1

    return success_count, failed_ids



def get_all_move_history(
    page: int = 1,
    page_size: int = 50,
    item_filter: str = "",
    location_filter: str = "",
    date_from: str = "",
    date_to: str = "",
) -> Dict[str, Any]:
    """取得所有物品的移動歷史，扁平化排序後分頁回傳。

    Returns:
        {
            "items": [{"item_id", "item_name", "date", "from_location", "to_location"}, ...],
            "total": N,
            "page": P,
            "page_size": PS,
            "total_pages": T,
        }
    """
    from app import get_db_type

    db_type = get_db_type()
    records: List[Dict[str, Any]] = []

    if db_type == "postgres":
        from app.models.item import Item as ItemModel
        from sqlalchemy import cast, String

        # Fetch only items that have a non-empty move_history JSON array
        try:
            items_with_history = ItemModel.query.filter(
                ItemModel.move_history.isnot(None),
                cast(ItemModel.move_history, String) != "[]",
                cast(ItemModel.move_history, String) != "null",
            ).all()
        except Exception:
            items_with_history = [
                item for item in ItemModel.query.all()
                if item.move_history
            ]
    else:
        from app import mongo

        docs = list(mongo.db.item.find(
            {"move_history": {"$exists": True, "$not": {"$size": 0}}},
            {"ItemID": 1, "ItemName": 1, "move_history": 1, "_id": 0},
        ))
        items_with_history = docs

    item_filter_lower = item_filter.lower()
    location_filter_lower = location_filter.lower()

    for item in items_with_history:
        if db_type == "postgres":
            item_id = item.ItemID
            item_name = item.ItemName
            history = item.move_history or []
        else:
            item_id = item.get("ItemID", "")
            item_name = item.get("ItemName", "")
            history = item.get("move_history") or []

        if not isinstance(history, list):
            continue

        if item_filter_lower and item_filter_lower not in item_name.lower():
            continue

        for record in history:
            if not isinstance(record, dict):
                continue

            rec_date = str(record.get("date") or "")
            from_loc = str(record.get("from_location") or "")
            to_loc = str(record.get("to_location") or "")

            if location_filter_lower and (
                location_filter_lower not in from_loc.lower()
                and location_filter_lower not in to_loc.lower()
            ):
                continue

            if date_from and rec_date < date_from:
                continue
            if date_to and rec_date[:10] > date_to:
                continue

            records.append({
                "item_id": item_id,
                "item_name": item_name,
                "date": rec_date,
                "from_location": from_loc,
                "to_location": to_loc,
            })

    # Sort by date descending
    records.sort(key=lambda r: r["date"], reverse=True)

    total = len(records)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": records[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def generate_purchase_links(item_name: str) -> List[Dict[str, Any]]:
    """產生主要電商平台的搜尋連結（Feature 21）。"""
    import urllib.parse

    q = urllib.parse.quote(item_name)
    return [
        {"store": "Amazon", "url": f"https://www.amazon.com/s?k={q}", "icon": "fab fa-amazon"},
        {"store": "PChome", "url": f"https://ecshweb.pchome.com.tw/search/v4.3/?q={q}", "icon": "fas fa-shopping-cart"},
        {"store": "Shopee", "url": f"https://shopee.tw/search?keyword={q}", "icon": "fas fa-store"},
        {"store": "Momo", "url": f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={q}", "icon": "fas fa-shopping-bag"},
    ]
