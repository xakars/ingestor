import json

import pytest
from aiokafka import AIOKafkaConsumer
from testcontainers.kafka import KafkaContainer

from app.services.kafka_producer import KafkaProducerService


@pytest.fixture(scope="session")
def kafka_container():
    container = KafkaContainer("confluentinc/cp-kafka:7.5.0")
    with container as kafka:
        yield kafka


@pytest.fixture()
async def kafka_service(kafka_container):
    bootstrap_server = kafka_container.get_bootstrap_server()

    service = KafkaProducerService(
        bootstrap_servers=bootstrap_server,
        topic="test.metrics",
    )
    await service.start()
    service._bootstrap_server = bootstrap_server
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_send_and_consume_message(kafka_service):
    await kafka_service.send_metrics(
        device_id="test-device-123",
        metrics_data={"metrics": [{"name": "cpu", "value": 777}]},
    )

    consumer = AIOKafkaConsumer(
        "test.metrics",
        bootstrap_servers=kafka_service._bootstrap_server,
        group_id="test-group",
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            # print(msg)
            value = json.loads(msg.value.decode('utf-8'))
            assert value["metrics"][0]["name"] == "cpu"
            break
    finally:
        await consumer.stop()


@pytest.mark.asyncio
async def test_message_ordering(kafka_service):
    consumer = AIOKafkaConsumer(
        "test.metrics",
        bootstrap_servers=kafka_service._bootstrap_server,
        group_id="order-test-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()

    try:
        # 2. Отправляем данные
        for i in range(10):
            await kafka_service.send_metrics(
                device_id="order-test-device",
                metrics_data={"sequence": i, "metrics": []},
            )

        sequences = []
        async for msg in consumer:
            value = json.loads(msg.value.decode('utf-8'))

            if value.get("device_id") == "order-test-device" or "sequence" in value:
                sequences.append(value.get("sequence"))

            if len(sequences) >= 10:
                break

        assert sequences == list(range(10)), f"Order broken: {sequences}"
    finally:
        await consumer.stop()
