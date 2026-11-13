"""標準函式庫日誌：請求脈絡、JSON 格式與可重複套用的設定。"""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id.get()),
        }
        for key in ("method", "path", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_format: str, log_level: str) -> None:
    """只管理自己的 handler，保留 pytest／宿主程式既有的 handler。"""
    root = logging.getLogger()
    handler = next((h for h in root.handlers if getattr(h, "_ims_handler", False)), None)
    if handler is None:
        handler = logging.StreamHandler()
        handler._ims_handler = True
        handler.addFilter(RequestContextFilter())
        root.addHandler(handler)
    handler.setFormatter(
        JsonFormatter() if log_format == "json" else logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
        )
    )
    handler.setLevel(log_level.upper())
    root.setLevel(log_level.upper())
