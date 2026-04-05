from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

settings = get_settings()


def encode_jwt(
    payload: dict,
    secret: str = settings.JWT_SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM,
    expire_minutes: int = settings.JWT_EXPIRE_MINUTES,
):
    to_encode = payload.copy()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)
    to_encode.update(exp=expire, iat=now)

    encoded = jwt.encode(
        to_encode,
        secret,
        algorithm=algorithm,
    )

    return encoded


def decode_jwt(
    encoded: str | bytes,
    secret: str = settings.JWT_SECRET_KEY,
    algorithm: str = settings.JWT_ALGORITHM,
) -> dict | None:
    try:
        decoded = jwt.decode(
            encoded,
            secret,
            algorithms=[algorithm],
        )
    except Exception:
        return None

    return decoded
