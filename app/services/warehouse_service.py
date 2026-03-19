"""倉庫服務模組"""
from typing import Any, Dict, List, Optional, Tuple

from flask import session as flask_session

from app.repositories import warehouse_repo

SESSION_KEY = "active_warehouse_id"


def create_warehouse(
    name: str,
    owner: str,
    address: str = "",
    group_id: Optional[int] = None,
) -> Tuple[bool, str, Any]:
    """建立倉庫。回傳 (success, message, warehouse_id)"""
    name = name.strip()
    if not name:
        return False, "倉庫名稱不可為空", None

    existing = warehouse_repo.list_user_warehouses(owner)
    is_default = len(existing) == 0  # 第一個倉庫自動設為預設

    data = {
        "name": name,
        "address": address.strip() if address else "",
        "owner": owner,
        "group_id": group_id,
        "is_default": is_default,
    }
    warehouse_id = warehouse_repo.create_warehouse(data)
    return True, "倉庫建立成功", warehouse_id


def get_user_warehouses(username: str) -> List[Dict[str, Any]]:
    """取得使用者所有倉庫"""
    return warehouse_repo.list_user_warehouses(username)


def switch_warehouse(username: str, warehouse_id: int) -> Tuple[bool, str]:
    """切換作用中倉庫，同時更新 session"""
    w = warehouse_repo.get_warehouse(warehouse_id)
    if not w:
        return False, "倉庫不存在"
    if w.get("owner") != username:
        return False, "無權限切換此倉庫"

    warehouse_repo.set_default(username, warehouse_id)
    flask_session[SESSION_KEY] = warehouse_id
    return True, f"已切換至倉庫「{w['name']}」"


def get_active_warehouse(username: str) -> Optional[Dict[str, Any]]:
    """取得當前作用中倉庫（從 session 或預設倉庫取得）"""
    active_id = flask_session.get(SESSION_KEY)
    if active_id:
        w = warehouse_repo.get_warehouse(active_id)
        if w and w.get("owner") == username:
            return w

    warehouses = warehouse_repo.list_user_warehouses(username)
    if not warehouses:
        return None

    for w in warehouses:
        if w.get("is_default"):
            flask_session[SESSION_KEY] = w["id"]
            return w

    # fallback: 第一個倉庫
    first = warehouses[0]
    flask_session[SESSION_KEY] = first["id"]
    return first


def delete_warehouse(username: str, warehouse_id: int) -> Tuple[bool, str]:
    """刪除倉庫"""
    w = warehouse_repo.get_warehouse(warehouse_id)
    if not w:
        return False, "倉庫不存在"
    if w.get("owner") != username:
        return False, "無權限刪除此倉庫"

    warehouse_repo.delete_warehouse(warehouse_id)
    # 清除 session 中的倉庫選擇（若刪除的是當前作用中倉庫）
    if flask_session.get(SESSION_KEY) == warehouse_id:
        flask_session.pop(SESSION_KEY, None)
    return True, "倉庫已刪除"
