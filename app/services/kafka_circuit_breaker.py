import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger("ingestor")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class KafkaCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def record_success(self):
        """Запись успешного вызова"""
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        logger.debug("Circuit breaker reset to CLOSED")

    def record_failure(self):
        """Запись неудачного вызова"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failures} failures",
            )

    def can_execute(self) -> bool:
        """Проверка можно ли выполнить запрос"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return False
            elapsed = datetime.now() - self.last_failure_time
            if elapsed > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker HALF_OPEN, testing...")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        return False

    def get_state(self) -> dict:
        """Получить текущее состояние для мониторинга"""
        return {
            "state": self.state.value,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "half_open_calls": self.half_open_calls,
        }
