import logging
import sys
import json
from datetime import datetime, timezone
from pythonjsonlogger import json
from typing import Dict, Any, Optional
from app.config import get_settings

settings = get_settings()


class CustomJsonFormatter(json.JsonFormatter):
    """
    Кастомный JSON formatter для логов
    Добавляет стандартные поля и обрабатывает contextvars
    """

    def __init__(
        self,
        fmt: str = '%(timestamp)s %(level)s %(service)s %(logger)s %(message)s',
        datefmt: str = '%Y-%m-%dT%H:%M:%S',
        style: str = '%',
        validate: bool = True,
    ):
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            validate=validate,
        )

    def add_fields(
        self,
        log_data: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super(CustomJsonFormatter, self).add_fields(log_data=log_data,record=record, message_dict=message_dict)

        log_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_data['level'] = record.levelname
        log_data['service'] = settings.SERVICE_NAME
        log_data['logger'] = record.name

        if record.filename:
            log_data['location'] = f"{record.filename}:{record.lineno}"

        from app.middleware.request_id import get_log_context
        context = get_log_context()
        for key, value in context.items():
            if key not in log_data:
                log_data[key] = value

        if hasattr(record, 'request_id') and record.request_id:
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id') and record.user_id:
            log_data['user_id'] = record.user_id
        if hasattr(record, 'duration_ms') and record.duration_ms:
            log_data['duration_ms'] = record.duration_ms


def setup_logger(
    name: str,
    level: Optional[str] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Настройка логгера для сервиса
    Args:
        name: Имя логгера (обычно __name__)
        level: Уровень логирования (из env или default)
        json_format: Использовать JSON формат (True для production)
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, (level or settings.LOG_LEVEL).upper()))

    # Обработчик (stdout для Docker)
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        # JSON формат для production
        formatter = CustomJsonFormatter()
    else:
        # Текстовый формат для development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    handler.setFormatter(formatter)

    # Добавляем обработчик если ещё не добавлен
    if not logger.handlers:
        logger.addHandler(handler)

    # Не propagating в root logger (избегаем дублирования)
    logger.propagate = False
    return logger


# Глобальный логгер для приложения
logger = setup_logger("ingestor")
