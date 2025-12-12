"""操作日誌資料存取模組"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app import mongo


def insert_log(log: Dict[str, Any]) -> None:
    """新增操作日誌"""
    log["created_at"] = datetime.now()
    mongo.db.activity_logs.insert_one(log)


def list_logs(
    filter_query: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """查詢操作日誌"""
    if filter_query is None:
        filter_query = {}
    
    logs = list(
        mongo.db.activity_logs.find(filter_query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    # 轉換 ObjectId 為字串
    for log in logs:
        log["_id"] = str(log["_id"])
    
    return logs


def count_logs(filter_query: Optional[Dict[str, Any]] = None) -> int:
    """計算日誌數量"""
    if filter_query is None:
        filter_query = {}
    return mongo.db.activity_logs.count_documents(filter_query)


def get_item_logs(item_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """取得特定物品的操作日誌"""
    return list_logs({"item_id": item_id}, limit=limit)


def ensure_indexes() -> None:
    """建立日誌索引"""
    mongo.db.activity_logs.create_index("created_at", background=True)
    mongo.db.activity_logs.create_index("action", background=True)
    mongo.db.activity_logs.create_index("user", background=True)
    mongo.db.activity_logs.create_index("item_id", background=True)

