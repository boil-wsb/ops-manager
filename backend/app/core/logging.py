import json
import logging
import sys
from datetime import timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.config import settings
from app.core.log_context import request_id_ctx, user_id_ctx
from app.core.tz import from_timestamp, now_shanghai

_LOGRECORD_BUILTIN = frozenset(
    {
        "name",
        "msg",
        "args",
        "created",
        "relativeCreated",
        "exc_info",
        "exc_text",
        "stack_info",
        "levelname",
        "levelno",
        "lineno",
        "funcName",
        "pathname",
        "filename",
        "module",
        "msecs",
        "thread",
        "threadName",
        "process",
        "processName",
        "taskName",
        "message",
        "asctime",
        "request_id",
        "user_id",
        "action",
    }
)


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get("")
        record.user_id = user_id_ctx.get("")
        if not hasattr(record, "action"):
            record.action = record.name
        return True


def _extract_extra(record) -> dict:
    extra = {}
    for key, value in record.__dict__.items():
        if key not in _LOGRECORD_BUILTIN and not key.startswith("_"):
            extra[key] = value
    return extra


class ConsoleFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)-5s | [%(name)s:%(funcName)s:%(lineno)d] | req=%(request_id)s user=%(user_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        msg = super().format(record)
        extra = _extract_extra(record)
        if extra:
            extra_parts = " ".join(f"{k}={v}" for k, v in extra.items())
            msg = f"{msg} | {extra_parts}"
        return msg


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "action": getattr(record, "action", record.name),
            "request_id": getattr(record, "request_id", ""),
            "user_id": getattr(record, "user_id", ""),
            "module": record.name,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        extra = _extract_extra(record)
        if extra:
            log_obj["extra"] = extra
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def _create_formatter():
    if settings.log_format == "json":
        return JsonFormatter()
    return ConsoleFormatter()


def cleanup_old_logs(log_dir: str, retention_days: int) -> None:
    if retention_days <= 0:
        return

    log_path = Path(log_dir)
    if not log_path.exists():
        return

    cutoff = now_shanghai() - timedelta(days=retention_days)

    for file in log_path.glob("app.*.log"):
        try:
            file_mtime = from_timestamp(file.stat().st_mtime)
            if file_mtime < cutoff:
                file.unlink()
        except Exception:
            pass


def configure_logging() -> None:
    ctx_filter = ContextFilter()
    formatter = _create_formatter()

    handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ctx_filter)
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
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ctx_filter)
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
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # 让 uvicorn 日志传播到 root logger，确保文件 handler 能捕获
    # 根因：uvicorn 默认 LOGGING_CONFIG 对 "uvicorn" 和 "uvicorn.access" 设置
    # propagate=False 并挂载自己的 stderr/stdout handler，导致
    # "Exception in ASGI application"（由 Starlette ServerErrorMiddleware 通过
    # uvicorn.error logger 输出）只打印到控制台，不写入日志文件
    for uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uv_name)
        uv_logger.handlers = []  # 移除 uvicorn 自带 handler，统一使用 root 的 file+console
        uv_logger.propagate = True
        # 显式设置 level：uvicorn 主 logger 和 uvicorn.error 用 INFO（确保启动日志写入文件），
        # uvicorn.access 保持上面的 WARNING（避免大量访问日志）
        if uv_name in ("uvicorn", "uvicorn.error"):
            uv_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
