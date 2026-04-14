
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.dependencies import get_kafka_producer
from app.schemas.metrics import MetricsPayload, MetricsResponse
from app.services.kafka_producer import KafkaProducerService
from app.utils.jwt import decode_jwt, encode_jwt

security = HTTPBearer()
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
    auth: HTTPAuthorizationCredentials = Depends(security),
    producer: KafkaProducerService = Depends(get_kafka_producer),

):
    token = auth.credentials
    user_data = decode_jwt(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token is not valid",
        )

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


class TokenInfo(BaseModel):
    access_token: str
    token_type: str


@metric_router.post("/auth/login", response_model=TokenInfo)
async def get_mocked_jwt():
    jwt_payload = {
        "user_id": "mocked_admin",
        "email": "xak@gmail.com",
        "is_active": True,
    }
    token = encode_jwt(
        jwt_payload,
    )
    return TokenInfo(
            access_token=token,
            token_type="Bearer",
        )
