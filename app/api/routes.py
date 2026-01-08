"""API documentation using Swagger (flasgger)"""
from flask import Blueprint

bp = Blueprint("api", __name__)


@bp.route("/api/docs", methods=["GET"])
def api_docs():
    """
    Swagger UI endpoint for API documentation

    Provides interactive API documentation using flasgger.
    Requires: flasgger>=0.3.7.0
    """
    from flasgger import swag_from_yaml

    from app import app

    try:
        # Try to import flasgger
        swagger_config = {
            "headers": [],
            "specs": [
                {
                    "version": "1.0.0",
                    "title": "物品管理系統 API",
                    "description": "物品管理系統的 RESTful API 接口文檔",
                    "host": "localhost:8080",
                    "basePath": "/api",
                    "schemes": ["http", "https"],
                    "consumes": ["application/json"],
                    "produces": ["application/json"],
                    "securityDefinitions": {
                        "BearerAuth": {
                            "type": "apiKey",
                            "name": "Authorization",
                            "in": "header"
                        }
                    },
                    "paths": {
                        "/items": {
                            "get": {
                                "tags": ["items"],
                                "summary": "獲取物品列表",
                                "description": "根據過濾條件分頁獲取所有物品",
                                "parameters": [
                                    {
                                        "name": "page",
                                        "in": "query",
                                        "type": "integer",
                                        "description": "頁碼（從 1 �始）",
                                        "default": 1,
                                        "minimum": 1
                                    },
                                    {
                                        "name": "limit",
                                        "in": "query",
                                        "type": "integer",
                                        "description": "每頁數量",
                                        "default": 20,
                                        "minimum": 1,
                                        "maximum": 100
                                    },
                                    {
                                        "name": "ItemName",
                                        "in": "query",
                                        "type": "string",
                                        "description": "按物品名稱模糊搜索"
                                    },
                                    {
                                        "name": "ItemType",
                                        "in": "query",
                                        "type": "string",
                                        "description": "按物品類型過濾"
                                    }
                                ],
                                "responses": {
                                    "200": {
                                        "description": "成功",
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "ItemID": {
                                                            "type": "string",
                                                            "description": "物品 ID"
                                                        },
                                                        "ItemName": {
                                                            "type": "string",
                                                            "description": "物品名稱"
                                                        },
                                                        "ItemType": {
                                                            "type": "string",
                                                            "description": "物品類型"
                                                        },
                                                        "ItemPic": {
                                                            "type": "string",
                                                            "description": "物品照片 URL"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                            "post": {
                                "tags": ["items"],
                                "summary": "新增物品",
                                "description": "創建新的物品",
                                "parameters": [
                                    {
                                        "name": "body",
                                        "in": "body",
                                        "required": True,
                                        "description": "物品資訊",
                                        "schema": {
                                            "type": "object",
                                            "required": ["ItemID", "ItemName"],
                                            "properties": {
                                                "ItemID": {
                                                    "type": "string",
                                                    "description": "物品 ID"
                                                },
                                                "ItemName": {
                                                    "type": "string",
                                                    "description": "物品名稱"
                                                }
                                            }
                                        }
                                    }
                                },
                                "put": {
                                    "tags": ["items"],
                                    "summary": "更新物品",
                                    "description": "更新指定物品的資訊",
                                },
                                "delete": {
                                    "tags": ["items"],
                                    "summary": "刪除物品",
                                    "description": "刪除指定物品"
                                }
                            }
                        },
                        "/types": {
                            "get": {
                                "tags": ["types"],
                                "summary": "獲取類型列表",
                                "responses": {
                                    "200": {
                                        "description": "成功",
                                        "schema": {
                                            "type": "array",
                                            "types": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "integer",
                                                            "description": "類型 ID"
                                                        },
                                                        "name": {
                                                            "type": "string",
                                                            "description": "類型名稱"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                                "post": {
                                    "tags": ["types"],
                                    "summary": "新增類型",
                                    "parameters": [
                                        {
                                            "name": "name",
                                            "in": "body",
                                            "required": True,
                                            "type": "string",
                                            "description": "類型名稱"
                                        }
                                    ]
                                },
                                "delete": {
                                    "tags": ["types"],
                                    "summary": "刪除類型",
                                    "parameters": [
                                        {
                                            "name": "name",
                                            "in": "path",
                                            "type": "string",
                                            "description": "類型名稱"
                                        }
                                    ]
                                }
                            },
                        "/locations": {
                            "get": {
                                "tags": ["locations"],
                                "summary": "獲取位置列表",
                                "responses": {
                                    "200": {
                                        "description": "成功",
                                        "schema": {
                                            "type": "array",
                                            "locations": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "integer",
                                                            "description": "位置 ID"
                                                        },
                                                        "floor": {
                                                            "type": "string",
                                                            "description": "樓層"
                                                        },
                                                        "room": {
                                                            "type": "string",
                                                            "description": "房間"
                                                        },
                                                        "zone": {
                                                            "type": "string",
                                                            "description": "區域"
                                                        },
                                                        "order": {
                                                            "type": "integer",
                                                            "description": "排序"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                    },
                    "security": [
                        {
                            "BearerAuth": {
                                "type": "apiKey",
                                "name": "Authorization",
                                "description": "JWT 或 Session Token",
                                "in": "header"
                            }
                        }
                    ]
                }
            }
        }

        return swagger_config

    except ImportError:
        return {
            "info": "flasgger 未安裝。要使用 API 文檔功能，請安裝：",
            "flasgger_install": "pip install flasgger==0.3.7.0",
            "alternative": "使用手動的 JSON 文檔記錄或改用 OpenAPI"
        }, 404


@bp.route("/api/health", methods=["GET"])
def api_health():
    """
    API health check endpoint

    Simple health check specifically for API functionality.
    """
    from flask import jsonify

    try:
        # Check if flasgger is available
        from flasgger import swag_from_yaml
        swag = swag_from_yaml({
            "swagger": "2.0",
            "info": {
                "version": "1.0.0",
                "title": "API Health",
                "description": "API 健康檢查"
            }
        })
        return jsonify({"status": "healthy", "version": "1.0.0"}), 200
    except ImportError:
        return jsonify({"status": "flasgger not available"}), 404


__all__ = ["api_docs", "api_health"]
