import time
from app.utils.logger import logger

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import TokenData, get_current_user
from app.dependencies.services import get_kafka_producer
from app.schemas.metrics import MetricsPayload, MetricsResponse
from app.services.kafka_producer import KafkaProducerService
from app.middleware.request_id import update_log_context


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
    start_time = time.time()

    update_log_context(
        user_id=user.user_id,
        device_id=payload.device_id,
        metrics_count=len(payload.metrics)
    )

    try:
        success = await producer.send_metrics(
            device_id=payload.device_id,
            metrics_data=payload.model_dump(),
        )

        duration_ms = (time.time() - start_time) * 1000

        if success:
            logger.info(
                "Metrics ingested successfully",
                extra={
                    "duration_ms": round(duration_ms, 2),
                    "kafka_topic": "raw.metrics.v1"
                }
            )
        else:
            logger.warning(
                "Metrics sent to DLQ",
                extra={
                    "duration_ms": round(duration_ms, 2),
                    "reason": "Kafka unavailable"
                }
            )

        return MetricsResponse(
            status="accepted",
            request_id=request.state.request_id,
            metrics_count=len(payload.metrics),
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Failed to ingest metrics",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration_ms, 2)
            },
            exc_info=True
        )
        raise
