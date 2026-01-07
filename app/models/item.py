"""物品模型"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Text, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Item(db.Model):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    ItemID: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    ItemName: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ItemDesc: Mapped[Optional[str]] = mapped_column(Text)
    ItemPic: Mapped[Optional[str]] = mapped_column(String(255), default="")
    ItemThumb: Mapped[Optional[str]] = mapped_column(String(255), default="")
    ItemPics: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    ItemStorePlace: Mapped[Optional[str]] = mapped_column(String(255), default="")
    ItemType: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    ItemOwner: Mapped[Optional[str]] = mapped_column(String(50))
    ItemGetDate: Mapped[Optional[str]] = mapped_column(String(20))
    ItemFloor: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    ItemRoom: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    ItemZone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    WarrantyExpiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    UsageExpiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    move_history: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
    favorites: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    related_items: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ItemID": self.ItemID,
            "ItemName": self.ItemName,
            "ItemDesc": self.ItemDesc or "",
            "ItemPic": self.ItemPic or "",
            "ItemThumb": self.ItemThumb or "",
            "ItemPics": list(self.ItemPics or []),
            "ItemStorePlace": self.ItemStorePlace or "",
            "ItemType": self.ItemType or "",
            "ItemOwner": self.ItemOwner or "",
            "ItemGetDate": self.ItemGetDate or "",
            "ItemFloor": self.ItemFloor or "",
            "ItemRoom": self.ItemRoom or "",
            "ItemZone": self.ItemZone or "",
            "WarrantyExpiry": self.WarrantyExpiry.strftime("%Y-%m-%d") if self.WarrantyExpiry else "",
            "UsageExpiry": self.UsageExpiry.strftime("%Y-%m-%d") if self.UsageExpiry else "",
            "move_history": list(self.move_history or []),
            "favorites": list(self.favorites or []),
            "related_items": list(self.related_items or []),
        }

    def __repr__(self) -> str:
        return f"<Item {self.ItemID}: {self.ItemName}>"

