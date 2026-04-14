import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer

logger = logging.getLogger("ingestor")


class KafkaDLQ:
    def __init__(self, bootstrap_servers: str, dlq_topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.dlq_topic = dlq_topic
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            acks=1,
            request_timeout_ms=5000,
        )
        await self._producer.start()

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def send_to_dlq(
        self,
        original_topic: str,
        key: str,
        value: dict,
        error: str,
        retry_count: int = 0,
    ):
        dlq_message = {
            "original_topic": original_topic,
            "original_key": key,
            "original_value": value,
            "error": error,
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ingestor",
        }

        try:
            await self._producer.send_and_wait(
                topic=self.dlq_topic,
                key=key,
                value=json.dumps(dlq_message).encode('utf-8'),
            )
            logger.warning(
                f"Message sent to DLQ",
                extra={
                    "dlq_topic": self.dlq_topic,
                    "original_topic": original_topic,
                    "key": key,
                    "error": error,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to send to DLQ: {e}",
                extra={"key": key, "error": str(e)},
            )
            logger.critical(f"DLQ FAILED: {dlq_message}")
