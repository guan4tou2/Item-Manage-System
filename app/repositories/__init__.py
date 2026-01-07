"""Repositories module with factory pattern for dual database support"""

from .base import BaseRepository, TypeRepository, LocationRepository
from .factory import get_item_repository, get_type_repository, get_location_repository
from .postgres_impl import PostgresItemRepository, PostgresTypeRepository, PostgresLocationRepository
from .mongo_impl import MongoItemRepository, MongoTypeRepository, MongoLocationRepository

# Legacy exports for backward compatibility
from .item_repo import (
    list_items,
    insert_item,
    update_item_by_id,
    find_item_by_id,
    delete_item_by_id,
    ensure_indexes,
    get_stats,
    get_all_items_for_export,
    toggle_favorite,
    get_favorites,
    is_favorite,
    add_move_history,
    add_related_item,
    remove_related_item,
    update_item_field,
    get_expiring_items,
)
from .type_repo import list_types, insert_type
from .user_repo import find_by_username, insert_user
from .location_repo import list_locations
from .log_repo import insert_log, list_logs, count_logs, get_item_logs, ensure_indexes

__all__ = [
    # Factory functions
    "get_item_repository",
    "get_type_repository",
    "get_location_repository",
    # Base classes
    "BaseRepository",
    "TypeRepository",
    "LocationRepository",
    # PostgreSQL implementations
    "PostgresItemRepository",
    "PostgresTypeRepository",
    "PostgresLocationRepository",
    # MongoDB implementations
    "MongoItemRepository",
    "MongoTypeRepository",
    "MongoLocationRepository",
    # Legacy exports
    "item_repo",
    "type_repo",
    "user_repo",
    "location_repo",
    "log_repo",
    "list_items",
    "insert_item",
    "update_item_by_id",
    "find_item_by_id",
    "delete_item_by_id",
    "ensure_indexes",
    "get_stats",
    "get_all_items_for_export",
    "toggle_favorite",
    "get_favorites",
    "is_favorite",
    "add_move_history",
    "add_related_item",
    "remove_related_item",
    "update_item_field",
    "get_expiring_items",
    "list_types",
    "insert_type",
    "find_by_username",
    "insert_user",
    "list_locations",
    "insert_log",
    "list_logs",
    "count_logs",
    "get_item_logs",
    "ensure_indexes",
]

