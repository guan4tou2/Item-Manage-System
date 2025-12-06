from datetime import datetime
from typing import Dict, Tuple, Optional, Iterable, Set


def _validate_date(date_str: str, label: str) -> Tuple[bool, str]:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, f"{label} 格式應為 YYYY-MM-DD"
    return True, ""


def validate_item_fields(
    data: Dict[str, str],
    valid_types: Optional[Iterable[str]] = None,
    valid_floors: Optional[Iterable[str]] = None,
    valid_rooms: Optional[Iterable[str]] = None,
    valid_zones: Optional[Iterable[str]] = None,
) -> Tuple[bool, str]:
    required = ["ItemName", "ItemID", "ItemStorePlace", "ItemType", "ItemOwner", "ItemGetDate"]
    for field in required:
        if not data.get(field):
            return False, f"{field} 為必填欄位"

    if valid_types is not None and data.get("ItemType"):
        if data.get("ItemType") not in valid_types:
            return False, "物品類型不存在"

    if valid_floors is not None and data.get("ItemFloor"):
        if data["ItemFloor"] not in valid_floors:
            return False, "樓層選項不存在"
    if valid_rooms is not None and data.get("ItemRoom"):
        if data["ItemRoom"] not in valid_rooms:
            return False, "房間選項不存在"
    if valid_zones is not None and data.get("ItemZone"):
        if data["ItemZone"] not in valid_zones:
            return False, "區域選項不存在"

    if data.get("ItemGetDate"):
        ok, msg = _validate_date(data["ItemGetDate"], "取得日期")
        if not ok:
            return ok, msg

    for date_field, label in [("WarrantyExpiry", "保固期限"), ("UsageExpiry", "使用期限")]:
        if data.get(date_field):
            ok, msg = _validate_date(data[date_field], label)
            if not ok:
                return ok, msg

    return True, ""

