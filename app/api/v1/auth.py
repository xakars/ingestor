from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.dependencies.auth import TokenData, TokenPair, get_current_user
from app.utils.jwt import create_access_token, create_refresh_token, decode_token

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"


@auth_router.post("/login", response_model=TokenPair)
async def login(request: LoginRequest):
    """
    Аутентификация пользователя и выдача токенов
    В production здесь должна быть проверка в БД
    """
    # Пример проверки (в реальности — запрос к БД)
    # user = await db.get_user_by_email(request.email)
    # if not user or not verify_password(request.password, user.password_hash):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")
    # Для демо — принимаем любой пароль длиннее 6 символов
    if len(request.password) < 6:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Создаём токены
    user_data = {
        "sub": f"user_{request.email.split('@')[0]}",
        "email": request.email,
        "role": "user",
        "permissions": ["read", "write"],
    }
    access_token = create_access_token(
        data=user_data,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data=user_data,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post("/refresh", response_model=TokenPair)
async def refresh_token(request: RefreshRequest):
    """
    Обновление access token по refresh token
    Refresh token должен быть валидным и не отозванным
    """
    payload = decode_token(request.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Проверка что токен не отозван (в production — проверка в БД/Redis blacklist)
    # if await is_token_revoked(request.refresh_token):
    #     raise HTTPException(status_code=401, detail="Token revoked")
    # Создаём новую пару токенов
    user_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        "permissions": payload.get("permissions", []),
    }
    access_token = create_access_token(
        data=user_data,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Опционально: выдать новый refresh token (rotation)
    refresh_token = create_refresh_token(
        data=user_data,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.get("/me", response_model=TokenData)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    Требует валидный access token
    """
    return current_user
