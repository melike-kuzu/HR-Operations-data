from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import Any

from workforce_assistant.config.settings import settings


_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render log records as JSON for local and cloud monitoring."""

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.environment,
            "application": settings.app_name,
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_FIELDS:
                continue

            payload[key] = self._serialise_value(value)

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _serialise_value(value: Any) -> Any:
        if isinstance(
            value,
            (str, int, float, bool, type(None)),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(key): JsonFormatter._serialise_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                JsonFormatter._serialise_value(item)
                for item in value
            ]

        return str(value)


def _create_formatter() -> logging.Formatter:
    if settings.log_format == "json":
        return JsonFormatter()

    return logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        )
    )


def configure_logging() -> None:
    """Configure application logging once per process."""

    root_logger = logging.getLogger()

    if getattr(
        root_logger,
        "_workforce_logging_configured",
        False,
    ):
        return

    log_level = getattr(
        logging,
        settings.log_level,
        logging.INFO,
    )

    formatter = _create_formatter()

    stream_handler = logging.StreamHandler(
        sys.stdout
    )
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(stream_handler)

    if settings.enable_file_logging:
        settings.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_handler = RotatingFileHandler(
            filename=(
                settings.log_dir
                / "workforce-assistant.log"
            ),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    root_logger._workforce_logging_configured = True

    logging.getLogger(__name__).info(
        "Application logging configured",
        extra={
            "event_type": "application_startup",
            "log_format": settings.log_format,
            "log_level": settings.log_level,
            "file_logging_enabled": (
                settings.enable_file_logging
            ),
        },
    )
