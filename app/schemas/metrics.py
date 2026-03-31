from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MetricItem(BaseModel):
    name: str = Field(..., description="Metric name", json_schema_extra={"example":"cpu_usage"})
    value: float = Field(..., description="Metric value", examples=[45.2, 1024.0, 0.95])
    tags: dict[str, str] = Field(default_factory=dict, description="Extra tags")


class MetricsPayload(BaseModel):
    device_id: UUID = Field(..., description="Uniq device id")
    timestamp: int = Field(..., description="Unix timestamp (UTC)", json_schema_extra={"example":"1774964804"})
    metrics: list[MetricItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="list of metrics"
    )

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: UUID) -> UUID:
        if v.version != 4:  # noqa: PLR2004
            raise ValueError("device_id must be a valid UUID v4")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        current_time = int(datetime.now(timezone.utc).timestamp())
        max_future = current_time + 300  # 5 min
        max_past = current_time - 86400  # 24 hour

        if v > max_future:
            raise ValueError(
                f'Timestamp cannot be more than 5 min in future. '
                f'Now: {current_time}, Given: {v}',
            )

        if v < max_past:
            raise ValueError(
                f'Timestamp cannot be older than 24 hours. '
                f'Now: {current_time}, Given: {v}',
            )
        return v


class MetricResponse(BaseModel):
    status: str = Field(json_schema_extra={"example": "accepted"})
    request_id: str = Field(json_schema_extra={"example": "req-abc123def456"})
    metrics_count: int = Field(json_schema_extra={"example": "2"})
    timestamp: str = Field(json_schema_extra={"example": "2024-05-24T10:30:00.000Z"})
