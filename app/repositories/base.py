"""Repository base class"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator


class BaseRepository(ABC):
    """Base repository interface

    All repositories must implement this interface to ensure
    consistent data access patterns across different database backends.
    """

    @abstractmethod
    def find_by_id(self, item_id: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Find item by ID"""
        pass

    @abstractmethod
    def insert(self, item: Dict[str, Any]) -> None:
        """Insert new item"""
        pass

    @abstractmethod
    def update(self, item_id: str, updates: Dict[str, Any]) -> None:
        """Update item by ID"""
        pass

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Delete item by ID"""
        pass

    @abstractmethod
    def list_all(
        self,
        filter_query: Dict[str, Any],
        sort: Optional[List[tuple]] = None,
        skip: int = 0,
        limit: int = 0
    ) -> List[Dict[str, Any]]:
        """List items with filtering, sorting, pagination"""
        pass

    @abstractmethod
    def count(self, filter_query: Dict[str, Any]) -> int:
        """Count items matching filter"""
        pass


class TypeRepository(ABC):
    """Type repository interface"""

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """List all types"""
        pass

    @abstractmethod
    def insert(self, name: str) -> None:
        """Insert new type"""
        pass

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete type by name"""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find type by name"""
        pass


class LocationRepository(ABC):
    """Location repository interface"""

    @abstractmethod
    def list_all(self) -> Generator[Dict[str, Any], None, None]:
        """List all locations"""
        pass

    @abstractmethod
    def insert(self, doc: Dict[str, Any]) -> None:
        """Insert new location"""
        pass

    @abstractmethod
    def delete(self, loc_id) -> None:
        """Delete location by ID"""
        pass

    @abstractmethod
    def update(self, loc_id, doc: Dict[str, Any]) -> None:
        """Update location by ID"""
        pass

    @abstractmethod
    def update_order(self, loc_id, order: int) -> None:
        """Update location order"""
        pass

    @abstractmethod
    def list_choices(self) -> tuple:
        """Get floor, room, zone choices"""
        pass
