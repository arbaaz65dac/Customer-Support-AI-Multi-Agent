from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.request_context import request_id_context


_SAFE_FIELDS = (
    "method",
    "path",
    "status_code",
    "duration_ms",
    "intent",
    "selected_agent",
    "error_type",
    "tool_name",
    "outcome",
)


class JsonLogFormatter(logging.Formatter):
    """Emit a small, allowlisted JSON record without request contents."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "framework_log"),
            "request_id": getattr(
                record,
                "request_id",
                request_id_context.get(),
            ),
        }
        for field in _SAFE_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (str, int, float)) and not isinstance(
                value, bool
            ):
                payload[field] = value
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = JsonLogFormatter()
    if not any(
        getattr(handler, "_supports_json_logs", False)
        for handler in root_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler._supports_json_logs = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def log_event(level: int, event: str, **fields: object) -> None:
    safe_fields = {
        key: value
        for key, value in fields.items()
        if key in _SAFE_FIELDS
        and isinstance(value, (str, int, float))
        and not isinstance(value, bool)
    }
    logging.getLogger("supportsphere").log(
        level,
        event,
        extra={
            "event": event,
            "request_id": request_id_context.get(),
            **safe_fields,
        },
    )
