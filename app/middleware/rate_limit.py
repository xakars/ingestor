import logging
import time
import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.services.rate_limiter import RateLimiter
from app.utils.jwt import decode_jwt

logger = logging.getLogger("ingestor")
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        exclude_paths: list = None,
    ):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.exclude_paths = exclude_paths or ['/health/live', '/health/ready', '/metrics']

    async def dispatch(self, request: Request, call_next):
        request_id = f"req-{uuid.uuid4()}"
        request.state.request_id = request_id
        rate_limiter: RateLimiter = request.app.state.rate_limiter
        # Пропускаем исключённые пути
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        start_time = time.time()
        # Формируем ключ rate limit
        user_id = await self._get_user_id(request)
        key = f"rl:{user_id}:{request.url.path}"
        # Проверяем лимит
        allowed = await rate_limiter.check_fixed_window(
            key=key,
            limit=self.limit,
            window=self.window,
        )
        if not allowed:
            # Получаем информацию для заголовков
            remaining = await rate_limiter.get_remaining(key, self.limit, self.window)
            reset_time = await rate_limiter.get_reset_time(key)
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "user_id": user_id,
                    "path": request.url.path,
                    "key": key,
                    "remaining": remaining,
                    "reset_time": reset_time,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "retry_after": reset_time,
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        response = await call_next(request)
        # Добавляем заголовки rate limit в ответ
        remaining = await rate_limiter.get_remaining(key, self.limit, self.window)
        reset_time = await rate_limiter.get_reset_time(key)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-Request-ID"] = request_id
        # Логирование
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            "Rate limit check passed",
            extra={
                "user_id": user_id,
                "path": request.url.path,
                "remaining": remaining,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    async def _get_user_id(self, request: Request) -> str:
        """
        Извлекает user_id из токена или использует IP
        Для анонимных запросов используем IP адрес
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_jwt(token)
            if payload and "user_id" in payload:
                return f"user_{payload.get('user_id')}"
        # Fallback на IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip_{client_ip}"
