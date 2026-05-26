"""
Redis cache utility module.
"""

import json
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


def _serialize(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _deserialize(value: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


async def cache_get(key: str) -> Any | None:
    redis = await get_redis()
    value = await redis.get(key)
    if value is None:
        return None
    return _deserialize(value)


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    redis = await get_redis()
    await redis.set(key, _serialize(value), ex=ttl)


async def cache_delete(*keys: str) -> None:
    if not keys:
        return
    redis = await get_redis()
    await redis.delete(*keys)


async def cache_delete_pattern(pattern: str) -> None:
    redis = await get_redis()
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)


async def cache_get_or_set(key: str, factory: Any, ttl: int = 60) -> Any:
    cached = await cache_get(key)
    if cached is not None:
        return cached

    import inspect

    if inspect.iscoroutinefunction(factory):
        value = await factory()
    else:
        value = factory()

    if value is not None:
        await cache_set(key, value, ttl)

    return value
