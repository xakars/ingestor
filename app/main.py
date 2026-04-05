from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import RateLimitMiddleware
from app.services.kafka_producer import KafkaProducerService
from app.services.rate_limiter import RateLimiter

from .api.v1.metrics import metric_router
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
    )

    app.state.kafka_service = KafkaProducerService(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP,
        topic=settings.KAFKA_TOPIC,
        acks=settings.KAFKA_ACKS,
        compression_type=settings.KAFKA_COMPRESSION,
    )
    app.state.rate_limiter = RateLimiter(redis_client=app.state.redis)
    await app.state.kafka_service.start()
    yield
    await app.state.redis.aclose()
    await app.state.kafka_service.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    RateLimitMiddleware,
    limit=100,
    window=60,
    exclude_paths=['/health/live', '/health/ready', '/metrics'],
)

app.include_router(metric_router)


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/health/ready")
async def health_ready():
    try:
        r = app.state.redis
        await r.ping()
        if not app.state.kafka_service._started:
            raise Exception("Kafka producer is not started")
        return {"status": "ready", "redis": "ok", "kafka": "ok"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "redis": "unavailable"},
        )
