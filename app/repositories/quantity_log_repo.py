"""數量變動日誌資料存取模組"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app import mongo, db, get_db_type
from app.models.quantity_log import QuantityLog


def insert_log(
    item_id: str,
    item_name: str,
    user: str,
    delta: int,
    old_qty: int,
    new_qty: int,
    reason: Optional[str] = None,
) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        log = QuantityLog(
            item_id=item_id,
            item_name=item_name,
            user=user,
            delta=delta,
            old_quantity=old_qty,
            new_quantity=new_qty,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        db.session.add(log)
        db.session.commit()
    else:
        mongo.db.quantity_logs.insert_one({
            "item_id": item_id,
            "item_name": item_name,
            "user": user,
            "delta": delta,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "reason": reason,
            "timestamp": datetime.utcnow(),
        })


def get_logs_by_item(item_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        logs = (
            QuantityLog.query
            .filter(QuantityLog.item_id == item_id)
            .order_by(QuantityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [log.to_dict() for log in logs]
    else:
        docs = list(
            mongo.db.quantity_logs.find({"item_id": item_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "strftime"):
                doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M")
        return docs


def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        logs = (
            QuantityLog.query
            .order_by(QuantityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [log.to_dict() for log in logs]
    else:
        docs = list(
            mongo.db.quantity_logs.find({})
            .sort("timestamp", -1)
            .limit(limit)
        )
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "strftime"):
                doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M")
        return docs
