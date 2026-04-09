"""
Audit logger for recording operations to both database and file.
"""

import json
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any

from app.config import settings
from app.core.audit.sanitizer import sanitize_sensitive_data
from app.models.audit_log import AuditLog


class AuditLogger:
    """
    Audit logger that writes to both database and file.
    """

    _instance = None
    _file_logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.enabled = settings.audit_log_enabled
        self._init_file_logger()

    def _init_file_logger(self):
        """Initialize file logger for audit logs."""
        if not self.enabled:
            return

        # Ensure logs directory exists
        log_dir = os.path.dirname(settings.audit_log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Parse max file size
        max_bytes = self._parse_file_size(settings.audit_log_max_file_size)

        # Create rotating file handler
        file_handler = RotatingFileHandler(
            filename=settings.audit_log_file_path,
            maxBytes=max_bytes,
            backupCount=settings.audit_log_backup_count,
            encoding="utf-8",
        )

        # Set formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | AUDIT | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)

        # Create logger
        self._file_logger = logging.getLogger("audit_logger")
        self._file_logger.setLevel(logging.INFO)
        self._file_logger.handlers = []  # Clear existing handlers
        self._file_logger.addHandler(file_handler)
        self._file_logger.propagate = False  # Don't propagate to root logger

    def _parse_file_size(self, size_str: str) -> int:
        """Parse file size string to bytes."""
        size_str = size_str.upper().strip()
        multipliers = {
            "GB": 1024 * 1024 * 1024,
            "MB": 1024 * 1024,
            "KB": 1024,
            "B": 1,
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number_part = size_str[: -len(suffix)].strip()
                return int(number_part) * multiplier

        # Default to bytes if no suffix
        return int(size_str)

    async def log(
        self,
        operation_type: str,
        operation_module: str,
        object_type: str | None = None,
        object_id: str | None = None,
        object_name: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        operator_id: int | None = None,
        operator_name: str | None = None,
        operator_ip: str | None = None,
        user_agent: str | None = None,
        status: str = "SUCCESS",
        error_message: str | None = None,
        request_id: str | None = None,
        duration_ms: int | None = None,
    ) -> AuditLog | None:
        """
        Log an audit event to both database and file.

        Returns:
            AuditLog instance if database logging succeeded, None otherwise
        """
        if not self.enabled:
            return None

        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        # Sanitize data
        before_data_sanitized = sanitize_sensitive_data(before_data) if before_data else None
        after_data_sanitized = sanitize_sensitive_data(after_data) if after_data else None

        # Log to file (always synchronous)
        self._log_to_file(
            operation_type=operation_type,
            operation_module=operation_module,
            object_type=object_type,
            object_id=object_id,
            object_name=object_name,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_ip=operator_ip,
            status=status,
            error_message=error_message,
            request_id=request_id,
            duration_ms=duration_ms,
            before_data=before_data_sanitized,
            after_data=after_data_sanitized,
        )

        # Log to database
        try:
            audit_log = await self._log_to_database(
                operation_type=operation_type,
                operation_module=operation_module,
                object_type=object_type,
                object_id=object_id,
                object_name=object_name,
                before_data=before_data_sanitized,
                after_data=after_data_sanitized,
                operator_id=operator_id,
                operator_name=operator_name,
                operator_ip=operator_ip,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
                request_id=request_id,
                duration_ms=duration_ms,
            )
            return audit_log
        except Exception as e:
            # Log error but don't fail the operation
            logging.error(f"Failed to write audit log to database: {e}")
            return None

    def _log_to_file(
        self,
        operation_type: str,
        operation_module: str,
        object_type: str | None,
        object_id: str | None,
        object_name: str | None,
        operator_id: int | None,
        operator_name: str | None,
        operator_ip: str | None,
        status: str,
        error_message: str | None,
        request_id: str,
        duration_ms: int | None,
        before_data: dict | None,
        after_data: dict | None,
    ):
        """Log to file."""
        if not self._file_logger:
            return

        # Build log message
        log_data = {
            "request_id": request_id,
            "type": operation_type,
            "module": operation_module,
            "object": f"{object_type}:{object_id}" if object_type and object_id else None,
            "object_name": object_name,
            "operator": operator_name or f"user:{operator_id}",
            "ip": operator_ip,
            "status": status,
            "duration_ms": duration_ms,
            "error": error_message,
        }

        # Add data changes summary
        if before_data or after_data:
            log_data["changes"] = self._summarize_changes(before_data, after_data)

        # Convert to JSON string
        log_message = json.dumps(log_data, ensure_ascii=False, default=str)

        # Write to file
        self._file_logger.info(log_message)

    def _summarize_changes(
        self, before_data: dict | None, after_data: dict | None
    ) -> dict[str, Any]:
        """Summarize changes between before and after data."""
        summary = {}

        if before_data and after_data:
            # Find changed fields
            changed = {}
            all_keys = set(before_data.keys()) | set(after_data.keys())
            for key in all_keys:
                before = before_data.get(key)
                after = after_data.get(key)
                if before != after:
                    changed[key] = {"from": before, "to": after}
            summary["changed_fields"] = changed
        elif after_data:
            summary["created"] = list(after_data.keys())
        elif before_data:
            summary["deleted"] = list(before_data.keys())

        return summary

    async def _log_to_database(
        self,
        operation_type: str,
        operation_module: str,
        object_type: str | None,
        object_id: str | None,
        object_name: str | None,
        before_data: dict | None,
        after_data: dict | None,
        operator_id: int | None,
        operator_name: str | None,
        operator_ip: str | None,
        user_agent: str | None,
        status: str,
        error_message: str | None,
        request_id: str,
        duration_ms: int | None,
    ) -> AuditLog:
        """Log to database."""
        from app.db.session import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as db:
            audit_log = AuditLog(
                operation_type=operation_type,
                operation_module=operation_module,
                object_type=object_type,
                object_id=str(object_id) if object_id else None,
                object_name=object_name,
                before_data=before_data,
                after_data=after_data,
                operator_id=operator_id,
                operator_name=operator_name,
                operator_ip=operator_ip,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
                request_id=request_id,
                duration_ms=duration_ms,
            )

            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            return audit_log


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
