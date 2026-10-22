from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ItemLabel(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    deep_link: str
    barcode: Optional[str] = None


class LocationLabel(BaseModel):
    """位置標籤資料（Phase 36）：貼在櫃子／箱子的 QR 標籤。"""

    location_id: int
    name: str
    #: 完整路徑（如 `1F / 廚房 / 藥箱`）
    path: str
    #: 含子孫的物品數（與清單篩選結果一致）
    item_count: int
    #: 深連結：導向該位置（含子孫）的物品清單
    deep_link: str
