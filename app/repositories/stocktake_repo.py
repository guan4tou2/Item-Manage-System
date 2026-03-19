"""庫存盤點資料存取模組"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from app import mongo, db, get_db_type
from app.models.stocktake import StocktakeSession, StocktakeItem


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def create_session(name: str, created_by: str, notes: Optional[str] = None) -> Any:
    """建立盤點作業，回傳 session id"""
    db_type = get_db_type()
    if db_type == "postgres":
        session = StocktakeSession(
            name=name,
            status="draft",
            created_by=created_by,
            created_at=datetime.utcnow(),
            notes=notes,
        )
        db.session.add(session)
        db.session.commit()
        return session.id
    else:
        result = mongo.db.stocktake_sessions.insert_one({
            "name": name,
            "status": "draft",
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "committed_at": None,
            "notes": notes or "",
        })
        return str(result.inserted_id)


def get_session(session_id: Any) -> Optional[Dict[str, Any]]:
    """取得盤點作業及其所有明細"""
    db_type = get_db_type()
    if db_type == "postgres":
        sess = StocktakeSession.query.get(int(session_id))
        if not sess:
            return None
        d = sess.to_dict()
        d["items"] = [item.to_dict() for item in sess.items]
        return d
    else:
        from bson import ObjectId
        doc = mongo.db.stocktake_sessions.find_one({"_id": ObjectId(str(session_id))})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        if doc.get("created_at") and hasattr(doc["created_at"], "strftime"):
            doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
        if doc.get("committed_at") and hasattr(doc["committed_at"], "strftime"):
            doc["committed_at"] = doc["committed_at"].strftime("%Y-%m-%d %H:%M")

        items = list(mongo.db.stocktake_items.find({"session_id": str(session_id)}))
        for item in items:
            item["id"] = str(item.pop("_id"))
            if item.get("counted_at") and hasattr(item["counted_at"], "strftime"):
                item["counted_at"] = item["counted_at"].strftime("%Y-%m-%d %H:%M")
        doc["items"] = items
        doc["item_count"] = len(items)
        return doc


def list_sessions() -> List[Dict[str, Any]]:
    """取得所有盤點作業（不含明細），依建立時間降冪"""
    db_type = get_db_type()
    if db_type == "postgres":
        sessions = StocktakeSession.query.order_by(StocktakeSession.created_at.desc()).all()
        return [s.to_dict() for s in sessions]
    else:
        docs = list(mongo.db.stocktake_sessions.find().sort("created_at", -1))
        result = []
        for doc in docs:
            sid = str(doc.pop("_id"))
            doc["id"] = sid
            if doc.get("created_at") and hasattr(doc["created_at"], "strftime"):
                doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
            if doc.get("committed_at") and hasattr(doc["committed_at"], "strftime"):
                doc["committed_at"] = doc["committed_at"].strftime("%Y-%m-%d %H:%M")
            doc["item_count"] = mongo.db.stocktake_items.count_documents({"session_id": sid})
            result.append(doc)
        return result


def update_session_status(session_id: Any, status: str, committed_at: Optional[datetime] = None) -> bool:
    """更新盤點作業狀態"""
    db_type = get_db_type()
    if db_type == "postgres":
        sess = StocktakeSession.query.get(int(session_id))
        if not sess:
            return False
        sess.status = status
        if committed_at:
            sess.committed_at = committed_at
        db.session.commit()
        return True
    else:
        from bson import ObjectId
        updates: Dict[str, Any] = {"status": status}
        if committed_at:
            updates["committed_at"] = committed_at
        result = mongo.db.stocktake_sessions.update_one(
            {"_id": ObjectId(str(session_id))},
            {"$set": updates},
        )
        return result.modified_count > 0


# ---------------------------------------------------------------------------
# Item operations
# ---------------------------------------------------------------------------

def populate_session(session_id: Any) -> int:
    """從現有庫存自動填入盤點明細，回傳建立的明細筆數"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.item import Item
        items = Item.query.all()
        count = 0
        for item in items:
            si = StocktakeItem(
                session_id=int(session_id),
                item_id=item.ItemID,
                item_name=item.ItemName,
                expected_qty=item.Quantity or 0,
                actual_qty=None,
                status="pending",
            )
            db.session.add(si)
            count += 1
        db.session.commit()
        return count
    else:
        items = list(mongo.db.item.find({}, {"ItemID": 1, "ItemName": 1, "Quantity": 1}))
        docs = []
        for item in items:
            docs.append({
                "session_id": str(session_id),
                "item_id": item.get("ItemID", ""),
                "item_name": item.get("ItemName", ""),
                "expected_qty": item.get("Quantity", 0) or 0,
                "actual_qty": None,
                "status": "pending",
                "counted_by": None,
                "counted_at": None,
                "notes": "",
            })
        if docs:
            mongo.db.stocktake_items.insert_many(docs)
        return len(docs)


