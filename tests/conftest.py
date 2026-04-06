import pytest
import uuid
from datetime import datetime, timezone


@pytest.fixture
def base_payload():
    return {
        "device_id": str(uuid.uuid4()),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "metrics": [{"name": "cpu", "value": 45.0}]
    }
