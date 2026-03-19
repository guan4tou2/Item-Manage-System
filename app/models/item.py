"""物品模型"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Text, JSON, Date, Integer, Numeric, Boolean, DateTime
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
    visibility: Mapped[str] = mapped_column(String(20), default="private", index=True)
    shared_with: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    Quantity: Mapped[int] = mapped_column(Integer, default=0)
    SafetyStock: Mapped[int] = mapped_column(Integer, default=0)
    ReorderLevel: Mapped[int] = mapped_column(Integer, default=0)
    WarrantyExpiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    UsageExpiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    MaintenanceCategory: Mapped[Optional[str]] = mapped_column(String(50), default="")
    MaintenanceIntervalDays: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    LastMaintenanceDate: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    move_history: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
    favorites: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    related_items: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
    size_notes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    # Feature 14: Item Condition
    condition: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="good")
    # Feature 13: Asset Depreciation
    purchase_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    current_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    depreciation_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    depreciation_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    # M18: Multi-Currency
    currency: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, default="TWD")
    # Feature 17: Multi-Location/Warehouse
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Feature 18: Location Map Visualization
    map_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    map_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Feature 21: Auto-Purchase Links
    purchase_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preferred_store: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # M6: Soft-delete / Trash
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # M10: Drag-and-drop sort order
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    # M28: Insurance Records
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_policy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

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
            "visibility": self.visibility or "private",
            "shared_with": list(self.shared_with or []),
            "Quantity": int(self.Quantity or 0),
            "SafetyStock": int(self.SafetyStock or 0),
            "ReorderLevel": int(self.ReorderLevel or 0),
            "WarrantyExpiry": self.WarrantyExpiry.strftime("%Y-%m-%d") if self.WarrantyExpiry else "",
            "UsageExpiry": self.UsageExpiry.strftime("%Y-%m-%d") if self.UsageExpiry else "",
            "MaintenanceCategory": self.MaintenanceCategory or "",
            "MaintenanceIntervalDays": self.MaintenanceIntervalDays if self.MaintenanceIntervalDays else "",
            "LastMaintenanceDate": self.LastMaintenanceDate.strftime("%Y-%m-%d") if self.LastMaintenanceDate else "",
            "move_history": list(self.move_history or []),
            "favorites": list(self.favorites or []),
            "related_items": list(self.related_items or []),
            "size_notes": self.size_notes or {},
            "condition": self.condition or "good",
            "purchase_price": float(self.purchase_price) if self.purchase_price is not None else None,
            "current_value": float(self.current_value) if self.current_value is not None else None,
            "depreciation_method": self.depreciation_method or "",
            "depreciation_rate": float(self.depreciation_rate) if self.depreciation_rate is not None else None,
            "currency": self.currency or "TWD",
            "warehouse_id": self.warehouse_id,
            "map_x": self.map_x,
            "map_y": self.map_y,
            "purchase_url": self.purchase_url or "",
            "preferred_store": self.preferred_store or "",
            "is_deleted": bool(self.is_deleted),
            "deleted_at": self.deleted_at.strftime("%Y-%m-%d %H:%M:%S") if self.deleted_at else None,
            "sort_order": int(self.sort_order or 0),
            "insurance_provider": self.insurance_provider or "",
            "insurance_policy": self.insurance_policy or "",
            "insurance_expiry": self.insurance_expiry.strftime("%Y-%m-%d") if self.insurance_expiry else "",
        }

    def __repr__(self) -> str:
        return f"<Item {self.ItemID}: {self.ItemName}>"
