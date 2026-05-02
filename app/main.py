from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status

from app.api.v1.auth import auth_router
from app.api.v1.metrics import metric_router
from app.dependencies.redis import get_redis_pool
from app.dependencies.services import get_kafka_producer
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.kafka_producer import KafkaProducerService
from app.services.rate_limiter import RateLimiter
from app.dependencies.services import get_redis
from app.utils.redis_monitor import get_pool_stats

from .config import get_settings

settings = get_settings()
kafka_service: KafkaProducerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_service

    pool = get_redis_pool()

    app.state.redis = redis.Redis(
        connection_pool=pool,
    )

    kafka_service = KafkaProducerService(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP,
        topic=settings.KAFKA_TOPIC,
        acks=settings.KAFKA_ACKS,
        compression_type=settings.KAFKA_COMPRESSION,
        dlq_topic="raw.metrics.dlq",
    )
    await kafka_service.start()
    app.state.kafka_service = kafka_service

    app.state.rate_limiter = RateLimiter(redis_client=app.state.redis)
    yield
    await pool.disconnect()
    if kafka_service:
        await kafka_service.stop()


app = FastAPI(title="Nexus Ingestor API", lifespan=lifespan)

app.add_middleware(
    RateLimitMiddleware,
    limit=100,
    window=60,
    exclude_paths=['/health/live', '/health/ready', '/metrics'],
)

app.include_router(metric_router)
app.include_router(auth_router)


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/health/ready")
async def health_ready(
    redis_client: redis.Redis = Depends(get_redis),
    producer: KafkaProducerService = Depends(get_kafka_producer),
):
    try:
        await redis_client.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "unavailable"

    kafka_status = "ok" if producer._started else "unavailable"

    if redis_status != "ok" or kafka_status != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "redis": redis_status, "kafka": kafka_status},
        )

    return {"status": "ready", "redis": redis_status, "kafka": kafka_status}


@app.get("/admin/redis/stats")
async def redis_stats():
    pool = get_redis_pool()
    stats = await get_pool_stats(pool)
    # Дополнительно INFO от Redis сервера
    client = redis.Redis(connection_pool=pool)
    info = await client.info()
    return {
        "pool": stats,
        "server": {
            "used_memory": info.get("used_memory"),
            "used_memory_peak": info.get("used_memory_peak"),
            "connected_clients": info.get("connected_clients"),
            "rejected_connections": info.get("rejected_connections"),
        },
    }
