from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.jwt import decode_token
from typing import Optional
from pydantic import BaseModel
import logging
logger = logging.getLogger("ingestor")
security = HTTPBearer()


class TokenData(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: str = "user"
    permissions: list = []


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:

    token = creds.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token, expected_type="access")

    if payload is None:
        raise

    user_id: str = payload.get("sub")
    email: str = payload.get("email")
    role: str = payload.get("role", "user")
    permissions: list = payload.get("permissions", [])

    if user_id is None:
        raise credentials_exception

    return TokenData(
        user_id=user_id,
        email=email,
        role=role,
        permissions=permissions
    )
