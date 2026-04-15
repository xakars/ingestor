import pytest
import uuid
from datetime import datetime, timezone


@pytest.fixture
def metrics_payload():
    return {
        "device_id": str(uuid.uuid4()),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "metrics": [{"name": "cpu", "value": 45.0}]
    }


@pytest.fixture
def metrics_response():
    return {
          "status": "accepted",
          "request_id": "req-fefdf03f-82d4-4fc8-8fa8-fc956f36b631",
          "metrics_count": 1,
          "timestamp": "2026-04-14T08:27:49.172102+00:00"
    }
