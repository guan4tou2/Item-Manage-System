"""API Token 資料存取模組"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import db, get_db_type


def create_token(
    user_id: str,
    name: str,
    token_hash: str,
    prefix: str,
    scopes: Optional[str] = None,
) -> int:
    """建立新 API Token，回傳 token id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        token = APIToken(
            user_id=user_id,
            name=name,
            token_hash=token_hash,
            token_prefix=prefix,
            scopes=scopes,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(token)
        db.session.commit()
        return token.id
    else:
        from app import mongo

        result = mongo.db.api_tokens.insert_one({
            "user_id": user_id,
            "name": name,
            "token_hash": token_hash,
            "token_prefix": prefix,
            "scopes": scopes,
            "expires_at": None,
            "last_used_at": None,
            "is_active": True,
            "created_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def find_by_hash(token_hash: str) -> Optional[Dict[str, Any]]:
    """依 token hash 查詢 token"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        token = APIToken.query.filter_by(token_hash=token_hash).first()
        return token.to_dict() if token else None
    else:
        from app import mongo

        doc = mongo.db.api_tokens.find_one({"token_hash": token_hash})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc


def find_by_hash_obj(token_hash: str):
    """依 token hash 查詢 token ORM 物件（僅 Postgres 使用）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        return APIToken.query.filter_by(token_hash=token_hash).first()
    return None


def list_user_tokens(user_id: str) -> List[Dict[str, Any]]:
    """列出使用者的所有 token"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        tokens = APIToken.query.filter_by(user_id=user_id).order_by(
            APIToken.created_at.desc()
        ).all()
        return [t.to_dict() for t in tokens]
    else:
        from app import mongo

        docs = list(mongo.db.api_tokens.find({"user_id": user_id}).sort("created_at", -1))
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs


def revoke_token(token_id, user_id: str) -> bool:
    """撤銷指定 token（設定 is_active=False）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        token = db.session.get(APIToken, int(token_id))
        if token and token.user_id == user_id:
            token.is_active = False
            db.session.commit()
            return True
        return False
    else:
        from app import mongo
        from bson import ObjectId

        result = mongo.db.api_tokens.update_one(
            {"_id": ObjectId(str(token_id)), "user_id": user_id},
            {"$set": {"is_active": False}},
        )
        return result.modified_count > 0


def update_last_used(token_id) -> None:
    """更新最後使用時間"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.api_token import APIToken

        token = db.session.get(APIToken, int(token_id))
        if token:
            token.last_used_at = datetime.utcnow()
            db.session.commit()
    else:
        from app import mongo
        from bson import ObjectId

        mongo.db.api_tokens.update_one(
            {"_id": ObjectId(str(token_id))},
            {"$set": {"last_used_at": datetime.utcnow()}},
        )
