from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import contextvars
import logging.handlers

"""
Centralized logger for the AI Engine.

Features:
- get_logger(name): returns a configured logger
- init_logging(): initialize root logger (called on app startup)
- request_id contextvar for tracking requests across async calls
- console (human-readable) and file (JSON) handlers with rotation
"""

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
    """JSON formatter for structured logs."""

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
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Include extra keys passed in logging call
        for k, v in record.__dict__.items():
            if k not in ("name", "msg", "args", "levelname", "levelno", "pathname",
                         "filename", "module", "exc_info", "exc_text", "stack_info",
                         "lineno", "funcName", "created", "msecs", "relativeCreated",
                         "thread", "threadName", "processName", "process", "message",
                         "request_id"):
                try:
                    json.dumps({k: v})
                    payload[k] = v
                except Exception:
                    payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with optional request_id."""
    
    def format(self, record: logging.LogRecord) -> str:
        rid = getattr(record, "request_id", None)
        record.request_id_part = f" [req={rid}]" if rid else ""
        return super().format(record)


def _default_log_dir() -> Path:
    """Default log directory: ai_engine/logs"""
    return Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[1] / "logs"))


def init_logging(
    *,
    level: Optional[int] = None,
    log_dir: Optional[Path] = None,
    filename: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Initialize the root logger. Safe to call multiple times.
    
    Args:
        level: logging level (defaults to env LOG_LEVEL or INFO)
        log_dir: directory to write rotated log file
        filename: file name for logs (defaults to ai_engine.log)
        max_bytes: max file size before rotation (default 10MB)
        backup_count: number of backup files to keep
    """
    root = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for h in list(root.handlers):
        root.removeHandler(h)

    env_level = os.getenv("LOG_LEVEL", "INFO").upper()
    chosen_level = level if level is not None else getattr(logging, env_level, logging.INFO)
    root.setLevel(chosen_level)

    request_filter = RequestIDFilter()

    # Console handler (human readable)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(chosen_level)
    ch.setFormatter(ConsoleFormatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s%(request_id_part)s",
        "%Y-%m-%d %H:%M:%S"
    ))
    ch.addFilter(request_filter)
    root.addHandler(ch)

    # File handler (JSON, with rotation)
    log_dir = Path(log_dir) if log_dir is not None else _default_log_dir()
    filename = filename or os.getenv("LOG_FILE", "ai_engine.log")
    
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            str(log_dir / filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        fh.setLevel(chosen_level)
        fh.setFormatter(JsonFormatter())
        fh.addFilter(request_filter)
        root.addHandler(fh)
    except Exception:
        root.warning("Failed to initialize file handler; continuing with console only", exc_info=True)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger with the given name.
    Automatically initializes logging if not already done.
    """
    if not logging.getLogger().handlers:
        init_logging()
    return logging.getLogger(name)


# Module-level logger
logger = get_logger(__name__)
