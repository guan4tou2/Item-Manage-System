"""使用者資料存取模組"""
from typing import Optional, Dict, Any, List
from datetime import datetime

from app import mongo, db, get_db_type
from app.models.user import User


def find_by_username(username: str) -> Optional[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        return user.to_dict() if user else None
    return mongo.db.user.find_one({"User": username})


def find_by_username_case_insensitive(username: str) -> Optional[Dict[str, Any]]:
    """以不區分大小寫的方式查找使用者"""
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter(User.User.ilike(username)).first()
        return user.to_dict() if user else None
    return mongo.db.user.find_one({"User": {"$regex": f"^{username}$", "$options": "i"}})


def insert_user(user: Dict[str, Any]) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        new_user = User(**user)
        db.session.add(new_user)
        db.session.commit()
    else:
        mongo.db.user.insert_one(user)


def update_password(username: str, hashed_password: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({"Password": hashed_password})
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"Password": hashed_password}}
        )


def mark_password_changed(username: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({"password_changed": True})
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"password_changed": True}}
        )


def mark_password_not_changed(username: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({"password_changed": False})
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"password_changed": False}}
        )


def list_all_users() -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        users = User.query.all()
        return [{"id": u.id, "User": u.User, "admin": u.admin} for u in users]
    return list(mongo.db.user.find({}, {"_id": 0, "Password": 0}))


def record_login(username: str, ip_address: str, success: bool) -> None:
    db_type = get_db_type()
    login_record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip_address,
        "success": success
    }
    
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        if user:
            user.login_history = (user.login_history or [])[-9:] + [login_record]
            
            if success:
                user.failed_attempts = 0
                user.locked_until = ""
                user.last_login = login_record["time"]
                user.last_login_ip = ip_address
            else:
                user.failed_attempts = (user.failed_attempts or 0) + 1
            
            db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {
                "$push": {
                    "login_history": {
                        "$each": [login_record],
                        "$slice": -10
                    }
                }
            }
        )
        
        if success:
            mongo.db.user.update_one(
                {"User": username},
                {
                    "$set": {
                        "failed_attempts": 0,
                        "locked_until": None,
                        "last_login": login_record["time"],
                        "last_login_ip": ip_address
                    }
                }
            )
        else:
            mongo.db.user.update_one(
                {"User": username},
                {"$inc": {"failed_attempts": 1}}
            )


def get_failed_attempts(username: str) -> int:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        return user.failed_attempts if user else 0
    user = mongo.db.user.find_one({"User": username}, {"failed_attempts": 1})
    return user.get("failed_attempts", 0) if user else 0


def lock_account(username: str, until: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({"locked_until": until})
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"locked_until": until}}
        )


def get_lock_status(username: str) -> Optional[str]:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        return user.locked_until if user else None
    user = mongo.db.user.find_one({"User": username}, {"locked_until": 1})
    return user.get("locked_until") if user else None


def unlock_account(username: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({
            "failed_attempts": 0,
            "locked_until": ""
        })
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"failed_attempts": 0, "locked_until": None}}
        )


def get_login_history(username: str) -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        return user.login_history if user else []
    user = mongo.db.user.find_one({"User": username}, {"login_history": 1})
    return user.get("login_history", []) if user else []


def get_notification_settings(username: str) -> Dict[str, Any]:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        if user:
            return {
                "email": user.email or "",
                "notify_enabled": user.notify_enabled or False,
                "notify_days": user.notify_days or 30,
                "notify_time": user.notify_time or "09:00",
                "notify_channels": list(user.notify_channels or []),
                "reminder_ladder": user.reminder_ladder or "30,14,7,3,1",
                "last_notification_date": user.last_notification_date or "",
                "replacement_enabled": user.replacement_enabled if user.replacement_enabled is not None else True,
                "replacement_intervals": list(user.replacement_intervals or []),
            }
        return {}
    user = mongo.db.user.find_one(
        {"User": username},
        {
            "email": 1,
            "notify_enabled": 1,
            "notify_days": 1,
            "notify_time": 1,
            "notify_channels": 1,
            "reminder_ladder": 1,
            "last_notification_date": 1,
            "replacement_enabled": 1,
            "replacement_intervals": 1,
        }
    )
    if user:
        return {
            "email": user.get("email", ""),
            "notify_enabled": user.get("notify_enabled", False),
            "notify_days": user.get("notify_days", 30),
            "notify_time": user.get("notify_time", "09:00"),
            "notify_channels": user.get("notify_channels", []),
            "reminder_ladder": user.get("reminder_ladder", "30,14,7,3,1"),
            "last_notification_date": user.get("last_notification_date", ""),
            "replacement_enabled": user.get("replacement_enabled", True),
            "replacement_intervals": user.get("replacement_intervals", []),
        }
    return {}


