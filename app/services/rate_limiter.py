
import redis.asyncio as redis


class RateLimiter:
    FIXED_WINDOW_SCRIPT = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current = redis.call('INCR', key)
        if current == 1 then
            redis.call('EXPIRE', key, window)
        end 
        if current > limit then
            return 0
        else
            return 1
        end
    """

    SLIDING_WINDOW_SCRIPT = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        redis.call('ZADD', key, now, now)
        local count = redis.call('ZCARD', key)
        redis.call('EXPIRE', key, window)
        return count <= limit and 1 or 0
        """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._fixed_script = redis_client.register_script(self.FIXED_WINDOW_SCRIPT)
        self._sliding_script = redis_client.register_script(self.SLIDING_WINDOW_SCRIPT)

    async def check_fixed_window(
        self,
        key: str,
        limit: int = 100,
        window: int = 60,
    ) -> bool:
        result = await self._fixed_script(
            keys=[key],
            args=[limit, window],
        )
        return result == 1

    async def check_sliding_window(
        self,
        key: str,
        limit: int = 100,
        window: int = 60,
    ) -> bool:
        import time
        now = time.time()
        result = await self._sliding_script(
            keys=[key],
            args=[limit, window, now],
        )
        return result == 1

    async def get_remaining(
        self,
        key: str,
        limit: int = 100,
        window: int = 60,
    ) -> int:
        current = await self.redis.get(key)
        if current is None:
            return limit
        return max(0, limit - int(current))

    async def get_reset_time(self, key: str) -> int:
        ttl = await self.redis.ttl(key)
        return max(0, ttl)
