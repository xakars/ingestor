import pytest
from pydantic import ValidationError
from app.schemas.metrics import MetricsPayload, MetricItem
from datetime import datetime, timezone
import uuid


def test_valid_payload():
    payload = MetricsPayload(
        device_id=str(uuid.uuid4()),
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        metrics=[MetricItem(name="cpu", value=45.0)]
    )
    assert len(payload.metrics) == 1
    assert payload.device_id is not None


def test_invalid_uuid():
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(
            device_id="not-a-uuid",
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            metrics=[MetricItem(name="cpu", value=45.0)]
        )
        print(exc_info)
    assert "UUID" in str(exc_info.value)


def test_timestamp_too_old():
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(
            device_id=str(uuid.uuid4()),
            timestamp=int(datetime.now(timezone.utc).timestamp()) - 100000,
            metrics=[MetricItem(name="cpu", value=45.0)]
        )
        assert "24 hours" in str(exc_info.value)


def test_empty_metrics():
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(
            device_id=str(uuid.uuid4()),
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            metrics=[]
        )
    assert "should have at least 1 item" in str(exc_info.value)


def test_too_many_metrics():
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(
            device_id=str(uuid.uuid4()),
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            metrics=[MetricItem(name=f"m{i}", value=1.0) for i in range(101)]
        )
    assert "should have at most 100 items" in str(exc_info.value)
