import json
import logging
from typing import Any, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.config import get_settings

logger = logging.getLogger("ingestor")
settings = get_settings()


class KafkaProducerService:
    """
    Сервис для отправки сообщений в Kafka

    Обеспечивает:
    - Надёжную доставку (acks='all')
    - Retry логику при ошибках
    - Сериализацию данных
    - Мониторинг отправки
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        acks: str = 'all',
        compression_type: str = 'gzip',
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.acks = acks
        self.compression_type = compression_type
        self._producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self):
        """
        Запуск producer

        Вызывается один раз при старте приложения
        """
        if self._started:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            acks=self.acks,
            request_timeout_ms=30000,
            retry_backoff_ms=1000,
            compression_type=self.compression_type,

            # Настройки батчинга
            max_batch_size=16384,  # 16KB макс размер батча
            linger_ms=10,  # Ждать 10мс для заполнения батча


            enable_idempotence=True,


            # Сериализация
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else json.dumps(v).encode('utf-8'),
        )

        await self._producer.start()
        self._started = True

        logger.info(
            "Kafka producer started",
            extra={
                "bootstrap_servers": self.bootstrap_servers,
                "topic": self.topic,
                "acks": self.acks,
            },
        )

    async def stop(self):
        """
        Остановка producer

        Вызывается при shutdown приложения
        """
        if self._producer and self._started:
            await self._producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def send_message(
        self,
        key: str,
        value: dict[str, Any],
        headers: Optional[dict[str, str]] = None,
    ) -> bool:
        """
        Отправка одного сообщения в Kafka

        Args:
            key: Partition key (для порядка сообщений)
            value: Данные сообщения (dict)
            headers: Опциональные заголовки

        Returns:
            bool: True если успешно отправлено

        Raises:
            KafkaError: Если отправка не удалась после retry
        """
        if not self._started:
            raise KafkaError("Producer not started")

        try:
            # Формируем заголовки
            kafka_headers = []
            if headers:
                for k, v in headers.items():
                    kafka_headers.append((k, v.encode('utf-8')))

            # Отправляем сообщение
            await self._producer.send_and_wait(
                topic=self.topic,
                key=key,
                value=value,
                headers=kafka_headers,
            )

            logger.debug(
                "Message sent to Kafka",
                extra={
                    "topic": self.topic,
                    "key": key,
                    "headers": headers,
                },
            )

            return True

        except KafkaError as e:
            logger.error(
                f"Failed to send message to Kafka: {e}",
                extra={
                    "topic": self.topic,
                    "key": key,
                    "error": str(e),
                },
            )
            raise

    async def send_message_batch(
        self,
        messages: list,
    ) -> dict[str, Any]:
        """
        Отправка батча сообщений

        Args:
            messages: Список сообщений [{"key": str, "value": dict, "headers": dict}]

        Returns:
            Dict со статистикой отправки
        """
        if not self._started:
            raise KafkaError("Producer not started")

        success_count = 0
        failed_count = 0
        errors = []

        for msg in messages:
            try:
                await self.send_message(
                    key=msg["key"],
                    value=msg["value"],
                    headers=msg.get("headers"),
                )
                success_count += 1
            except KafkaError as e:
                failed_count += 1
                errors.append({
                    "key": msg["key"],
                    "error": str(e),
                })

        return {
            "total": len(messages),
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
        }
