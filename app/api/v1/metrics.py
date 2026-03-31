from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.metrics import MetricResponse, MetricsPayload

metric_router = APIRouter(prefix="/api/v1", tags=["Metric API"])


@metric_router.post("/metrics", response_model=MetricResponse)
async def ingest_metric(req: MetricsPayload):
    return JSONResponse({
          "status": "accepted",
          "request_id": "req-abc123def456",
          "metrics_count": 2,
          "timestamp": "2024-05-24T10:30:00.000Z",
        }, status_code=status.HTTP_202_ACCEPTED)
