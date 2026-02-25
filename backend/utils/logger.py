from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import contextvars
import structlog
from structlog.stdlib import LoggerFactory
from rich.logging import RichHandler
import logging.handlers

"""
Centralized structured logger for the project using structlog and rich.

Features:
- get_logger(name): returns a configured structlog logger
- init_logging(): initialize structlog with rich console and JSON file output
- request_id contextvar with helpers set_request_id/clear_request_id
- Rich console handler for beautiful terminal output
- JSON file handler with rotation for production logs
"""

# Public context var for request/correlation id
request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_logger_initialized = False


_logger_initialized = False


def set_request_id(rid: Optional[str]) -> None:
    """Set a request/correlation id for the current context."""
    request_id.set(rid)


def clear_request_id() -> None:
    """Clear the request/correlation id for the current context."""
    request_id.set(None)


def add_request_id(logger, method_name, event_dict):
    """Processor to add request_id to structlog events."""
    rid = request_id.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


class JsonFormatter(logging.Formatter):
    """JSON formatter for file logging with structlog compatibility."""

    def format(self, record: logging.LogRecord) -> str:
        # Extract structlog's event_dict if present
        event_dict = getattr(record, "event_dict", None)
        if event_dict:
            payload = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "level": record.levelname,
                "logger": record.name,
                **event_dict
            }
        else:
            # Fallback for non-structlog messages
            payload = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "funcName": record.funcName,
                "line": record.lineno,
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
        
        return json.dumps(payload, ensure_ascii=False, default=str)


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
    Initialize structlog with rich console output and JSON file logging.
    Safe to call multiple times (handlers replaced).
    
    Args:
        level: logging level (defaults to env LOG_LEVEL or INFO)
        log_dir: directory to write rotated log file
        filename: file name for logs (defaults to app.log)
        max_bytes: max file size before rotation (default 10MB)
        backup_count: number of backup files to keep
    """
    global _logger_initialized
    if _logger_initialized:
        return
    
    # Configure stdlib logging first
    root = logging.getLogger()
    
    # Remove existing handlers
    for h in list(root.handlers):
        try:
            h.close()
        except Exception:
            pass
        root.removeHandler(h)

    env_level = os.getenv("LOG_LEVEL", "INFO").upper()
    chosen_level = level if level is not None else getattr(logging, env_level, logging.INFO)
    root.setLevel(chosen_level)

    # Rich console handler for beautiful terminal output
    ch = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_level=True,
        show_path=False,
    )
    ch.setLevel(chosen_level)
    root.addHandler(ch)

    # JSON file handler for production logs
    log_dir = (Path(log_dir) if log_dir is not None else _default_log_dir())
    filename = filename or os.getenv("LOG_FILE", "app.log")
    
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
        root.addHandler(fh)
    except Exception:
        root.warning("Failed to initialize file handler for logging; continuing with console only", exc_info=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_request_id,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    _logger_initialized = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Return a configured structlog logger with the given name.
    Automatically initializes logging if not already done.
    
    Returns:
        A structlog BoundLogger instance that supports structured logging
    """
    if not _logger_initialized:
        init_logging()
    return structlog.get_logger(name)


# Convenience: module-level logger
logger = get_logger(__name__)