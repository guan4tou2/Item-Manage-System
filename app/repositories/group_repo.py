"""群組資料存取模組"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from app import mongo, db, get_db_type


def create_group(name: str, owner: str) -> int:
    """建立新群組，回傳 group id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import Group

        group = Group(name=name, owner=owner, created_at=datetime.utcnow())
        db.session.add(group)
        db.session.commit()
        return group.id
    else:
        result = mongo.db.groups.insert_one({
            "name": name,
            "owner": owner,
            "created_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def get_group(group_id) -> Optional[Dict[str, Any]]:
    """依 ID 取得群組"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import Group

        group = db.session.get(Group, group_id)
        return group.to_dict() if group else None
    else:
        from bson import ObjectId

        doc = mongo.db.groups.find_one({"_id": ObjectId(str(group_id))})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc


def list_user_groups(username: str) -> List[Dict[str, Any]]:
    """列出使用者所有群組（擁有者或成員）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import Group, GroupMember

        owned = db.session.query(Group).filter(Group.owner == username).all()
        owned_ids = {g.id for g in owned}
        member_group_ids = [
            m.group_id for m in db.session.query(GroupMember)
            .filter(GroupMember.username == username)
            .all()
            if m.group_id not in owned_ids
        ]
        member_groups = db.session.query(Group).filter(Group.id.in_(member_group_ids)).all() if member_group_ids else []
        all_groups = owned + member_groups
        return [g.to_dict() for g in all_groups]
    else:
        owned = list(mongo.db.groups.find({"owner": username}))
        member_docs = list(mongo.db.group_members.find({"username": username}))
        member_group_ids = [m["group_id"] for m in member_docs]
        member_groups = list(mongo.db.groups.find({"_id": {"$in": member_group_ids}, "owner": {"$ne": username}}))
        result = []
        for doc in owned + member_groups:
            doc["id"] = str(doc.pop("_id"))
            result.append(doc)
        return result


def add_member(group_id, username: str, role: str = "member") -> int:
    """加入群組成員，回傳 member id"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import GroupMember

        member = GroupMember(
            group_id=group_id,
            username=username,
            role=role,
            joined_at=datetime.utcnow(),
        )
        db.session.add(member)
        db.session.commit()
        return member.id
    else:
        result = mongo.db.group_members.insert_one({
            "group_id": group_id,
            "username": username,
            "role": role,
            "joined_at": datetime.utcnow(),
        })
        return str(result.inserted_id)


def remove_member(group_id, username: str) -> bool:
    """從群組移除成員"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import GroupMember

        member = db.session.query(GroupMember).filter_by(
            group_id=group_id, username=username
        ).first()
        if member:
            db.session.delete(member)
            db.session.commit()
            return True
        return False
    else:
        result = mongo.db.group_members.delete_one({"group_id": group_id, "username": username})
        return result.deleted_count > 0


def get_group_members(group_id) -> List[Dict[str, Any]]:
    """取得群組所有成員"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import GroupMember

        members = db.session.query(GroupMember).filter_by(group_id=group_id).all()
        return [m.to_dict() for m in members]
    else:
        docs = list(mongo.db.group_members.find({"group_id": group_id}))
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs


def is_member(group_id, username: str) -> bool:
    """檢查使用者是否為群組成員（含擁有者）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import Group, GroupMember

        group = db.session.get(Group, group_id)
        if group and group.owner == username:
            return True
        return db.session.query(GroupMember).filter_by(
            group_id=group_id, username=username
        ).first() is not None
    else:
        from bson import ObjectId

        group = mongo.db.groups.find_one({"_id": ObjectId(str(group_id))})
        if group and group.get("owner") == username:
            return True
        return mongo.db.group_members.find_one({"group_id": group_id, "username": username}) is not None


def delete_group(group_id) -> bool:
    """刪除群組"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.group import Group

        group = db.session.get(Group, group_id)
        if group:
            db.session.delete(group)
            db.session.commit()
            return True
        return False
    else:
        from bson import ObjectId

        mongo.db.group_members.delete_many({"group_id": group_id})
        result = mongo.db.groups.delete_one({"_id": ObjectId(str(group_id))})
        return result.deleted_count > 0
