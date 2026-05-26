from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = timezone.utc


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def now_utc() -> datetime:
    return datetime.now(UTC_TZ)


def to_shanghai(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC_TZ).astimezone(SHANGHAI_TZ)
    return dt.astimezone(SHANGHAI_TZ)


def from_timestamp(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=SHANGHAI_TZ)


def format_shanghai(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return to_shanghai(dt).strftime(fmt)
