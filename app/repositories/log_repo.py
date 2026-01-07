"""操作日誌資料存取模組"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app import mongo, db, get_db_type
from app.models.log import Log


def insert_log(log_entry: Dict[str, Any]) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        log = Log(**log_entry)
        db.session.add(log)
        db.session.commit()
    else:
        # MongoDB uses created_at, PostgreSQL uses timestamp
        mongo_log_entry = log_entry.copy()
        # Convert timestamp to created_at if present
        if "timestamp" in mongo_log_entry and "created_at" not in mongo_log_entry:
            mongo_log_entry["created_at"] = mongo_log_entry.pop("timestamp")
        # Add created_at if not present (PostgreSQL has a default, MongoDB does not)
        if "created_at" not in mongo_log_entry:
            mongo_log_entry["created_at"] = datetime.now()
        mongo.db.activity_logs.insert_one(mongo_log_entry)


def list_logs(
    filter_query: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        query = db.session.query(Log)

        if filter_query:
            if "action" in filter_query:
                query = query.filter(Log.action == filter_query["action"])
            if "user" in filter_query:
                query = query.filter(Log.user == filter_query["user"])

        query = query.order_by(Log.timestamp.desc())

        if skip > 0:
            query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)

        return [log.to_dict() for log in query.all()]

    if filter_query is None:
        filter_query = {}

    logs = list(
        mongo.db.activity_logs.find(filter_query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    for log in logs:
        log["_id"] = str(log["_id"])

    return logs


def count_logs(filter_query: Optional[Dict[str, Any]] = None) -> int:
    db_type = get_db_type()
    if db_type == "postgres":
        query = db.session.query(Log)
        if filter_query:
            if "action" in filter_query:
                query = query.filter(Log.action == filter_query["action"])
            if "user" in filter_query:
                query = query.filter(Log.user == filter_query["user"])
        return query.count()
    if filter_query is None:
        filter_query = {}
    return mongo.db.activity_logs.count_documents(filter_query)


def get_item_logs(item_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        logs = Log.query.filter(Log.item_id == item_id).order_by(Log.timestamp.desc()).limit(limit).all()
        return [log.to_dict() for log in logs]
    return list_logs({"item_id": item_id}, limit=limit)


def ensure_indexes() -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        pass
    else:
        mongo.db.activity_logs.create_index("created_at", background=True)
        mongo.db.activity_logs.create_index("action", background=True)
        mongo.db.activity_logs.create_index("user", background=True)
        mongo.db.activity_logs.create_index("item_id", background=True)
