import logging

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger("ingestor")
settings = get_settings()

_redis_pool: redis.ConnectionPool | None = None


def get_redis_pool() -> redis.ConnectionPool:
    global _redis_pool

    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            max_connections=50,
            decode_responses=False,
        )
        logger.info(
            f"Redis connection pool created",
            extra={
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "max_connections": 50,
            },
        )
    return _redis_pool
