from typing import List, Dict, Any, Optional

from app.repositories import type_repo

DEFAULT_TYPE_NAMES = [
    "文具",
    "工具",
    "電子產品",
    "3C配件",
    "家電",
    "廚房用品",
    "餐具",
    "食品",
    "飲品",
    "藥品",
    "保健食品",
    "清潔用品",
    "衛浴用品",
    "美妝保養",
    "衣物",
    "鞋類",
    "寢具",
    "收納用品",
    "書籍",
    "文件證件",
    "玩具",
    "寵物用品",
    "嬰幼兒用品",
    "園藝用品",
    "車用用品",
    "五金耗材",
    "急救防災",
]


def _ensure_default_types(existing_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    existing_names = {str(t.get("name", "")).strip() for t in existing_types if t.get("name")}
    missing_names = [name for name in DEFAULT_TYPE_NAMES if name not in existing_names]

    for name in missing_names:
        type_repo.insert_type(name)

    if missing_names:
        return list(type_repo.list_types())
    return existing_types


def list_types() -> List[Dict[str, Any]]:
    return _ensure_default_types(list(type_repo.list_types()))


def create_type(data: Dict[str, Any]) -> None:
    parent_id = data.get("parent_id")
    type_repo.insert_type(data["name"], parent_id=parent_id if parent_id else None)


def update_type(old_name: str, new_name: str) -> tuple[bool, str]:
    """Rename a type, updating all items that reference it."""
    if not new_name or not new_name.strip():
        return False, "類型名稱不能為空"
    new_name = new_name.strip()
    if old_name == new_name:
        return True, "名稱未變更"
    existing = type_repo.get_type_by_name(new_name)
    if existing:
        return False, "該類型名稱已存在"

    ok = type_repo.update_type(old_name, new_name)
    if not ok:
        return False, "找不到該類型"

    count = type_repo.update_items_type(old_name, new_name)
    return True, f"已更新類型名稱，{count} 個物品已同步更新"


def delete_type(name: str) -> tuple[bool, str]:
    """Delete a type. Refuses if items still reference it."""
    count = type_repo.count_items_by_type(name)
    if count > 0:
        return False, f"無法刪除：尚有 {count} 個物品使用此類型，請先變更或刪除這些物品"

    ok = type_repo.delete_type(name)
    if not ok:
        return False, "找不到該類型"
    return True, "類型已刪除"


def get_type_tree() -> List[Dict[str, Any]]:
    """Return a nested tree structure: [{id, name, parent_id, children: [...]}]."""
    flat = type_repo.get_type_tree()

    # Build id->node map
    nodes: Dict[Any, Dict[str, Any]] = {}
    for t in flat:
        nodes[t["id"]] = {
            "id": t["id"],
            "name": t["name"],
            "parent_id": t["parent_id"],
            "children": [],
        }

    roots: List[Dict[str, Any]] = []
    for node in nodes.values():
        parent_id = node["parent_id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def set_parent(type_name: str, parent_name: Optional[str]) -> tuple[bool, str]:
    """Set the parent category for a type."""
    if not type_name:
        return False, "請提供分類名稱"

    t = type_repo.get_type_by_name(type_name)
    if not t:
        return False, "找不到該分類"

    # Clear parent
    if not parent_name or parent_name.strip() == "":
        ok = type_repo.update_type_parent(type_name, None)
        return (True, "已清除父分類") if ok else (False, "操作失敗")

    parent_name = parent_name.strip()
    if parent_name == type_name:
        return False, "不能將分類設為自己的父分類"

    parent = type_repo.get_type_by_name(parent_name)
    if not parent:
        return False, f"找不到父分類「{parent_name}」"

    ok = type_repo.update_type_parent(type_name, parent_name)
    return (True, f"已設定「{parent_name}」為父分類") if ok else (False, "操作失敗")
