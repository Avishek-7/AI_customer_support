"""
Centralized structured logger for the backend using structlog.

Features:
- get_logger(name): returns a configured structlog logger
- init_logging(): initializes structlog with console + JSON file output
- request_id contextvar with helpers set_request_id/clear_request_id
"""

from __future__ import annotations

import contextvars
import logging
import logging.handlers
import os
import threading
from pathlib import Path
from typing import Optional

import structlog
from structlog.stdlib import LoggerFactory, ProcessorFormatter

try:
    from rich.logging import RichHandler
except ImportError:  # Optional dev dependency
    RichHandler = None

# Public context var for request/correlation id
request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_logger_initialized = False
_logger_init_lock = threading.RLock()


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


def _default_log_dir() -> Path:
    # If project structure is .../project/backend/utils/logger.py -> root = two parents up
    return Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[2] / "logs"))


def _build_pre_chain() -> list:
    return [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def _is_production() -> bool:
    value = os.getenv("ENV", "development").lower()
    return value in {"production", "prod"}


def init_logging(
    *,
    level: Optional[int] = None,
    log_dir: Optional[Path] = None,
    filename: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Initialize structlog with console output and JSON file logging.
    Subsequent calls are a no-op once initialized.

    Args:
        level: logging level (defaults to env LOG_LEVEL or INFO)
        log_dir: directory to write rotated log file
        filename: file name for logs (defaults to app.log)
        max_bytes: max file size before rotation (default 10MB)
        backup_count: number of backup files to keep
    """
    global _logger_initialized
    with _logger_init_lock:
        if _logger_initialized:
            return

        root = logging.getLogger()
        for handler in list(root.handlers):
            try:
                handler.close()
            except Exception:
                pass
            root.removeHandler(handler)

        env_level = os.getenv("LOG_LEVEL", "INFO").upper()
        chosen_level = level if level is not None else getattr(logging, env_level, logging.INFO)
        root.setLevel(chosen_level)

        pre_chain = _build_pre_chain()

        if _is_production():
            console_renderer = structlog.processors.JSONRenderer()
        else:
            console_renderer = structlog.dev.ConsoleRenderer(colors=True)

        console_formatter = ProcessorFormatter(
            processor=console_renderer,
            foreign_pre_chain=pre_chain,
        )
        json_formatter = ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=pre_chain,
        )

        if RichHandler is not None and not _is_production():
            console_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=False,
                show_level=False,
                show_path=False,
            )
        else:
            console_handler = logging.StreamHandler()

        console_handler.setLevel(chosen_level)
        console_handler.setFormatter(console_formatter)
        root.addHandler(console_handler)

        log_dir = (Path(log_dir) if log_dir is not None else _default_log_dir())
        filename = filename or os.getenv("LOG_FILE", "app.log")

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_dir / filename),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(chosen_level)
            file_handler.setFormatter(json_formatter)
            root.addHandler(file_handler)
        except Exception:
            root.warning("Failed to initialize file handler for logging; continuing with console only", exc_info=True)

        structlog.configure(
            processors=[
                *pre_chain,
                ProcessorFormatter.wrap_for_formatter,
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
        with _logger_init_lock:
            if not _logger_initialized:
                init_logging()
    return structlog.get_logger(name)


