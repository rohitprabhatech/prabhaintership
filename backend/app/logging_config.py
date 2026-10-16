import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        event = getattr(record, "event", None)
        if event:
            payload["event"] = event
        exception_type = getattr(record, "exception_type", None)
        if exception_type:
            payload["exception_type"] = exception_type
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)