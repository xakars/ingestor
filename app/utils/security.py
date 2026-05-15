import secrets
import hashlib
from datetime import datetime, timezone
import logging

logger = logging.getLogger("ingestor")


class SecurityUtils:
    """Утилиты безопасности для JWT"""

    @staticmethod
    def generate_secret_key() -> str:
        """
        Генерация криптографически стойкого секретного ключа

        Использование:
            SECRET_KEY = SecurityUtils.generate_secret_key()
            # Сохранить в .env и никогда не менять!
        """
        return secrets.token_urlsafe(32)  # 256 бит

    @staticmethod
    def hash_token(token: str) -> str:
        """Хеширование токена для безопасного логирования"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    @staticmethod
    def get_token_info(token: str) -> dict:
        """
        Получение информации о токене без декодирования payload

        Безопасно для логирования
        """
        parts = token.split('.')
        if len(parts)!=3:
            return {"error": "Invalid token format"}

        return {
            "token_hash": SecurityUtils.hash_token(token),
            "header_length": len(parts[0]),
            "payload_length": len(parts[1]),
            "signature_length": len(parts[2])
        }

    @staticmethod
    def validate_token_claims(payload: dict) -> bool:
        """
        Валидация обязательных claims в токене

        Returns:
            bool: True если все обязательные claims присутствуют
        """
        required_claims = ['sub', 'exp', 'iat', 'type']
        return all(claim in payload for claim in required_claims)

    @staticmethod
    def is_token_expiring_soon(payload: dict, threshold_minutes: int = 5) -> bool:
        """
        Проверка истекает ли токен скоро

        Полезно для preemptive refresh
        """
        exp = payload.get('exp')
        if not exp:
            return True

        exp_time = datetime.fromtimestamp(exp, timezone.utc)
        now = datetime.now(timezone.utc)
        remaining = exp_time - now

        return remaining.total_seconds() < threshold_minutes * 60
