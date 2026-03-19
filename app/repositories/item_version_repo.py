"""物品版本歷史資料存取模組"""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from app import get_db_type, db, mongo


def save_version(item_id: str, data_dict: Dict[str, Any], user: str, summary: str = "") -> None:
    """儲存物品的當前狀態為新版本（自動遞增版本號）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.item_version import ItemVersion
        latest = (
            ItemVersion.query.filter_by(item_id=item_id)
            .order_by(ItemVersion.version.desc())
            .first()
        )
        next_version = (latest.version + 1) if latest else 1
        # Convert non-serializable types in data_dict
        serializable = _make_serializable(data_dict)
        version = ItemVersion(
            item_id=item_id,
            version=next_version,
            data=json.dumps(serializable, ensure_ascii=False),
            changed_by=user,
            changed_at=datetime.utcnow(),
            change_summary=summary or None,
        )
        db.session.add(version)
        db.session.commit()
    else:
        col = mongo.db.item_versions
        latest = col.find_one({"item_id": item_id}, sort=[("version", -1)])
        next_version = (latest["version"] + 1) if latest else 1
        serializable = _make_serializable(data_dict)
        col.insert_one({
            "item_id": item_id,
            "version": next_version,
            "data": json.dumps(serializable, ensure_ascii=False),
            "changed_by": user,
            "changed_at": datetime.utcnow(),
            "change_summary": summary or "",
        })


def list_versions(item_id: str) -> List[Dict[str, Any]]:
    """傳回指定物品的版本列表（最新優先）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.item_version import ItemVersion
        versions = (
            ItemVersion.query.filter_by(item_id=item_id)
            .order_by(ItemVersion.version.desc())
            .all()
        )
        return [v.to_dict() for v in versions]
    col = mongo.db.item_versions
    docs = list(col.find({"item_id": item_id}, {"_id": 0}).sort("version", -1))
    for d in docs:
        if isinstance(d.get("changed_at"), datetime):
            d["changed_at"] = d["changed_at"].strftime("%Y-%m-%d %H:%M:%S")
    return docs


def get_version(item_id: str, version: int) -> Optional[Dict[str, Any]]:
    """取得特定版本"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.item_version import ItemVersion
        v = ItemVersion.query.filter_by(item_id=item_id, version=version).first()
        return v.to_dict() if v else None
    col = mongo.db.item_versions
    doc = col.find_one({"item_id": item_id, "version": version}, {"_id": 0})
    if doc and isinstance(doc.get("changed_at"), datetime):
        doc["changed_at"] = doc["changed_at"].strftime("%Y-%m-%d %H:%M:%S")
    return doc


def _make_serializable(obj: Any) -> Any:
    """遞迴將 datetime/date 轉換為字串，確保 JSON 可序列化"""
    from datetime import datetime, date
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, date):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(i) for i in obj]
    return obj
