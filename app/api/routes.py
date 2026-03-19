"""API documentation and RESTful endpoints."""

from flask import Blueprint, jsonify, request, g

from app.utils.auth import api_token_or_login_required

bp = Blueprint("api", __name__)


def _swagger_spec() -> dict:
    return {
        "specs": [
            {
                "version": "1.0.0",
                "title": "物品管理系統 API",
                "description": "物品管理系統的 RESTful API 接口文檔",
                "securityDefinitions": {
                    "BearerAuth": {
                        "type": "apiKey",
                        "name": "Authorization",
                        "in": "header",
                    }
                },
                "paths": {
                    "/items": {"get": {"summary": "獲取物品列表"}},
                    "/types": {"get": {"summary": "獲取類型列表"}},
                    "/locations": {"get": {"summary": "獲取位置列表"}},
                },
            }
        ]
    }


@bp.route("/api/docs", methods=["GET"])
def api_docs():
    """Swagger-like API docs endpoint."""
    try:
        from flasgger import swag_from_yaml  # noqa: F401
        return _swagger_spec()
    except ImportError:
        return {
            "info": "flasgger 未安裝。要使用 API 文檔功能，請安裝：",
            "flasgger_install": "pip install flasgger==0.3.7.0",
            "alternative": "使用手動的 JSON 文檔記錄或改用 OpenAPI",
        }, 404


@bp.route("/api/health", methods=["GET"])
def api_health():
    """API health check endpoint."""
    try:
        from flasgger import swag_from_yaml  # noqa: F401
        return jsonify({"status": "healthy", "version": "1.0.0"}), 200
    except ImportError:
        return jsonify({"status": "flasgger not available"}), 404


@bp.route("/api/v1/items", methods=["GET"])
@api_token_or_login_required
def api_v1_list_items():
    """List items (RESTful). Supports q, page, page_size params."""
    from app.services import item_service

    q = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(100, max(1, request.args.get("page_size", 20, type=int)))

    filters = {"q": q}
    result = item_service.list_items(filters, page=page, page_size=page_size)

    items = result.get("items", [])
    return jsonify({
        "items": items,
        "total": result.get("total", len(items)),
        "page": page,
        "page_size": page_size,
    })


@bp.route("/api/v1/items/<item_id>", methods=["GET"])
@api_token_or_login_required
def api_v1_get_item(item_id: str):
    """Get a single item by ItemID."""
    from app.services import item_service

    item = item_service.get_item(item_id)
    if not item:
        return jsonify({"error": "找不到物品"}), 404
    return jsonify(item)


__all__ = ["api_docs", "api_health", "api_v1_list_items", "api_v1_get_item"]
