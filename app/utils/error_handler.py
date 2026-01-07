"""錯誤處理和結構化日誌模組"""
import logging
import traceback
from typing import Dict, Any
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from datetime import datetime

# 配置結構化日誌
logger = logging.getLogger(__name__)


class AppError(Exception):
    """應用程式自定義錯誤基類"""
    def __init__(self, message: str, status_code: int = 500, payload: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


class DatabaseError(AppError):
    """數據庫錯誤"""
    pass


class ValidationError(AppError):
    """驗證錯誤"""
    pass


class NotFoundError(AppError):
    """資源未找到錯誤"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


def init_error_handlers(app: Flask) -> None:
    """初始化全局錯誤處理器"""

    @app.errorhandler(404)
    def not_found(error):
        return handle_error(error)

    @app.errorhandler(500)
    def internal_error(error):
        return handle_error(error)

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return handle_error(error)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error(
            "Unexpected error",
            extra={
                "type": type(error).__name__,
                "message": str(error),
                "path": request.path,
                "method": request.method,
                "ip": request.remote_addr,
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_exc()
            }
        )
        response = {
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
        return jsonify(response), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return handle_error(error)


def handle_error(error: Exception) -> Dict[str, Any]:
    """統一錯誤處理並記錄結構化日誌"""
    if isinstance(error, AppError):
        status_code = error.status_code
        message = error.message
        error_type = type(error).__name__
    else:
        status_code = getattr(error, 'code', 500)
        message = str(error)
        error_type = type(error).__name__

    # 記錄錯誤日誌
    log_data = {
        "type": error_type,
        "message": message,
        "path": request.path if request else None,
        "method": request.method if request else None,
        "ip": request.remote_addr if request else None,
        "timestamp": datetime.now().isoformat(),
        "status_code": status_code
    }

    if isinstance(error, (DatabaseError, Exception)):
        log_data["traceback"] = traceback.format_exc()

    logger.error(
        message,
        extra={
            **log_data,
            "error_data": {
                "type": error_type,
                "message": message
            }
        }
    )

    # 構建回應
    response = {
        "success": False,
        "error": error_type,
        "message": message
    }

    if hasattr(error, 'payload'):
        response["data"] = error.payload

    return jsonify(response), status_code


def log_info(message: str, extra: Dict[str, Any] = None) -> None:
    """記錄資訊級別日誌"""
    logger.info(
        message,
        extra={
            **(extra or {}),
            "timestamp": datetime.now().isoformat(),
            "service": "item-manage-system"
        }
    )


def log_warning(message: str, extra: Dict[str, Any] = None) -> None:
    """記錄警告級別日誌"""
    logger.warning(
        message,
        extra={
            **(extra or {}),
            "timestamp": datetime.now().isoformat(),
            "service": "item-manage-system"
        }
    )


def log_error(message: str, extra: Dict[str, Any] = None, exc_info=None) -> None:
    """記錄錯誤級別日誌"""
    logger.error(
        message,
        exc_info=exc_info,
        extra={
            **(extra or {}),
            "timestamp": datetime.now().isoformat(),
            "service": "item-manage-system"
        }
    )
