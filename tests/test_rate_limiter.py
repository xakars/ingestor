import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from app.services.rate_limiter import RateLimiter


class MockRedis:
    def __init__(self):
        self.zsets = {}
        self.data = {}
        self.ttls = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        if key not in self.zsets:
            return 0

        initial_count = len(self.zsets[key])
        self.zsets[key] = {
            member: score for member, score in self.zsets[key].items()
            if not (min_score <= score <= max_score)
        }
        return initial_count - len(self.zsets[key])

    async def zcard(self, key: str):
        return len(self.zsets.get(key, {}))

    async def zadd(self, key: str, mapping: dict):
        if key not in self.zsets:
            self.zsets[key] = {}
        self.zsets[key].update(mapping)

    async def incr(self, key: str):
        current = int(self.data.get(key, 0)) + 1
        self.data[key] = str(current)
        return current

    async def expire(self, key: str, second: int):
        self.ttls[key] = second

    async def ttl(self, key: str):
        return self.ttls.get(key, -1)

    def register_script(self, lua: str):
        async def execute(keys=None, args=None):
            key = keys[0]
            limit = int(args[0])
            window = int(args[1])

            current = int(self.data.get(key, 0)) + 1
            self.data[key] = str(current)

            if current == 1:
                self.ttls[key] = window

            return 1 if current <= limit else 0

        return execute


class TestReteLimiter:

    @pytest.fixture
    def rate_limiter(self):
        redis_client = MockRedis()
        return RateLimiter(redis_client)

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, rate_limiter):
        key = "rl:test_user:/api/v1/metrics"

        for i in range(100):
            allowed = await rate_limiter.check_fixed_window(
                key=key,
                limit=100,
                window=60
            )
            assert allowed is True, f"Request {i+1} should be allowed"

    @pytest.mark.asyncio
    async def test_requests_out_off_limiter(self, rate_limiter):
        key = "rl:test_user:/api/v1/metrics"

        for i in range(100):
            await rate_limiter.check_fixed_window(
                key=key,
                limit=100,
                window=60
            )

        # 101-й запрос должен быть заблокирован
        allowed = await rate_limiter.check_fixed_window(key=key, limit=100, window=60)

        assert allowed is False

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, rate_limiter):
        key1 = "rl:user1:/api/v1/metrics"
        key2 = "rl:user2:/api/v1/metrics"

        # Исчерпываем лимит для user1
        for i in range(100):
            await rate_limiter.check_fixed_window(key=key1, limit=100, window=60)

        allowed = await rate_limiter.check_fixed_window(key=key2, limit=100, window=60)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_get_remaining(self, rate_limiter):
        key = "rl:test_user:/api/v1/metrics"
        now = time.time()

        for i in range(50):
            await rate_limiter.redis.zadd(key, {str(now - i): now - i})

        remaining = await rate_limiter.get_remaining(key=key, limit=100, window=60)

        assert remaining == 50