def record_count(session_id: Any, item_id: str, actual_qty: int, counted_by: str) -> bool:
    """記錄實際盤點數量，自動判斷 status"""
    db_type = get_db_type()
    now = datetime.utcnow()
    if db_type == "postgres":
        si = StocktakeItem.query.filter_by(
            session_id=int(session_id), item_id=item_id
        ).first()
        if not si:
            return False
        si.actual_qty = actual_qty
        si.counted_by = counted_by
        si.counted_at = now
        si.status = "discrepancy" if actual_qty != si.expected_qty else "counted"
        db.session.commit()
        return True
    else:
        doc = mongo.db.stocktake_items.find_one(
            {"session_id": str(session_id), "item_id": item_id}
        )
        if not doc:
            return False
        expected_qty = doc.get("expected_qty", 0)
        new_status = "discrepancy" if actual_qty != expected_qty else "counted"
        mongo.db.stocktake_items.update_one(
            {"session_id": str(session_id), "item_id": item_id},
            {"$set": {
                "actual_qty": actual_qty,
                "counted_by": counted_by,
                "counted_at": now,
                "status": new_status,
            }},
        )
        return True


def mark_discrepancies(session_id: Any) -> int:
    """將所有已盤點但數量不符的明細標記為 discrepancy，回傳標記筆數"""
    db_type = get_db_type()
    if db_type == "postgres":
        from sqlalchemy import and_
        items = StocktakeItem.query.filter(
            StocktakeItem.session_id == int(session_id),
            StocktakeItem.actual_qty.isnot(None),
        ).all()
        count = 0
        for item in items:
            correct_status = "discrepancy" if item.actual_qty != item.expected_qty else "counted"
            if item.status != correct_status:
                item.status = correct_status
                count += 1
        if count:
            db.session.commit()
        return count
    else:
        items = list(mongo.db.stocktake_items.find({
            "session_id": str(session_id),
            "actual_qty": {"$ne": None},
        }))
        count = 0
        for item in items:
            correct_status = "discrepancy" if item.get("actual_qty") != item.get("expected_qty", 0) else "counted"
            if item.get("status") != correct_status:
                mongo.db.stocktake_items.update_one(
                    {"_id": item["_id"]},
                    {"$set": {"status": correct_status}},
                )
                count += 1
        return count


def apply_counts_to_inventory(session_id: Any) -> int:
    """將盤點實際數量寫回庫存，回傳更新筆數"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.item import Item
        items = StocktakeItem.query.filter(
            StocktakeItem.session_id == int(session_id),
            StocktakeItem.actual_qty.isnot(None),
        ).all()
        count = 0
        for si in items:
            updated = Item.query.filter_by(ItemID=si.item_id).update(
                {"Quantity": si.actual_qty}
            )
            if updated:
                count += 1
        db.session.commit()
        return count
    else:
        items = list(mongo.db.stocktake_items.find({
            "session_id": str(session_id),
            "actual_qty": {"$ne": None},
        }))
        count = 0
        for si in items:
            result = mongo.db.item.update_one(
                {"ItemID": si["item_id"]},
                {"$set": {"Quantity": si["actual_qty"]}},
            )
            if result.modified_count:
                count += 1
        return count


def get_session_summary(session_id: Any) -> Dict[str, int]:
    """取得盤點作業各狀態統計"""
    db_type = get_db_type()
    if db_type == "postgres":
        from sqlalchemy import func
        rows = (
            db.session.query(StocktakeItem.status, func.count(StocktakeItem.id))
            .filter(StocktakeItem.session_id == int(session_id))
            .group_by(StocktakeItem.status)
            .all()
        )
        summary = {"pending": 0, "counted": 0, "discrepancy": 0, "total": 0}
        for status, cnt in rows:
            if status in summary:
                summary[status] = cnt
            summary["total"] += cnt
        return summary
    else:
        pipeline = [
            {"$match": {"session_id": str(session_id)}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        rows = list(mongo.db.stocktake_items.aggregate(pipeline))
        summary = {"pending": 0, "counted": 0, "discrepancy": 0, "total": 0}
        for row in rows:
            status = row["_id"]
            cnt = row["count"]
            if status in summary:
                summary[status] = cnt
            summary["total"] += cnt
        return summary
