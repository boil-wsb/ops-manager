"""
Redis client configuration.
"""
from typing import Optional
import redis.asyncio as aioredis

from app.config import settings

# Redis client instance
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """Initialize Redis connection."""
    global redis_client
    
    if redis_client is None:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            decode_responses=True,
        )
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> aioredis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        await init_redis()
    return redis_client
