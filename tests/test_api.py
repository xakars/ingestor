import pytest

from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
import uuid


client = TestClient(app)


@pytest.fixture
def valid_token():
    """Фикстура для JWT токена"""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoibW9ja2VkX2FkbWluIiwiZW1haWwiOiJ4YWtAZ21haWwuY29tIiwiaXNfYWN0aXZlIjp0cnVlLCJleHAiOjE3NzUwMTQxOTksImlhdCI6MTc3NTAxMjM5OX0.RNlXzG3k3nBpAEWv4-p3jol6eaX2OCRRkCIWc68gMMk"


@pytest.fixture
def valid_payload():
    """Фикстура для валидного запроса"""
    return {
        "device_id": str(uuid.uuid4()),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "metrics": [
            {"name": "cpu_usage", "value": 45.2},
            {"name": "memory_usage", "value": 1024}
        ]
    }


def test_metrics_ingest_success(valid_token, valid_payload):
    """Тест успешной отправки метрик"""
    response = client.post(
        "/api/v1/metrics",
        json=valid_payload,
        headers={"Authorization": valid_token}
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["metrics_count"] == 2


def test_invalid_token(valid_payload):
    """Тест невалидного токена"""
    response = client.post(
        "/api/v1/metrics",
        json=valid_payload,
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
