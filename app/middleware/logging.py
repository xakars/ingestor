import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.middleware.request_id import get_log_context, update_log_context
from app.utils.security import SecurityUtils


logger = logging.getLogger("ingestor")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех HTTP запросов
    Логирует:
    - Начало запроса (method, path)
    - Конец запроса (status, duration)
    - Ошибки (с деталями)
    """

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        skip_paths: list = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.skip_paths = skip_paths or ['/health/live', '/health/ready', '/metrics']

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        # Пропускаем health checks и metrics
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        request_id = request.state.request_id

        update_log_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )

        logger.debug(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else None
            }
        )

        # Извлекаем user_id из токена (если есть)
        user_id = await self._extract_user_id(request)
        if user_id:
            update_log_context(user_id=user_id)

        try:
            # Выполняем запрос
            response = await call_next(request)
            # Вычисляем длительность
            duration_ms = (time.time() - start_time) * 1000
            # Определяем уровень лога по статус коду
            log_level = logging.INFO
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING
            # Лог завершения запроса
            logger.log(
                log_level,
                f"Request completed: {request.method} {request.url.path} {response.status_code}",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": response.headers.get("content-length", 0)
                }
            )
            return response
        except Exception as e:
            # Лог ошибки
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2)
                },
                exc_info=True  # Добавляет traceback
            )
            raise

    async def _extract_user_id(self, request: Request) -> str | None:
        """
        Извлекает user_id из JWT токена для логирования
        Не валидирует токен полностью, только извлекает sub claim
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        try:
            from app.utils.jwt import decode_token
            token = auth_header[7:]
            payload = decode_token(token, expected_type="access")
            if payload:
                # Логируем только хеш токена, не сам токен!
                token_hash = SecurityUtils.hash_token(token)
                update_log_context(token_hash=token_hash)
                return payload.get("sub")
        except Exception:
            pass

        return None
