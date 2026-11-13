"""純 ASGI 請求識別與 access log，不緩衝串流本文。"""

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id

logger = logging.getLogger("ims.access")
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}", re.ASCII)


class ObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get("x-request-id", "")
        current_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid4().hex
        token = request_id.set(current_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = current_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            try:
                if not scope["path"].startswith("/api/health"):
                    duration = round((time.perf_counter() - started) * 1000, 3)
                    logger.info(
                        "%s %s %s %.3fms", scope["method"], scope["path"], status, duration,
                        extra={"method": scope["method"], "path": scope["path"],
                               "status": status, "duration_ms": duration,
                               "request_id": current_id},
                    )
            finally:
                request_id.reset(token)
