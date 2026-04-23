"""OpenAPI / Swagger UI 設定。

提供：
- ``/api/openapi.json``：OpenAPI 3.0 規格 JSON。
- ``/docs``：Swagger UI 介面（若未安裝 ``flask-swagger-ui`` 則只回傳 JSON 連結）。

注意：原本的 ``api`` 藍圖在 ``app/api/routes.py`` 已存在，所以本檔的藍圖採用
不同名稱 ``api_docs``，避免在 Flask 註冊時衝突。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify


bp = Blueprint("api_docs", __name__, url_prefix="/api")


API_INFO: Dict[str, Any] = {
    "title": "物品管理系統 API",
    "version": "1.0.0",
    "description": (
        "## 物品管理系統 RESTful API\n\n"
        "### 認證\n- 使用 API Token：`Authorization: Bearer <token>`\n\n"
        "### 錯誤碼\n"
        "| Code | 說明 |\n|------|------|\n"
        "| 200 | 成功 |\n| 400 | 請求錯誤 |\n| 401 | 未認證 |\n"
        "| 403 | 無權限 |\n| 404 | 資源不存在 |\n| 500 | 伺服器錯誤 |\n"
    ),
    "contact": {"name": "API Support", "email": "support@example.com"},
    "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
}


API_SCHEMAS: Dict[str, Any] = {
    "Item": {
        "type": "object",
        "properties": {
            "ItemID": {"type": "string", "description": "物品ID"},
            "ItemName": {"type": "string", "description": "物品名稱"},
            "ItemStorePlace": {"type": "string", "description": "放置地點"},
            "ItemFloor": {"type": "string", "description": "樓層"},
            "ItemRoom": {"type": "string", "description": "房間"},
            "ItemZone": {"type": "string", "description": "區域"},
            "ItemType": {"type": "string", "description": "物品類型"},
            "ItemQuantity": {"type": "integer", "description": "數量"},
            "ItemDesc": {"type": "string", "description": "描述"},
            "ItemPic": {"type": "string", "description": "照片URL"},
            "ItemGetDate": {"type": "string", "format": "date", "description": "取得日期"},
            "WarrantyExpiry": {"type": "string", "format": "date", "description": "保固截止"},
            "UsageExpiry": {"type": "string", "format": "date", "description": "使用期限"},
            "ItemStoreMin": {"type": "integer", "description": "安全庫存"},
            "ItemStoreReorder": {"type": "integer", "description": "補貨門檻"},
            "favorite": {"type": "boolean", "description": "收藏"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    },
    "Location": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "floor": {"type": "string"},
            "room": {"type": "string"},
            "zone": {"type": "string"},
            "description": {"type": "string"},
        },
    },
    "ItemType": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "description": {"type": "string"},
        },
    },
    "Error": {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "message": {"type": "string"},
            "code": {"type": "integer"},
        },
    },
}


API_PATHS: Dict[str, Any] = {
    "/api/items": {
        "get": {
            "summary": "取得物品列表",
            "description": "可分頁與條件篩選。",
            "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer"}},
                {"name": "per_page", "in": "query", "schema": {"type": "integer"}},
                {"name": "q", "in": "query", "schema": {"type": "string"}},
                {"name": "type", "in": "query", "schema": {"type": "string"}},
                {"name": "place", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Item"},
                                    },
                                    "total": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "per_page": {"type": "integer"},
                                },
                            }
                        }
                    },
                }
            },
        },
        "post": {
            "summary": "新增物品",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Item"}
                    }
                },
            },
            "responses": {"201": {"description": "建立成功"}, "400": {"description": "請求錯誤"}},
        },
    },
    "/api/items/{id}": {
        "get": {
            "summary": "取得單一物品",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Item"}
                        }
                    },
                },
                "404": {"description": "不存在"},
            },
        },
        "put": {
            "summary": "更新物品",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Item"}
                    }
                }
            },
            "responses": {"200": {"description": "更新成功"}, "404": {"description": "不存在"}},
        },
        "delete": {
            "summary": "刪除物品",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {"200": {"description": "刪除成功"}, "404": {"description": "不存在"}},
        },
    },
    "/api/locations": {
        "get": {"summary": "取得位置列表", "responses": {"200": {"description": "成功"}}},
        "post": {"summary": "新增位置", "responses": {"201": {"description": "建立成功"}}},
    },
    "/api/types": {
        "get": {"summary": "取得類型列表", "responses": {"200": {"description": "成功"}}},
        "post": {"summary": "新增類型", "responses": {"201": {"description": "建立成功"}}},
    },
    "/api/stats": {
        "get": {
            "summary": "取得統計資料",
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "with_photo": {"type": "integer"},
                                    "with_location": {"type": "integer"},
                                    "expiring_soon": {"type": "integer"},
                                },
                            }
                        }
                    },
                }
            },
        }
    },
}


def build_spec() -> Dict[str, Any]:
    """組成完整 OpenAPI 3.0 規格。"""
    return {
        "openapi": "3.0.0",
        "info": API_INFO,
        "paths": API_PATHS,
        "components": {
            "schemas": API_SCHEMAS,
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "API Token",
                }
            },
        },
        "security": [{"bearerAuth": []}],
    }


@bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI 規格端點。"""
    return jsonify(build_spec())


def register_swagger_ui(app) -> None:
    """嘗試註冊 Swagger UI 至 ``/docs``，未安裝套件則安靜略過。"""
    try:
        from flask_swagger_ui import get_swaggerui_blueprint
    except ImportError:
        app.logger.info("flask-swagger-ui 未安裝，跳過 /docs Swagger UI。可改存取 /api/openapi.json。")
        return

    swagger_bp = get_swaggerui_blueprint(
        "/docs",
        "/api/openapi.json",
        config={"app_name": API_INFO["title"]},
    )
    # 避免與其他 blueprint 衝突，使用獨立名稱
    app.register_blueprint(swagger_bp, url_prefix="/docs", name="swagger_ui")


def init_openapi(app) -> None:
    """在 create_app 中呼叫：註冊 OpenAPI 藍圖與 Swagger UI。"""
    app.register_blueprint(bp)
    register_swagger_ui(app)
