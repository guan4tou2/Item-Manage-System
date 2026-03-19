"""倉庫資料存取模組"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from app import mongo, db, get_db_type


def create_warehouse(data: Dict[str, Any]) -> int:
    """建立新倉庫，回傳 warehouse id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        warehouse = Warehouse(
            name=data["name"],
            address=data.get("address"),
            owner=data["owner"],
            group_id=data.get("group_id"),
            is_default=data.get("is_default", False),
            created_at=datetime.utcnow(),
        )
        db.session.add(warehouse)
        db.session.commit()
        return warehouse.id
    else:
        result = mongo.db.warehouses.insert_one({
            "name": data["name"],
            "address": data.get("address", ""),
            "owner": data["owner"],
            "group_id": data.get("group_id"),
            "is_default": data.get("is_default", False),
            "created_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def list_user_warehouses(username: str) -> List[Dict[str, Any]]:
    """列出使用者的所有倉庫"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        warehouses = db.session.query(Warehouse).filter_by(owner=username).order_by(
            Warehouse.is_default.desc(), Warehouse.created_at.asc()
        ).all()
        return [w.to_dict() for w in warehouses]
    else:
        docs = list(mongo.db.warehouses.find({"owner": username}))
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs


def get_warehouse(warehouse_id) -> Optional[Dict[str, Any]]:
    """依 ID 取得倉庫"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        w = db.session.get(Warehouse, warehouse_id)
        return w.to_dict() if w else None
    else:
        from bson import ObjectId

        doc = mongo.db.warehouses.find_one({"_id": ObjectId(str(warehouse_id))})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc


def update_warehouse(warehouse_id, data: Dict[str, Any]) -> bool:
    """更新倉庫資訊"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        w = db.session.get(Warehouse, warehouse_id)
        if not w:
            return False
        if "name" in data:
            w.name = data["name"]
        if "address" in data:
            w.address = data["address"]
        if "group_id" in data:
            w.group_id = data["group_id"]
        if "is_default" in data:
            w.is_default = data["is_default"]
        db.session.commit()
        return True
    else:
        from bson import ObjectId

        result = mongo.db.warehouses.update_one(
            {"_id": ObjectId(str(warehouse_id))},
            {"$set": data}
        )
        return result.modified_count > 0


def delete_warehouse(warehouse_id) -> bool:
    """刪除倉庫"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        w = db.session.get(Warehouse, warehouse_id)
        if w:
            db.session.delete(w)
            db.session.commit()
            return True
        return False
    else:
        from bson import ObjectId

        result = mongo.db.warehouses.delete_one({"_id": ObjectId(str(warehouse_id))})
        return result.deleted_count > 0


def set_default(username: str, warehouse_id) -> bool:
    """設定預設倉庫（先清除所有，再設定指定者）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.warehouse import Warehouse

        # 清除所有預設
        db.session.query(Warehouse).filter_by(owner=username).update({"is_default": False})
        # 設定新預設
        w = db.session.get(Warehouse, warehouse_id)
        if w and w.owner == username:
            w.is_default = True
            db.session.commit()
            return True
        db.session.commit()
        return False
    else:
        from bson import ObjectId

        mongo.db.warehouses.update_many({"owner": username}, {"$set": {"is_default": False}})
        result = mongo.db.warehouses.update_one(
            {"_id": ObjectId(str(warehouse_id)), "owner": username},
            {"$set": {"is_default": True}}
        )
        return result.modified_count > 0
