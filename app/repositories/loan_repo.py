"""物品借出資料存取模組"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app import mongo, db, get_db_type
from app.models.item_loan import ItemLoan


def create_loan(data: Dict[str, Any]) -> int:
    """新增借出記錄，回傳 loan id"""
    db_type = get_db_type()
    if db_type == "postgres":
        loan = ItemLoan(
            item_id=data["item_id"],
            item_name=data.get("item_name", ""),
            borrower=data["borrower"],
            borrower_contact=data.get("borrower_contact"),
            lent_date=data["lent_date"],
            expected_return=data.get("expected_return"),
            actual_return=None,
            status="active",
            notes=data.get("notes"),
            lent_by=data["lent_by"],
            created_at=datetime.utcnow(),
        )
        db.session.add(loan)
        db.session.commit()
        return loan.id
    else:
        result = mongo.db.item_loans.insert_one({
            "item_id": data["item_id"],
            "item_name": data.get("item_name", ""),
            "borrower": data["borrower"],
            "borrower_contact": data.get("borrower_contact"),
            "lent_date": str(data["lent_date"]) if data.get("lent_date") else "",
            "expected_return": str(data["expected_return"]) if data.get("expected_return") else "",
            "actual_return": "",
            "status": "active",
            "notes": data.get("notes"),
            "lent_by": data["lent_by"],
            "created_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def return_loan(loan_id: int) -> bool:
    """標記借出記錄為已歸還"""
    db_type = get_db_type()
    today = date.today()
    if db_type == "postgres":
        loan = ItemLoan.query.get(loan_id)
        if not loan:
            return False
        loan.actual_return = today
        loan.status = "returned"
        db.session.commit()
        return True
    else:
        from bson import ObjectId
        result = mongo.db.item_loans.update_one(
            {"_id": ObjectId(str(loan_id))},
            {"$set": {"actual_return": str(today), "status": "returned"}},
        )
        return result.modified_count > 0


def get_loans_by_item(item_id: str) -> List[Dict[str, Any]]:
    """取得指定物品的所有借出記錄，依 created_at 降冪排序"""
    db_type = get_db_type()
    if db_type == "postgres":
        loans = (
            ItemLoan.query
            .filter(ItemLoan.item_id == item_id)
            .order_by(ItemLoan.created_at.desc())
            .all()
        )
        return [loan.to_dict() for loan in loans]
    else:
        docs = list(
            mongo.db.item_loans.find({"item_id": item_id})
            .sort("created_at", -1)
        )
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            if "created_at" in doc and hasattr(doc["created_at"], "strftime"):
                doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
        return docs


def get_active_loans() -> List[Dict[str, Any]]:
    """取得所有進行中的借出記錄，依 lent_date 降冪排序"""
    db_type = get_db_type()
    if db_type == "postgres":
        loans = (
            ItemLoan.query
            .filter(ItemLoan.status == "active")
            .order_by(ItemLoan.lent_date.desc())
            .all()
        )
        return [loan.to_dict() for loan in loans]
    else:
        docs = list(
            mongo.db.item_loans.find({"status": "active"})
            .sort("lent_date", -1)
        )
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            if "created_at" in doc and hasattr(doc["created_at"], "strftime"):
                doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
        return docs


def get_overdue_loans() -> List[Dict[str, Any]]:
    """取得已逾期的借出記錄 (status=active AND expected_return < today)"""
    db_type = get_db_type()
    today = date.today()
    if db_type == "postgres":
        loans = (
            ItemLoan.query
            .filter(
                ItemLoan.status == "active",
                ItemLoan.expected_return != None,
                ItemLoan.expected_return < today,
            )
            .order_by(ItemLoan.expected_return.asc())
            .all()
        )
        return [loan.to_dict() for loan in loans]
    else:
        today_str = str(today)
        docs = list(
            mongo.db.item_loans.find({
                "status": "active",
                "expected_return": {"$ne": "", "$lt": today_str},
            })
            .sort("expected_return", 1)
        )
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            if "created_at" in doc and hasattr(doc["created_at"], "strftime"):
                doc["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
        return docs


def count_active_loans() -> int:
    """計算進行中的借出數量"""
    db_type = get_db_type()
    if db_type == "postgres":
        return ItemLoan.query.filter(ItemLoan.status == "active").count()
    else:
        return mongo.db.item_loans.count_documents({"status": "active"})


def mark_overdue_loans() -> int:
    """將逾期的 active 借出標記為 overdue，回傳更新筆數"""
    db_type = get_db_type()
    today = date.today()
    if db_type == "postgres":
        loans = (
            ItemLoan.query
            .filter(
                ItemLoan.status == "active",
                ItemLoan.expected_return != None,
                ItemLoan.expected_return < today,
            )
            .all()
        )
        for loan in loans:
            loan.status = "overdue"
        if loans:
            db.session.commit()
        return len(loans)
    else:
        today_str = str(today)
        result = mongo.db.item_loans.update_many(
            {"status": "active", "expected_return": {"$ne": "", "$lt": today_str}},
            {"$set": {"status": "overdue"}},
        )
        return result.modified_count
