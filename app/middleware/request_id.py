from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from typing import Optional
import uuid
import logging
from contextvars import ContextVar
from typing import Dict, Any


logger = logging.getLogger("ingestor")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware для добавления Requiest ID ко всем запросам
    Request ID:
    - Генерируется если не предоставлен клиентом
    - Добавляется в ответ
    - Добавляется в контекст логирования
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        context_token = log_context.set({"request_id": request_id})

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            log_context.reset(context_token)


log_context: ContextVar[Dict[str, Any]] = ContextVar(
    "log_context",
    default={"request_id": "unknown"}
)


def get_log_context() -> Dict[str, Any]:
    """Получить текущий контекст логирования"""
    return log_context.get()


def update_log_context(**kwargs):
    """Обновить контекст логирования"""
    current = log_context.get()
    current.update(kwargs)
    log_context.set(current)