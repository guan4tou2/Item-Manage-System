"""PostgreSQL repository implementations"""
from typing import List, Dict, Any, Optional, Generator, Tuple

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app import db, cache
from app.models import Item, ItemType, Location
from app.repositories.base import BaseRepository, TypeRepository, LocationRepository


class PostgresItemRepository(BaseRepository):
    """PostgreSQL implementation for Item repository"""

    def find_by_id(self, item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        item = db.session.query(Item).filter_by(ItemID=item_id).first()
        return item.to_dict() if item else None

    def insert(self, item: Dict[str, Any]) -> None:
        new_item = Item(**item)
        db.session.add(new_item)
        db.session.commit()

    def update(self, item_id: str, updates: Dict[str, Any]) -> None:
        Item.query.filter_by(ItemID=item_id).update(updates)
        db.session.commit()

    def delete(self, item_id: str) -> bool:
        result = Item.query.filter_by(ItemID=item_id).delete()
        db.session.commit()
        return result > 0

    def list_all(
        self,
        filter_query: Dict[str, Any],
        sort: Optional[List[Tuple[str, int]]] = None,
        skip: int = 0,
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        query = db.session.query(Item)

        if "ItemName" in filter_query and filter_query["ItemName"]:
            query = query.filter(Item.ItemName.ilike(f"%{filter_query['ItemName']}%"))
        if "ItemStorePlace" in filter_query and filter_query["ItemStorePlace"]:
            query = query.filter(Item.ItemStorePlace.ilike(f"%{filter_query['ItemStorePlace']}%"))
        if "ItemType" in filter_query and filter_query["ItemType"]:
            query = query.filter(Item.ItemType == filter_query["ItemType"])
        if "ItemFloor" in filter_query and filter_query["ItemFloor"]:
            query = query.filter(Item.ItemFloor == filter_query["ItemFloor"])
        if "ItemRoom" in filter_query and filter_query["ItemRoom"]:
            query = query.filter(Item.ItemRoom == filter_query["ItemRoom"])
        if "ItemZone" in filter_query and filter_query["ItemZone"]:
            query = query.filter(Item.ItemZone == filter_query["ItemZone"])

        if sort:
            for field, direction in sort:
                attr = getattr(Item, field)
                query = query.order_by(attr.asc() if direction == 1 else attr.desc())

        if skip > 0:
            query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)

        return [item.to_dict() for item in query.all()]

    def count(self, filter_query: Dict[str, Any]) -> int:
        query = db.session.query(Item)

        if "ItemName" in filter_query and filter_query["ItemName"]:
            query = query.filter(Item.ItemName.ilike(f"%{filter_query['ItemName']}%"))
        if "ItemStorePlace" in filter_query and filter_query["ItemStorePlace"]:
            query = query.filter(Item.ItemStorePlace.ilike(f"%{filter_query['ItemStorePlace']}%"))
        if "ItemType" in filter_query and filter_query["ItemType"]:
            query = query.filter(Item.ItemType == filter_query["ItemType"])
        if "ItemFloor" in filter_query and filter_query["ItemFloor"]:
            query = query.filter(Item.ItemFloor == filter_query["ItemFloor"])
        if "ItemRoom" in filter_query and filter_query["ItemRoom"]:
            query = query.filter(Item.ItemRoom == filter_query["ItemRoom"])
        if "ItemZone" in filter_query and filter_query["ItemZone"]:
            query = query.filter(Item.ItemZone == filter_query["ItemZone"])

        return query.count()

    def get_expiring_items(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        from datetime import date, timedelta

        today = date.today()
        threshold_date = today + timedelta(days=days_threshold)

        expired_items = Item.query.filter(
            or_(
                Item.WarrantyExpiry < today,
                Item.UsageExpiry < today
            )
        ).all()

        near_expiry_items = Item.query.filter(
            and_(
                or_(
                    Item.WarrantyExpiry >= today,
                    Item.UsageExpiry >= today
                ),
                or_(
                    Item.WarrantyExpiry <= threshold_date,
                    Item.UsageExpiry <= threshold_date
                )
            )
        ).all()

        items = expired_items + near_expiry_items
        return [item.to_dict() for item in items]


class PostgresTypeRepository(TypeRepository):
    """PostgreSQL implementation for Type repository"""

    def list_all(self) -> List[Dict[str, Any]]:
        cache_key = "types_list_postgres"

        cached = cache.get(cache_key)
        if cached:
            return cached

        types = db.session.query(ItemType).all()
        result = [{"id": t.id, "name": t.name} for t in types]

        cache.set(cache_key, result, timeout=300)
        return result

    def insert(self, name: str) -> None:
        item_type = ItemType(name=name)
        db.session.add(item_type)
        db.session.commit()

        cache.delete("types_list_postgres")

    def delete(self, name: str) -> bool:
        result = ItemType.query.filter_by(name=name).delete()
        db.session.commit()

        cache.delete("types_list_postgres")

        return result > 0

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cache_key = f"type_by_name_{name}"

        cached = cache.get(cache_key)
        if cached:
            return cached

        type_obj = ItemType.query.filter_by(name=name).first()
        result = type_obj.to_dict() if type_obj else None

        if result:
            cache.set(cache_key, result, timeout=300)

        return result


class PostgresLocationRepository(LocationRepository):
    """PostgreSQL implementation for Location repository"""

    def list_all(self) -> Generator[Dict[str, Any], None, None]:
        cache_key = "locations_list_postgres"

        cached = cache.get(cache_key)
        if cached:
            for loc in cached:
                yield loc
            return

        locations = db.session.query(Location).order_by(Location.order).all()
        result = [loc.to_dict() for loc in locations]

        cache.set(cache_key, result, timeout=300)

        for loc in result:
            yield loc

    def insert(self, doc: Dict[str, Any]) -> None:
        location = Location(
            floor=doc.get("floor"),
            room=doc.get("room"),
            zone=doc.get("zone"),
            order=doc.get("order", 0),
        )
        db.session.add(location)
        db.session.commit()

        cache.delete("locations_list_postgres")

    def delete(self, loc_id) -> None:
        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            db.session.delete(location)
            db.session.commit()

        cache.delete("locations_list_postgres")

    def update(self, loc_id, doc: Dict[str, Any]) -> None:
        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            if "floor" in doc:
                location.floor = doc["floor"]
            if "room" in doc:
                location.room = doc["room"]
            if "zone" in doc:
                location.zone = doc["zone"]
            if "order" in doc:
                location.order = doc["order"]
            db.session.commit()

        cache.delete("locations_list_postgres")

    def update_order(self, loc_id, order: int) -> None:
        location = db.session.query(Location).filter_by(id=loc_id).first()
        if location:
            location.order = order
            db.session.commit()

        cache.delete("locations_list_postgres")

    def list_choices(self) -> tuple:
        from app.models import Item

        floors = [i[0] for i in db.session.query(Item.ItemFloor).distinct().filter(Item.ItemFloor != None).all()]
        rooms = [i[0] for i in db.session.query(Item.ItemRoom).distinct().filter(Item.ItemRoom != None).all()]
        zones = [i[0] for i in db.session.query(Item.ItemZone).distinct().filter(Item.ItemZone != None).all()]

        return (floors, rooms, zones)
