from typing import List, Dict, Any

from app.repositories import type_repo

DEFAULT_TYPE_NAMES = [
    "文具",
    "工具",
    "電子產品",
    "3C配件",
    "家電",
    "廚房用品",
    "餐具",
    "食品",
    "飲品",
    "藥品",
    "保健食品",
    "清潔用品",
    "衛浴用品",
    "美妝保養",
    "衣物",
    "鞋類",
    "寢具",
    "收納用品",
    "書籍",
    "文件證件",
    "玩具",
    "寵物用品",
    "嬰幼兒用品",
    "園藝用品",
    "車用用品",
    "五金耗材",
    "急救防災",
]


def _ensure_default_types(existing_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    existing_names = {str(t.get("name", "")).strip() for t in existing_types if t.get("name")}
    missing_names = [name for name in DEFAULT_TYPE_NAMES if name not in existing_names]

    for name in missing_names:
        type_repo.insert_type(name)

    if missing_names:
        return list(type_repo.list_types())
    return existing_types


def list_types() -> List[Dict[str, Any]]:
    return _ensure_default_types(list(type_repo.list_types()))


def create_type(data: Dict[str, Any]) -> None:
    type_repo.insert_type(data["name"])
