import asyncio
import logging
from typing import Any, Callable

from aiokafka.errors import KafkaError

logger = logging.getLogger("ingestor")


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable,
    config: RetryConfig = RetryConfig(),
    retryable_exceptions: tuple = (KafkaError,),
) -> Any:

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == config.max_retries:
                logger.error(
                    f"All retry attempts exhausted",
                    extra={
                        "function": func.__name__,
                        "attempts": config.max_retries,
                        "error": str(e),
                    },
                )
                raise
            # Вычисляем задержку
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay,
            )
            # Добавляем jitter для предотвращения thundering herd
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random())
            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_retries} after {delay:.2f}s",
                extra={
                    "function": func.__name__,
                    "error": str(e),
                    "delay": delay,
                },
            )
            await asyncio.sleep(delay)
    raise last_exception
