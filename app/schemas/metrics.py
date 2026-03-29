from uuid import UUID

from pydantic import BaseModel, Field


class MetricItem(BaseModel):
    name: str
    value: float
    tags: dict[str, str] = Field(default_factory=dict, description="Extra tags")


class MetricsPayload(BaseModel):
    device_id: UUID
    timestamp: int
    metrics: list[MetricItem]
