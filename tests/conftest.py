import sys
import types

import tests.fixtures_env  # noqa: F401


class _FakeCollection:
    def __init__(self):
        self.data = {}

    def find_one(self, query):
        key, val = next(iter(query.items())) if query else (None, None)
        if isinstance(val, dict) and "$regex" in val:
            target = val["$regex"].strip("^").strip("$")
            for k, v in self.data.items():
                if target.lower() in str(k).lower():
                    return v
            return None
        return self.data.get(val)

    def insert_one(self, doc):
        if doc is None:
            return
        key = doc.get("User") or doc.get("ItemID") or doc.get("ItemName") or str(len(self.data))
        self.data[key] = doc

    def update_one(self, query, update):
        key, val = next(iter(query.items())) if query else (None, None)
        doc = self.data.get(val, {})
        if isinstance(update, dict):
            if "$set" in update:
                doc.update(update.get("$set", {}))
            if "$push" in update:
                for k, pushv in update["$push"].items():
                    arr = doc.get(k, [])
                    if "$each" in pushv:
                        arr += pushv["$each"]
                    doc[k] = arr[-10:]
        self.data[val] = doc

    def delete_one(self, query):
        key, val = next(iter(query.items())) if query else (None, None)
        self.data.pop(val, None)

    def find(self, *_, **__):
        return list(self.data.values())


class _FakeMongoDB:
    def __init__(self):
        self.user = _FakeCollection()
        self.items = _FakeCollection()


_fake_mongo_mod = types.ModuleType("app.mongo")
_fake_mongo_mod.db = _FakeMongoDB()  # type: ignore[attr-defined]
sys.modules["app.mongo"] = _fake_mongo_mod
sys.modules["mongo"] = _fake_mongo_mod

import app  # type: ignore  # noqa: E402
import app.repositories.user_repo as user_repo  # noqa: E402
import app.repositories.type_repo as type_repo  # noqa: E402
import app.repositories.item_repo as item_repo  # noqa: E402

app.get_db_type = lambda: "postgres"  # type: ignore[assignment]
app.db.init_app = lambda *args, **kwargs: None  # type: ignore[assignment]
app.db.create_all = lambda *args, **kwargs: None  # type: ignore[assignment]

app.mongo = _fake_mongo_mod  # type: ignore[attr-defined]
sys.modules["mongo"] = _fake_mongo_mod

app.limiter.enabled = False  # type: ignore[attr-defined]
app.cache.init_app = lambda *args, **kwargs: None  # type: ignore[assignment]

import importlib
user_repo = importlib.reload(user_repo)  # type: ignore[assignment]
item_repo = importlib.reload(item_repo)  # type: ignore[assignment]
type_repo = importlib.reload(type_repo)  # type: ignore[assignment]
import app.services.user_service as user_service  # noqa: E402

user_service.get_db_type = lambda: "mongo"  # type: ignore[assignment]

fake_settings = {
    "email": "admin@example.com",
    "notify_enabled": True,
    "notify_days": 30,
    "notify_time": "09:00",
    "notify_channels": ["email"],
    "reminder_ladder": "30,14,7,3,1",
    "last_notification_date": "",
    "replacement_enabled": True,
    "replacement_intervals": [],
}

user_repo.get_db_type = lambda: "mongo"  # type: ignore[assignment]

_fake_mongo_mod.db.user.find = lambda *args, **kwargs: list(_fake_mongo_mod.db.user.data.values())  # type: ignore[attr-defined]

user_repo.get_notification_settings = lambda username: fake_settings.copy()  # type: ignore[assignment]
user_repo.update_notification_settings = lambda **kwargs: fake_settings.update({k: v for k, v in kwargs.items() if v is not None})  # type: ignore[assignment]
user_repo.update_last_notification_date = lambda username, date_str: fake_settings.update({"last_notification_date": date_str})  # type: ignore[assignment]
setattr(user_repo, "get_all_users_for_notification", lambda: [
    {
        "User": "admin",
        "email": fake_settings["email"],
        "notify_days": fake_settings["notify_days"],
        "notify_time": fake_settings["notify_time"],
        "notify_channels": fake_settings["notify_channels"],
        "reminder_ladder": fake_settings["reminder_ladder"],
        "last_notification_date": fake_settings["last_notification_date"],
        "replacement_enabled": fake_settings["replacement_enabled"],
        "replacement_intervals": fake_settings["replacement_intervals"],
    }
])

item_repo.list_items = lambda *args, **kwargs: []  # type: ignore[assignment]
item_repo.find_item_by_id = lambda *args, **kwargs: None  # type: ignore[assignment]
item_repo.get_stats = lambda: {"total": 0, "by_type": {}, "low_stock": 0}  # type: ignore[assignment]
_fake_types: list = []

type_repo.insert_type = lambda doc: _fake_types.append(doc if isinstance(doc, dict) else {"name": doc})  # type: ignore[assignment]
type_repo.list_types = lambda: list(_fake_types)  # type: ignore[assignment]
type_repo.find_by_name = lambda name: next((t for t in _fake_types if isinstance(t, dict) and t.get("name") == name), None)  # type: ignore[assignment]

type_repo.get_db_type = lambda: "mongo"  # type: ignore[assignment]

import app.__init__ as app_init  # noqa: E402
app_init._ensure_default_admin = lambda: None  # type: ignore[assignment]