def update_notification_settings(
    username: str,
    email: Optional[str] = None,
    notify_enabled: Optional[bool] = None,
    notify_days: Optional[int] = None,
    notify_time: Optional[str] = None,
    notify_channels: Optional[List[str]] = None,
    reminder_ladder: Optional[str] = None,
    replacement_enabled: Optional[bool] = None,
    replacement_intervals: Optional[List[dict]] = None,
) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        user = User.query.filter_by(User=username).first()
        if user:
            if email is not None:
                user.email = email
            if notify_enabled is not None:
                user.notify_enabled = notify_enabled
            if notify_days is not None:
                user.notify_days = notify_days
            if notify_time is not None:
                user.notify_time = notify_time
            if notify_channels is not None:
                user.notify_channels = notify_channels
            if reminder_ladder is not None:
                user.reminder_ladder = reminder_ladder
            if replacement_enabled is not None:
                user.replacement_enabled = replacement_enabled
            if replacement_intervals is not None:
                user.replacement_intervals = replacement_intervals
            db.session.commit()
    else:
        update_data = {}
        if email is not None:
            update_data["email"] = email
        if notify_enabled is not None:
            update_data["notify_enabled"] = notify_enabled
        if notify_days is not None:
            update_data["notify_days"] = notify_days
        if notify_time is not None:
            update_data["notify_time"] = notify_time
        if notify_channels is not None:
            update_data["notify_channels"] = notify_channels
        if reminder_ladder is not None:
            update_data["reminder_ladder"] = reminder_ladder
        if replacement_enabled is not None:
            update_data["replacement_enabled"] = replacement_enabled
        if replacement_intervals is not None:
            update_data["replacement_intervals"] = replacement_intervals
    
        if update_data:
            mongo.db.user.update_one({"User": username}, {"$set": update_data})



def update_last_notification_date(username: str, date: str) -> None:
    db_type = get_db_type()
    if db_type == "postgres":
        User.query.filter_by(User=username).update({"last_notification_date": date})
        db.session.commit()
    else:
        mongo.db.user.update_one(
            {"User": username},
            {"$set": {"last_notification_date": date}}
        )


def get_all_users_for_notification() -> List[Dict[str, Any]]:
    db_type = get_db_type()
    if db_type == "postgres":
        users = User.query.filter(User.notify_enabled == True).filter(User.email.isnot(None), User.email != "").all()
        return [
            {
                "User": u.User,
                "email": u.email,
                "notify_days": u.notify_days,
                "notify_time": u.notify_time,
                "notify_channels": list(u.notify_channels or []),
                "reminder_ladder": u.reminder_ladder or "30,14,7,3,1",
                "last_notification_date": u.last_notification_date,
                "replacement_enabled": u.replacement_enabled if u.replacement_enabled is not None else True,
                "replacement_intervals": list(u.replacement_intervals or []),
            }
            for u in users
        ]
    return list(mongo.db.user.find(
        {"notify_enabled": True, "email": {"$ne": ""}},
        {
            "_id": 0,
            "User": 1,
            "email": 1,
            "notify_days": 1,
            "notify_time": 1,
            "notify_channels": 1,
            "reminder_ladder": 1,
            "last_notification_date": 1,
            "replacement_enabled": 1,
            "replacement_intervals": 1,
        }
    ))
