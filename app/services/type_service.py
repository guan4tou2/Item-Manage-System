from typing import List, Dict, Any

from app.repositories import type_repo


def list_types() -> List[Dict[str, Any]]:
    return list(type_repo.list_types())


def create_type(data: Dict[str, Any]) -> None:
    type_repo.insert_type(data["name"])

