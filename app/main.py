from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status

from app.api.v1.auth import auth_router
from app.api.v1.metrics import metric_router
from app.dependencies.redis import get_redis_client, get_redis_pool, shutdown_redis_pool
from app.dependencies.services import get_kafka_producer
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.kafka_producer import KafkaProducerService
from app.services.rate_limiter import RateLimiter

from .config import get_settings

settings = get_settings()
kafka_service: KafkaProducerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_service

    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        connection_pool=await get_redis_pool(),
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
    await shutdown_redis_pool()
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
    redis_client: redis.Redis = Depends(get_redis_client),
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
