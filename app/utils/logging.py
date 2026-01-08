"""Application logging configuration."""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False,
    service_name: str = "item-manage-system"
) -> None:
    """
    Configure comprehensive logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        json_logs: If True, use JSON formatted logs for production
        service_name: Name of the service for log identification
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create logs directory if file logging is enabled
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Set up structlog
    if json_logs:
        # Production: JSON structured logs
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Human-readable logs
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Add file handler if log file is specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)

        if json_logs:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        file_handler.setFormatter(formatter)

        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    configure_logger_levels()


def configure_logger_levels() -> None:
    """Configure logging levels for specific third-party libraries."""
    # Suppress verbose logging from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    # Enable debug logging for application modules in development
    if os.getenv("FLASK_ENV") != "production":
        logging.getLogger("app").setLevel(logging.DEBUG)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for a module.

    Args:
        name: Name of the module (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LoggingMiddleware:
    """Middleware to add request logging to Flask applications."""

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")

    def __call__(self, environ, start_response):
        """Log HTTP requests."""
        import time
        from flask import request

        # Log request start
        self.logger.info(
            "request_started",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
        )

        start_time = time.time()

        def custom_start_response(status, headers, exc_info=None):
            # Log request completion
            duration = time.time() - start_time
            self.logger.info(
                "request_completed",
                status=status.split()[0],
                duration_ms=round(duration * 1000, 2),
            )
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)


def init_flask_logging(app):
    """
    Initialize logging for Flask application.

    Args:
        app: Flask application instance
    """
    # Get configuration
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", None)
    json_logs = os.getenv("FLASK_ENV") == "production"

    # Setup logging
    setup_logging(
        level=log_level,
        log_file=log_file,
        json_logs=json_logs,
    )

    # Add request logging middleware in development
    if os.getenv("FLASK_ENV") != "production":
        app.wsgi_app = LoggingMiddleware(app.wsgi_app)

    # Log application startup
    logger = get_logger("app")
    logger.info(
        "application_started",
        environment=os.getenv("FLASK_ENV", "development"),
        log_level=log_level,
        json_logs=json_logs,
        log_file=log_file,
    )

    return logger
