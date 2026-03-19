"""自訂欄位服務模組"""
from typing import Any, Dict, List, Optional, Tuple

from app.repositories import custom_field_repo


def list_fields() -> List[Dict[str, Any]]:
    """取得所有自訂欄位"""
    return custom_field_repo.list_fields()


def create_field(
    name: str,
    field_type: str,
    options: Optional[str] = None,
    required: bool = False,
    sort_order: int = 0,
    created_by: str = "",
) -> Tuple[bool, str, Any]:
    """新增自訂欄位，回傳 (success, message, field_id)"""
    name = name.strip() if name else ""
    if not name:
        return False, "欄位名稱不可為空", None
    valid_types = {"text", "number", "date", "select", "boolean"}
    if field_type not in valid_types:
        return False, f"不支援的欄位類型：{field_type}", None
    if field_type == "select" and not (options and options.strip()):
        return False, "選擇類型必須提供選項", None
    try:
        field_id = custom_field_repo.create_field(
            name=name,
            field_type=field_type,
            options=options,
            required=bool(required),
            sort_order=int(sort_order),
            created_by=created_by,
        )
        return True, "欄位已建立", field_id
    except Exception as e:
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            return False, f"欄位名稱「{name}」已存在", None
        return False, f"建立失敗：{err}", None


def update_field(field_id, data: Dict[str, Any]) -> Tuple[bool, str]:
    """更新自訂欄位"""
    if "name" in data:
        data["name"] = data["name"].strip()
        if not data["name"]:
            return False, "欄位名稱不可為空"
    if "required" in data:
        data["required"] = bool(data["required"])
    if "sort_order" in data:
        try:
            data["sort_order"] = int(data["sort_order"])
        except (ValueError, TypeError):
            data["sort_order"] = 0
    try:
        success = custom_field_repo.update_field(field_id, data)
        if success:
            return True, "欄位已更新"
        return False, "找不到欄位"
    except Exception as e:
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            return False, f"欄位名稱「{data.get('name', '')}」已存在"
        return False, f"更新失敗：{err}"


def delete_field(field_id) -> Tuple[bool, str]:
    """刪除自訂欄位"""
    success = custom_field_repo.delete_field(field_id)
    if success:
        return True, "欄位已刪除"
    return False, "找不到欄位"


def get_item_custom_values(item_id: str) -> List[Dict[str, Any]]:
    """取得物品的自訂欄位值清單，格式：{field_name, field_type, value, ...}"""
    return custom_field_repo.get_values(item_id)


def save_item_custom_values(item_id: str, form_data: Dict[str, Any]) -> None:
    """從表單資料解析並儲存自訂欄位值"""
    # form keys are like: custom_field_<field_id>
    values_dict: Dict[str, str] = {}
    for key, val in form_data.items():
        if key.startswith("custom_field_"):
            field_id_str = key[len("custom_field_"):]
            if field_id_str.isdigit():
                values_dict[field_id_str] = str(val) if val is not None else ""
    if values_dict:
        custom_field_repo.set_values(item_id, values_dict)
