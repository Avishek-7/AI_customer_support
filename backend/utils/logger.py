from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import contextvars

"""
Simple centralized logger for the project.

Features:
- get_logger(name): returns a configured logger
- init_logging(): initialize root logger (called on app startup)
- request_id contextvar with helpers set_request_id/clear_request_id
- console (human) and file (JSON) handlers with rotation
"""


import logging.handlers

# Public context var for request/correlation id
request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def set_request_id(rid: Optional[str]) -> None:
    """Set a request/correlation id for the current context."""
    request_id.set(rid)


def clear_request_id() -> None:
    """Clear the request/correlation id for the current context."""
    request_id.set(None)


class RequestIDFilter(logging.Filter):
    """Attach the current request_id (if any) to every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Basic JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", None),
        }
        # include exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # include any extra keys passed in the logging call
        for k, v in record.__dict__.items():
            if k not in ("name", "msg", "args", "levelname", "levelno", "pathname",
                         "filename", "module", "exc_info", "exc_text", "stack_info",
                         "lineno", "funcName", "created", "msecs", "relativeCreated",
                         "thread", "threadName", "processName", "process", "message",
                         "request_id"):
                try:
                    json.dumps({k: v})  # test serializability
                    payload[k] = v
                except Exception:
                    payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)


def _default_log_dir() -> Path:
    # If project structure is .../project/backend/utils/logger.py -> root = two parents up
    return Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[2] / "logs"))


def init_logging(
    *,
    level: Optional[int] = None,
    log_dir: Optional[Path] = None,
    filename: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Initialize the root logger. Safe to call multiple times (handlers replaced).
    - level: logging level (defaults to env LOG_LEVEL or INFO)
    - log_dir: directory to write rotated log file
    - filename: file name for logs (defaults to app.log)
    """
    root = logging.getLogger()
    # Remove existing handlers to avoid duplicate logs if init called multiple times
    for h in list(root.handlers):
        root.removeHandler(h)

    env_level = os.getenv("LOG_LEVEL", "INFO").upper()
    chosen_level = level if level is not None else getattr(logging, env_level, logging.INFO)
    root.setLevel(chosen_level)

    request_filter = RequestIDFilter()

    # Console handler (human readable)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(chosen_level)
    console_fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s%(request_id_part)s"
    # Using a small wrapper Formatter to inject request_id_part into message
    class ConsoleFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            rid = getattr(record, "request_id", None)
            record.request_id_part = f" [request_id={rid}]" if rid else ""
            return super().format(record)

    ch.setFormatter(ConsoleFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s%(request_id_part)s", "%Y-%m-%d %H:%M:%S"))
    ch.addFilter(request_filter)
    root.addHandler(ch)

    # File handler (JSON)
    log_dir = (Path(log_dir) if log_dir is not None else _default_log_dir())
    filename = filename or os.getenv("LOG_FILE", "app.log")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(str(log_dir / filename), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setLevel(chosen_level)
        fh.setFormatter(JsonFormatter())
        fh.addFilter(request_filter)
        root.addHandler(fh)
    except Exception:
        # If file logging fails (e.g., permission), continue with console only
        root.warning("Failed to initialize file handler for logging; continuing with console only", exc_info=True)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger with the given name. Ensure init_logging() has been called.
    """
    if not logging.getLogger().handlers:
        init_logging()
    return logging.getLogger(name)


# Convenience: module-level logger
logger = get_logger(__name__)