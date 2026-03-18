from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app import db

class ItemLoan(db.Model):
    __tablename__ = "item_loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_name: Mapped[str] = mapped_column(String(200), default="")
    borrower: Mapped[str] = mapped_column(String(100))
    borrower_contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lent_date: Mapped[date] = mapped_column(Date)
    expected_return: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_return: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, returned, overdue
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lent_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "item_id": self.item_id, "item_name": self.item_name,
            "borrower": self.borrower, "borrower_contact": self.borrower_contact,
            "lent_date": str(self.lent_date) if self.lent_date else "",
            "expected_return": str(self.expected_return) if self.expected_return else "",
            "actual_return": str(self.actual_return) if self.actual_return else "",
            "status": self.status, "notes": self.notes, "lent_by": self.lent_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        }
