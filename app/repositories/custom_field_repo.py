"""自訂欄位資料存取模組"""
from typing import Any, Dict, List, Optional

from app import mongo, db, get_db_type


def list_fields() -> List[Dict[str, Any]]:
    """取得所有自訂欄位，依 sort_order 排序"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomField
        fields = CustomField.query.order_by(CustomField.sort_order.asc(), CustomField.id.asc()).all()
        return [f.to_dict() for f in fields]
    else:
        docs = list(mongo.db.custom_fields.find({}).sort("sort_order", 1))
        result = []
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            result.append(doc)
        return result


def get_field_by_id(field_id) -> Optional[Dict[str, Any]]:
    """取得單一欄位"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomField
        field = CustomField.query.get(int(field_id))
        return field.to_dict() if field else None
    else:
        from bson import ObjectId
        doc = mongo.db.custom_fields.find_one({"_id": ObjectId(str(field_id))})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc


def create_field(
    name: str,
    field_type: str,
    options: Optional[str] = None,
    required: bool = False,
    sort_order: int = 0,
    created_by: str = "",
):
    """新增自訂欄位，回傳 field id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomField
        field = CustomField(
            name=name,
            field_type=field_type,
            options=options or "",
            required=bool(required),
            sort_order=int(sort_order),
            created_by=created_by,
        )
        db.session.add(field)
        db.session.commit()
        return field.id
    else:
        result = mongo.db.custom_fields.insert_one({
            "name": name,
            "field_type": field_type,
            "options": options or "",
            "required": bool(required),
            "sort_order": int(sort_order),
            "created_by": created_by,
        })
        return str(result.inserted_id)


def update_field(field_id, data: Dict[str, Any]) -> bool:
    """更新自訂欄位"""
    db_type = get_db_type()
    allowed = {"name", "field_type", "options", "required", "sort_order"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return False

    if db_type == "postgres":
        from app.models.custom_field import CustomField
        field = CustomField.query.get(int(field_id))
        if not field:
            return False
        for key, val in updates.items():
            setattr(field, key, val)
        db.session.commit()
        return True
    else:
        from bson import ObjectId
        result = mongo.db.custom_fields.update_one(
            {"_id": ObjectId(str(field_id))},
            {"$set": updates},
        )
        return result.modified_count > 0


def delete_field(field_id) -> bool:
    """刪除自訂欄位及所有對應的值"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomField, CustomFieldValue
        # Delete values first (cascade should handle it, but be explicit)
        CustomFieldValue.query.filter_by(field_id=int(field_id)).delete()
        field = CustomField.query.get(int(field_id))
        if not field:
            db.session.rollback()
            return False
        db.session.delete(field)
        db.session.commit()
        return True
    else:
        from bson import ObjectId
        mongo.db.custom_field_values.delete_many({"field_id": str(field_id)})
        result = mongo.db.custom_fields.delete_one({"_id": ObjectId(str(field_id))})
        return result.deleted_count > 0


def get_values(item_id: str) -> List[Dict[str, Any]]:
    """取得某物品的所有自訂欄位值，附帶欄位資訊"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomField, CustomFieldValue
        rows = (
            db.session.query(CustomFieldValue, CustomField)
            .join(CustomField, CustomFieldValue.field_id == CustomField.id)
            .filter(CustomFieldValue.item_id == item_id)
            .order_by(CustomField.sort_order.asc(), CustomField.id.asc())
            .all()
        )
        result = []
        for cfv, cf in rows:
            result.append({
                "field_id": cf.id,
                "field_name": cf.name,
                "field_type": cf.field_type,
                "options": cf.options or "",
                "required": bool(cf.required),
                "value": cfv.value or "",
            })
        return result
    else:
        values = list(mongo.db.custom_field_values.find({"item_id": item_id}))
        field_ids = [v["field_id"] for v in values]
        fields_map: Dict[str, Any] = {}
        for fid in field_ids:
            from bson import ObjectId
            try:
                doc = mongo.db.custom_fields.find_one({"_id": ObjectId(str(fid))})
            except Exception:
                doc = mongo.db.custom_fields.find_one({"_id": fid})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                fields_map[doc["id"]] = doc

        result = []
        for v in values:
            fid = str(v["field_id"])
            field_info = fields_map.get(fid, {})
            if field_info:
                result.append({
                    "field_id": fid,
                    "field_name": field_info.get("name", ""),
                    "field_type": field_info.get("field_type", "text"),
                    "options": field_info.get("options", ""),
                    "required": bool(field_info.get("required", False)),
                    "value": v.get("value", ""),
                })
        result.sort(key=lambda x: fields_map.get(str(x["field_id"]), {}).get("sort_order", 0))
        return result


def set_values(item_id: str, values_dict: Dict[str, str]) -> None:
    """Upsert 物品的自訂欄位值 {field_id: value}"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomFieldValue
        for field_id_str, value in values_dict.items():
            try:
                fid = int(field_id_str)
            except (ValueError, TypeError):
                continue
            existing = CustomFieldValue.query.filter_by(
                item_id=item_id, field_id=fid
            ).first()
            if existing:
                existing.value = str(value)
            else:
                cfv = CustomFieldValue(item_id=item_id, field_id=fid, value=str(value))
                db.session.add(cfv)
        db.session.commit()
    else:
        for field_id_str, value in values_dict.items():
            mongo.db.custom_field_values.update_one(
                {"item_id": item_id, "field_id": str(field_id_str)},
                {"$set": {"value": str(value)}},
                upsert=True,
            )


def delete_values_for_item(item_id: str) -> None:
    """刪除某物品的所有自訂欄位值"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.custom_field import CustomFieldValue
        CustomFieldValue.query.filter_by(item_id=item_id).delete()
        db.session.commit()
    else:
        mongo.db.custom_field_values.delete_many({"item_id": item_id})
