"""
Logging configuration.
"""

import logging
import sys
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.config import settings


class StandardFormatter(logging.Formatter):
    """Custom formatter with the specified format."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def cleanup_old_logs(log_dir: str, retention_days: int) -> None:
    """Delete log files older than retention days."""
    if retention_days <= 0:
        return

    log_path = Path(log_dir)
    if not log_path.exists():
        return

    cutoff = datetime.now() - timedelta(days=retention_days)

    for file in log_path.glob("app.*.log"):
        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if file_mtime < cutoff:
                file.unlink()
        except Exception:
            pass


def configure_logging() -> None:
    """Configure logging with standard format."""

    handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StandardFormatter())
    handlers.append(console_handler)

    if settings.log_file_enabled:
        log_dir = Path(settings.log_file_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        cleanup_old_logs(settings.log_file_dir, settings.log_file_retention_days)

        file_handler = TimedRotatingFileHandler(
            filename=log_dir / "app.log",
            when="midnight",
            interval=1,
            backupCount=settings.log_file_retention_days,
            encoding="utf-8",
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(StandardFormatter())
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.log_level.upper() == "DEBUG" else logging.WARNING
    )
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
