import logging
from typing import AsyncGenerator

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger("ingestor")
settings = get_settings()

_redis_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    global _redis_pool

    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            # Настройки пула
            max_connections=150,  # Максимум подключений в пуле
            socket_timeout=5,  # Таймаут на операцию
            socket_connect_timeout=5,  # Таймаут на подключение
            retry_on_timeout=True,  # Повтор при таймауте
            # Health check
            health_check_interval=30,  # Проверка здоровья подключения
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


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    Зависимость для получения Redis клиента из пула
    """
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        # Не закрываем клиент, возвращаем в пул
        await client.close()


async def shutdown_redis_pool():
    """
    Очистка пула при остановке приложения
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool closed")
