from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Text, JSON, Integer, Date, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Travel(db.Model):
    __tablename__ = "travels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    owner: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
    shared: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    groups: Mapped[List["TravelGroup"]] = relationship("TravelGroup", back_populates="travel", cascade="all, delete-orphan")
    items: Mapped[List["TravelItem"]] = relationship("TravelItem", back_populates="travel", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Travel {self.id} {self.name}>"


class TravelGroup(db.Model):
    __tablename__ = "travel_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    travel_id: Mapped[int] = mapped_column(ForeignKey("travels.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    travel: Mapped[Travel] = relationship("Travel", back_populates="groups")
    items: Mapped[List["TravelItem"]] = relationship("TravelItem", back_populates="group")

    def __repr__(self) -> str:
        return f"<TravelGroup {self.id} {self.name}>"


class TravelItem(db.Model):
    __tablename__ = "travel_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    travel_id: Mapped[int] = mapped_column(ForeignKey("travels.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("travel_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(20), default="temp")
    source_ref: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    qty_required: Mapped[int] = mapped_column(Integer, default=1)
    qty_packed: Mapped[int] = mapped_column(Integer, default=0)
    carried: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    size_notes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    is_temp: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    travel: Mapped[Travel] = relationship("Travel", back_populates="items")
    group: Mapped[Optional[TravelGroup]] = relationship("TravelGroup", back_populates="items")

    def __repr__(self) -> str:
        return f"<TravelItem {self.id} {self.name}>"


class ShoppingList(db.Model):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_type: Mapped[str] = mapped_column(String(20), default="general")
    travel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("travels.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
    shared: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    items: Mapped[List["ShoppingItem"]] = relationship("ShoppingItem", back_populates="shopping_list", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ShoppingList {self.id} {self.title}>"


class ShoppingItem(db.Model):
    __tablename__ = "shopping_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    store: Mapped[Optional[str]] = mapped_column(String(120))
    link: Mapped[Optional[str]] = mapped_column(String(255))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[Optional[str]] = mapped_column(Text)
    size_notes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    shopping_list: Mapped[ShoppingList] = relationship("ShoppingList", back_populates="items")

    def __repr__(self) -> str:
        return f"<ShoppingItem {self.id} {self.name}>"
