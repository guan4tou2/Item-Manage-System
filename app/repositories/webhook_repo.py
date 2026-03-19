"""Webhook 資料存取模組"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from app import mongo, db, get_db_type


def create_webhook(data: Dict[str, Any]) -> int:
    """建立 webhook，回傳 id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook

        wh = Webhook(
            user_id=data["user_id"],
            url=data["url"],
            events=data.get("events"),
            secret=data["secret"],
            is_active=data.get("is_active", True),
            failure_count=0,
            created_at=datetime.utcnow(),
        )
        db.session.add(wh)
        db.session.commit()
        return wh.id
    else:
        result = mongo.db.webhooks.insert_one({
            "user_id": data["user_id"],
            "url": data["url"],
            "events": data.get("events"),
            "secret": data["secret"],
            "is_active": data.get("is_active", True),
            "last_triggered_at": None,
            "failure_count": 0,
            "created_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def list_user_webhooks(user_id: str) -> List[Dict[str, Any]]:
    """列出使用者所有 webhooks"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook

        webhooks = db.session.query(Webhook).filter_by(user_id=user_id).order_by(
            Webhook.created_at.desc()
        ).all()
        return [w.to_dict() for w in webhooks]
    else:
        docs = list(mongo.db.webhooks.find({"user_id": user_id}))
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs


def delete_webhook(webhook_id: int, user_id: str) -> bool:
    """刪除 webhook（確認 owner）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook

        wh = db.session.query(Webhook).filter_by(id=webhook_id, user_id=user_id).first()
        if wh:
            db.session.delete(wh)
            db.session.commit()
            return True
        return False
    else:
        from bson import ObjectId

        result = mongo.db.webhooks.delete_one({
            "_id": ObjectId(str(webhook_id)),
            "user_id": user_id,
        })
        return result.deleted_count > 0


def get_webhooks_for_event(event_name: str) -> List[Dict[str, Any]]:
    """取得所有訂閱特定事件且啟用的 webhooks"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook
        from sqlalchemy import or_

        # events 欄位是 JSON 字串，需要包含 event_name 或為 null/空（訂閱所有）
        webhooks = db.session.query(Webhook).filter_by(is_active=True).all()
        result = []
        for wh in webhooks:
            if not wh.events:
                result.append(wh.to_dict())
                continue
            try:
                ev_list = json.loads(wh.events)
                if event_name in ev_list or not ev_list:
                    result.append(wh.to_dict())
            except Exception:
                pass
        return result
    else:
        docs = list(mongo.db.webhooks.find({"is_active": True}))
        result = []
        for doc in docs:
            doc["id"] = str(doc.pop("_id", ""))
            ev_raw = doc.get("events")
            if not ev_raw:
                result.append(doc)
                continue
            try:
                ev_list = json.loads(ev_raw) if isinstance(ev_raw, str) else ev_raw
                if event_name in ev_list or not ev_list:
                    result.append(doc)
            except Exception:
                pass
        return result


def get_webhook_by_id(webhook_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """依 ID 取得 webhook"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook

        wh = db.session.query(Webhook).filter_by(id=webhook_id, user_id=user_id).first()
        return wh.to_dict() if wh else None
    else:
        from bson import ObjectId

        doc = mongo.db.webhooks.find_one({
            "_id": ObjectId(str(webhook_id)),
            "user_id": user_id,
        })
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc


def update_webhook_status(webhook_id: int, last_triggered: datetime, failure_count: int) -> None:
    """更新 webhook 最後觸發時間和失敗次數"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.webhook import Webhook

        wh = db.session.get(Webhook, webhook_id)
        if wh:
            wh.last_triggered_at = last_triggered
            wh.failure_count = failure_count
            if failure_count >= 5:
                wh.is_active = False
            db.session.commit()
    else:
        from bson import ObjectId

        update_data: Dict[str, Any] = {
            "last_triggered_at": last_triggered,
            "failure_count": failure_count,
        }
        if failure_count >= 5:
            update_data["is_active"] = False
        mongo.db.webhooks.update_one(
            {"_id": ObjectId(str(webhook_id))},
            {"$set": update_data},
        )
