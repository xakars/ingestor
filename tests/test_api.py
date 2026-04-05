import pytest

from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
import uuid


client = TestClient(app)


@pytest.fixture
def valid_token():
    """Фикстура для JWT токена"""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoibW9ja2VkX2FkbWluIiwiZW1haWwiOiJ4YWtAZ21haWwuY29tIiwiaXNfYWN0aXZlIjp0cnVlLCJleHAiOjE3NzUzOTk5NjAsImlhdCI6MTc3NTM5ODE2MH0.oqgG-z87hQgt7wiBtMdzWd0DSYdNan45K-o685Uawgs"


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


def test_rate_limit(valid_token, valid_payload):
    """Тест срабатывания Rate Limiting"""
    # Отправить 101 запрос
    for i in range(101):
        response = client.post(
            "/api/v1/metrics",
            json=valid_payload,
            headers={"Authorization": valid_token}
        )
    # 101-й должен получить 429
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]