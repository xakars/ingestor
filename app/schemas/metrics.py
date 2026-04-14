from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )


class MetricItem(BaseSchema):
    name: str = Field(..., description="Metric name", examples=["cpu_usage", "memory_free", "disk_io"])
    value: float = Field(..., description="Metric value", examples=[45.2, 1024.0, 0.95])
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Extra tags",
        examples=[{"host": "server-01", "region": "eu-west"}],
    )


class MetricsPayload(BaseSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "timestamp": 1712405492,
                "metrics": [{"name": "cpu", "value": 10.5}],
            },
        },
    )
    device_id: str = Field(..., description="Uniq device id")
    timestamp: int = Field(..., description="Unix timestamp (UTC)", examples=[1775405495])

    metrics: list[MetricItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="list of metrics",
    )

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        try:
            uuid_obj = UUID(v)
        except ValueError:
            raise ValueError("device_id must be a valid UUID string")

        if uuid_obj.version != 4:  # noqa: PLR2004
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


class MetricsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'status': 'accepted',
                'request_id': 'req-abc123',
                'metrics_count': 2,
                'timestamp': '2024-05-24T10:30:00.000Z',
            },
        },
    )

    status: str = Field(
        ...,
        description="Processing status",
        examples=["accepted", "pending"],
    )

    request_id: str = Field(
        ...,
        description="Unique request ID for tracing and debugging",
        examples=["req-abc123def456"],
    )

    metrics_count: int = Field(
        ...,
        description="Number of successfully received metrics",
        examples=[2, 10, 50],
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Request processing timestamp in ISO 8601 format",
    )
