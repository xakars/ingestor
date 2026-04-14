import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError, LeaderNotAvailableError, NotLeaderForPartitionError

from app.services.kafka_circuit_breaker import KafkaCircuitBreaker
from app.services.kafka_dlq import KafkaDLQ
from app.services.kafka_retry import RetryConfig, retry_with_backoff

logger = logging.getLogger("ingestor")


class KafkaProducerService:
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        dlq_topic: str = "raw.metrics.dlq",
        acks: str = 'all',
        compression_type: str = 'gzip',
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.dql_topic = dlq_topic
        self.acks = acks
        self.compression_type = compression_type
        self._producer: AIOKafkaProducer | None = None
        self._dlq: KafkaDLQ | None = None
        self._circuit_breaker = KafkaCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
        )
        self._started = False

        self._send_count = 0
        self._error_count = 0
        self._dlq_count = 0

    async def start(self):
        if self._started:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            acks=self.acks,
            # retries=self.retries,
            request_timeout_ms=30000,
            retry_backoff_ms=1000,
            compression_type=self.compression_type,
            max_batch_size=16384,
            linger_ms=10,
            enable_idempotence=True,
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else json.dumps(v).encode('utf-8'),
        )
        await self._producer.start()

        # DLQ producer
        self._dlq = KafkaDLQ(self.bootstrap_servers, self.dql_topic)
        await self._dlq.start()
        self._started = True
        logger.info("Kafka producer service started")

    async def stop(self):
        if self._producer and self._started:
            await self._producer.stop()
        if self._dlq:
            await self._dlq.stop()
        self._started = False
        logger.info("Kafka producer service stopped")

    async def send_metrics(
        self,
        device_id: str,
        metrics_data: dict,
        headers: dict[str, str] | None = None,
    ) -> bool:
        if not self._circuit_breaker.can_execute():
            logger.warning(
                "Circuit breaker OPEN, sending to DLQ",
                extra={"device_id": device_id},
            )
            await self._send_to_dlq(device_id, metrics_data, "Circuit breaker open")

            self._error_count += 1
            return False

        async def _send():
            return await self._producer.send_and_wait(
                topic=self.topic,
                key=device_id,
                value=metrics_data,
                headers=[(k, v.encode('utf-8')) for k, v in (headers or {}).items()],
            )

        try:
            await retry_with_backoff(
                _send,
                config=RetryConfig(max_retries=3, base_delay=1.0),
                retryable_exceptions=(LeaderNotAvailableError, NotLeaderForPartitionError),
            )

            self._circuit_breaker.record_success()

            logger.debug(
                f"Metrics sent to Kafka",
                extra={
                    "device_id": device_id,
                    "topic": self.topic,
                    "metrics_count": len(metrics_data.get("metrics", [])),
                },
            )

            return True

        except KafkaError as e:
            self._circuit_breaker.record_failure()
            self._error_count += 1
            logger.error(
                f"Failed to send metrics to Kafka: {e}",
                extra={
                    "device_id": device_id,
                    "topic": self.topic,
                    "error": str(e),
                },
            )

            await self._send_to_dlq(device_id, metrics_data, str(e))
            return False

    async def _send_to_dlq(self, device_id: str, metrics_data: dict, error: str):
        """Отправка в Dead Letter Queue"""
        try:
            await self._dlq.send_to_dlq(
                original_topic=self.topic,
                key=device_id,
                value=metrics_data,
                error=error,
                retry_count=self.retries,
            )
            self._dlq_count += 1
        except Exception as e:
            logger.critical(
                f"DLQ failed: {e}",
                extra={"device_id": device_id, "error": str(e)},
            )

    def get_stats(self) -> dict:
        return {
            "send_count": self._send_count,
            "error_count": self._error_count,
            "dlq_count": self._dlq_count,
            "error_rate": self._error_count / max(self._send_count, 1),
            "circuit_breaker": self._circuit_breaker.get_state(),
        }
