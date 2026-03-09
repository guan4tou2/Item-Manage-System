"""API documentation endpoints."""

from flask import Blueprint, jsonify

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


__all__ = ["api_docs", "api_health"]
