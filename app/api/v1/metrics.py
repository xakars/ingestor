
import logging

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import TokenData, get_current_user
from app.dependencies.services import get_kafka_producer
from app.schemas.metrics import MetricsPayload, MetricsResponse
from app.services.kafka_producer import KafkaProducerService

logger = logging.getLogger("ingestor")


metric_router = APIRouter(prefix="/api/v1", tags=["Metric API"])


@metric_router.post(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_metrics(
    payload: MetricsPayload,
    request: Request,
    user: TokenData = Depends(get_current_user),
    producer: KafkaProducerService = Depends(get_kafka_producer),

):
    success = await producer.send_metrics(
        device_id=payload.device_id,
        metrics_data=payload.model_dump(),
    )

    if not success:
        logger.warning(
            "Metrics sent to DLQ",
            extra={"device_id": payload.device_id},
        )

    return MetricsResponse(
        status="accepted",
        request_id=request.state.request_id,
        metrics_count=len(payload.metrics),
    )
