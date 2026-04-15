import pytest
from pydantic import ValidationError
from app.schemas.metrics import MetricsPayload, MetricItem, MetricsResponse
from datetime import datetime, timezone


def test_valid_payload(metrics_payload):
    payload = MetricsPayload(**metrics_payload)
    assert len(payload.metrics) == 1
    assert payload.device_id is not None


def test_invalid_uuid(metrics_payload):
    metrics_payload["device_id"] = "not-valid-uuid-8888"
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    assert "UUID" in str(exc_info.value)


def test_timestamp_too_old(metrics_payload):
    metrics_payload["timestamp"] = int(datetime.now(timezone.utc).timestamp()) - 100000
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
        assert "24 hours" in str(exc_info.value)


def test_empty_metrics(metrics_payload):
    metrics_payload["metrics"] = []
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    assert "should have at least 1 item" in str(exc_info.value)


def test_too_many_metrics(metrics_payload):
    with pytest.raises(ValidationError) as exc_info:
        metrics_payload["metrics"] = [MetricItem(name=f"m{i}", value=1.0) for i in range(101)]
        MetricsPayload(**metrics_payload)
    assert "should have at most 100 items" in str(exc_info.value)


def test_timestamp_from_future(metrics_payload):
    metrics_payload["timestamp"] += 100000
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    assert "Timestamp cannot be more than 5 min in future" in str(exc_info.value)


def test_request_have_extra_field(metrics_payload):
    metrics_payload["extra_filed"] = "device_ID"
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    errors = exc_info.value.errors()
    error_type = errors[0]["type"]
    assert error_type == "extra_forbidden"


def test_uuid_v_7(metrics_payload):
    metrics_payload["device_id"] = "019d6160-1b9e-7b90-8ced-d6137c828593"
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    errors = exc_info.value.errors()
    assert "device_id must be a valid UUID v4" in str(errors)


def test_metric_wrong_value(metrics_payload):
    metrics_payload["metrics"] = [{"name": "cpu", "value": "null"}]
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    errors = exc_info.value.errors()
    assert "Input should be a valid number" in str(errors)


def test_metric_wrong_name(metrics_payload):
    metrics_payload["metrics"] = [{"name": 45.5, "value": "43.3"}]
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    errors = exc_info.value.errors()
    assert "Input should be a valid string" in str(errors)


def test_metrics_wrong_tag(metrics_payload):
    metrics_payload["metrics"] = [{"name": "cpu", "value": 45.0, "tags": {"key": 45.5}}]
    with pytest.raises(ValidationError) as exc_info:
        MetricsPayload(**metrics_payload)
    errors = exc_info.value.errors()
    assert "Input should be a valid string" in str(errors)


def test_valid_metrics_response(metrics_response):
    response = MetricsResponse(**metrics_response)
    assert response.request_id is not None


def test_invalid_metrics_count(metrics_response):
    metrics_response["metrics_count"] = "not-an-int"
    with pytest.raises(ValidationError) as exc_info:
        MetricsResponse(**metrics_response)
    assert "metrics_count" in str(exc_info.value)


def test_missing_status(metrics_response):
    metrics_response.pop("status")
    with pytest.raises(ValidationError) as exc_info:
        MetricsResponse(**metrics_response)
    assert "status" in str(exc_info.value)


def test_invalid_request_id(metrics_response):
    metrics_response["request_id"] = None
    with pytest.raises(ValidationError) as exc_info:
        MetricsResponse(**metrics_response)
    assert "request_id" in str(exc_info.value)


def test_timestamp_default():
    response = MetricsResponse(
        status="accepted",
        request_id="req-123",
        metrics_count=1
    )
    assert response.timestamp is not None
    assert isinstance(response.timestamp, str)
