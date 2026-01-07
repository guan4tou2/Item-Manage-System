"""Repository factory for creating database-specific repositories"""
from typing import Optional

from app.repositories.base import BaseRepository, TypeRepository, LocationRepository
from app.repositories.postgres_impl import (
    PostgresItemRepository,
    PostgresTypeRepository,
    PostgresLocationRepository
)
from app.repositories.mongo_impl import (
    MongoItemRepository,
    MongoTypeRepository,
    MongoLocationRepository
)


def get_item_repository(db_type: str) -> BaseRepository:
    """Factory function to get appropriate item repository

    Args:
        db_type: Database type ('postgres' or 'mongo')

    Returns:
        Appropriate repository implementation
    """
    if db_type == "postgres":
        return PostgresItemRepository()
    return MongoItemRepository()


def get_type_repository(db_type: str) -> TypeRepository:
    """Factory function to get appropriate type repository

    Args:
        db_type: Database type ('postgres' or 'mongo')

    Returns:
        Appropriate repository implementation
    """
    if db_type == "postgres":
        return PostgresTypeRepository()
    return MongoTypeRepository()


def get_location_repository(db_type: str) -> LocationRepository:
    """Factory function to get appropriate location repository

    Args:
        db_type: Database type ('postgres' or 'mongo')

    Returns:
        Appropriate repository implementation
    """
    if db_type == "postgres":
        return PostgresLocationRepository()
    return MongoLocationRepository()


__all__ = [
    "get_item_repository",
    "get_type_repository",
    "get_location_repository"
]
