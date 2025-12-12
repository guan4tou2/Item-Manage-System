"""操作日誌服務模組"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.repositories import log_repo


# 操作類型常量
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_MOVE = "move"
ACTION_IMPORT = "import"
ACTION_EXPORT = "export"


def log_action(
    action: str,
    user: str,
    item_id: Optional[str] = None,
    item_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """記錄操作日誌"""
    log_entry = {
        "action": action,
        "user": user,
        "item_id": item_id,
        "item_name": item_name,
        "details": details or {},
    }
    log_repo.insert_log(log_entry)


def log_item_create(user: str, item_id: str, item_name: str) -> None:
    """記錄新增物品"""
    log_action(
        ACTION_CREATE,
        user,
        item_id,
        item_name,
        {"message": f"新增物品: {item_name}"}
    )


def log_item_update(user: str, item_id: str, item_name: str, changes: Dict[str, Any] = None) -> None:
    """記錄更新物品"""
    log_action(
        ACTION_UPDATE,
        user,
        item_id,
        item_name,
        {"message": f"更新物品: {item_name}", "changes": changes or {}}
    )


def log_item_delete(user: str, item_id: str, item_name: str) -> None:
    """記錄刪除物品"""
    log_action(
        ACTION_DELETE,
        user,
        item_id,
        item_name,
        {"message": f"刪除物品: {item_name}"}
    )


def log_item_move(
    user: str, 
    item_id: str, 
    item_name: str, 
    from_location: str, 
    to_location: str
) -> None:
    """記錄移動物品"""
    log_action(
        ACTION_MOVE,
        user,
        item_id,
        item_name,
        {
            "message": f"移動物品: {item_name}",
            "from": from_location,
            "to": to_location,
        }
    )


def log_import(user: str, success: int, failed: int) -> None:
    """記錄匯入操作"""
    log_action(
        ACTION_IMPORT,
        user,
        details={
            "message": f"匯入物品: 成功 {success} 筆, 失敗 {failed} 筆",
            "success": success,
            "failed": failed,
        }
    )


def log_export(user: str, format: str, count: int) -> None:
    """記錄匯出操作"""
    log_action(
        ACTION_EXPORT,
        user,
        details={
            "message": f"匯出 {count} 筆物品為 {format.upper()} 格式",
            "format": format,
            "count": count,
        }
    )


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """取得最近的操作日誌"""
    return log_repo.list_logs(limit=limit)


def get_item_history(item_id: str) -> List[Dict[str, Any]]:
    """取得物品的操作歷史"""
    return log_repo.get_item_logs(item_id)


def get_user_logs(username: str, limit: int = 50) -> List[Dict[str, Any]]:
    """取得使用者的操作日誌"""
    return log_repo.list_logs({"user": username}, limit=limit)


def get_logs_paginated(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """分頁取得操作日誌"""
    total = log_repo.count_logs()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    logs = log_repo.list_logs(limit=page_size, skip=skip)
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }

