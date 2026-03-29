from fastapi import APIRouter

from app.schemas.metrics import MetricsPayload

metric_router = APIRouter(prefix="/api/v1", tags=["Metric API"])


@metric_router.post("/metrics", response_model="")
async def ingest_metric(req: MetricsPayload):
    return {req.json()}
