from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from starlette.responses import JSONResponse

from app.core.request_context import request_id_context
from app.core.structured_logging import log_event


class RequestIdMiddleware:
    """Attach an untrusted-input-independent ID to every HTTP request."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        token = request_id_context.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: dict) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                headers = list(message.get("headers", []))
                headers = [
                    (name, value)
                    for name, value in headers
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            logging.getLogger(__name__).error(
                "request_unhandled_exception",
                extra={
                    "event": "request_unhandled_exception",
                    "error_type": type(exc).__name__,
                    "request_id": request_id,
                },
            )
            if not response_started:
                response = JSONResponse(
                    status_code=500,
                    content={
                        "detail": "An unexpected error occurred.",
                        "request_id": request_id,
                    },
                )
                await response(scope, receive, send_with_request_id)
        finally:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_event(
                logging.INFO,
                "http_request_completed",
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status_code=status_code,
                duration_ms=elapsed_ms,
            )
            if status_code == 401:
                log_event(
                    logging.WARNING,
                    "auth_failure",
                    path=scope.get("path", ""),
                )
            request_id_context.reset(token)
