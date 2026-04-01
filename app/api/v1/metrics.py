from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.schemas.metrics import MetricResponse, MetricsPayload
from app.utils.jwt import decode_jwt, encode_jwt

security = HTTPBearer()

metric_router = APIRouter(prefix="/api/v1", tags=["Metric API"])


@metric_router.post("/metrics", response_model=MetricResponse)
async def ingest_metric(
    metrics: MetricsPayload,
    auth: HTTPAuthorizationCredentials = Depends(security),
):
    token = auth.credentials
    user_data = decode_jwt(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token is not valid",
        )

    return JSONResponse({
          "status": "accepted",
          "request_id": "req-abc123def456",
          "metrics_count": 2,
          "timestamp": "2024-05-24T10:30:00.000Z",
        }, status_code=status.HTTP_202_ACCEPTED)


class TokenInfo(BaseModel):
    access_token: str
    token_type: str


@metric_router.post("/auth/login", response_model=TokenInfo)
async def get_mocked_jwt():
    jwt_payload = {
        "user": "mocked_admin",
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
