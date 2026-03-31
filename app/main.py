from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from .api.v1.metrics import metric_router
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(metric_router)


@app.get("/health/live")
async def health():
    return {"status": "alive", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/health/ready")
async def health_ready():
    try:
        await app.state.redis.ping()
        return {"status": "ready", "redis": "ok"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "redis": "unavailable"}
        )
