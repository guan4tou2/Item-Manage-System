"""資料庫模型模組"""
from app.models.user import User
from app.models.item import Item
from app.models.item_type import ItemType
from app.models.log import Log
from app.models.location import Location
from app.models.travel import Travel, TravelGroup, TravelItem, ShoppingList, ShoppingItem
from app.models.line_link import LineUserLink
from app.models.telegram_link import TelegramUserLink
from app.models.quantity_log import QuantityLog
from app.models.item_loan import ItemLoan
from app.models.stocktake import StocktakeSession, StocktakeItem
from app.models.custom_field import CustomField, CustomFieldValue
from app.models.group import Group, GroupMember
from app.models.warehouse import Warehouse
from app.models.api_token import APIToken
from app.models.webhook import Webhook
from app.models.backup_config import BackupConfig
from app.models.item_version import ItemVersion
from app.models.item_template import ItemTemplate
from app.models.transfer import WarehouseTransfer
from app.models.item_transfer import ItemTransferRequest
from app.models.permission import (
    Permission,
    Role,
    can_create_items,
    can_delete_items,
    can_edit_items,
    can_manage_system,
    can_manage_users,
    get_user_role,
    has_all_permissions,
    has_any_permission,
    has_permission,
    require_permission,
    require_role,
)

__all__ = [
    "User",
    "Item",
    "ItemType",
    "Log",
    "Location",
    "Travel",
    "TravelGroup",
    "TravelItem",
    "ShoppingList",
    "ShoppingItem",
    "LineUserLink",
    "TelegramUserLink",
    "QuantityLog",
    "ItemLoan",
    "StocktakeSession",
    "StocktakeItem",
    "CustomField",
    "CustomFieldValue",
    "Group",
    "GroupMember",
    "Warehouse",
    "APIToken",
    "Webhook",
    "BackupConfig",
    "ItemVersion",
    "ItemTemplate",
    "WarehouseTransfer",
    "ItemTransferRequest",
    "Permission",
    "Role",
    "get_user_role",
    "has_permission",
    "has_any_permission",
    "has_all_permissions",
    "require_permission",
    "require_role",
    "can_create_items",
    "can_edit_items",
    "can_delete_items",
    "can_manage_users",
    "can_manage_system",
]
