import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.kafka_producer import KafkaProducerService
from app.services.kafka_circuit_breaker import KafkaCircuitBreaker, CircuitState
from aiokafka.errors import KafkaError, LeaderNotAvailableError


class TestKafkaCircuitBreaker:
    """Тесты Circuit Breaker"""

    def test_initial_state_closed(self):
        """Начальное состояние — CLOSED"""
        cb = KafkaCircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        """Открывается после threshold неудач"""
        cb = KafkaCircuitBreaker(failure_threshold=3)
        for i in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        """Переход в HALF_OPEN после timeout"""
        import time
        cb = KafkaCircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(1.1)  # Ждём recovery timeout
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_on_success(self):
        """Закрывается после успешного вызова"""
        cb = KafkaCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


class TestKafkaProducerService:
    @pytest.fixture
    def mock_producer(self):
        """Мок AIOKafkaProducer"""
        producer = AsyncMock()
        producer.start = AsyncMock()
        producer.stop = AsyncMock()
        producer.send_and_wait = AsyncMock()
        return producer

    @pytest.fixture
    def kafka_service(self, mock_producer):
        with patch('app.services.kafka_producer.AIOKafkaProducer', return_value=mock_producer), \
             patch('app.services.kafka_producer.KafkaDLQ') as mock_dlq_class:
            mock_dlq_class.return_value = AsyncMock()

            service = KafkaProducerService(
                bootstrap_servers='localhost:9092',
                topic='test.topic'
            )
            yield service

    @pytest.mark.asyncio
    async def test_send_metrics_success(self, kafka_service, mock_producer):
        """Тест успешной отправки"""
        await kafka_service.start()
        result = await kafka_service.send_metrics(
            device_id="device-123",
            metrics_data={"metrics": [{"name": "cpu", "value": 45}]}
        )
        assert result is True
        mock_producer.send_and_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_metrics_failure_sends_to_dlq(self, kafka_service, mock_producer):
        """Тест отправки в DLQ при ошибке"""
        await kafka_service.start()

        mock_producer.send_and_wait.side_effect = LeaderNotAvailableError()
        with patch.object(kafka_service, '_send_to_dlq', new_callable=AsyncMock) as mock_dlq:
            result = await kafka_service.send_metrics(
                device_id="device-123",
                metrics_data={"metrics": [{"name": "cpu", "value": 45}]}
            )
            assert result is False
            mock_dlq.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, kafka_service, mock_producer):
        """Тест что circuit breaker открывается при ошибках"""
        await kafka_service.start()
        # 5 неудачных отправок
        mock_producer.send_and_wait.side_effect = LeaderNotAvailableError()
        for i in range(5):
            await kafka_service.send_metrics(
                device_id=f"device-{i}",
                metrics_data={"metrics": []}
            )
        # Circuit breaker должен открыться
        assert kafka_service._circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_get_stats(self, kafka_service):
        """Тест получения статистики"""
        await kafka_service.start()
        # Отправляем несколько сообщений
        await kafka_service.send_metrics("device-1", {"metrics": []})
        await kafka_service.send_metrics("device-2", {"metrics": []})
        stats = kafka_service.get_stats()
        assert "send_count" in stats
        assert "error_count" in stats
        assert "dlq_count" in stats
        assert "circuit_breaker" in stats
