
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
        local window_ms = tonumber(ARGV[2])
        local now_ms = tonumber(ARGV[3])
        local clear_before = now_ms - window_ms

        -- 1. Очистка старых данных
        redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

        -- 2. Проверка текущего количества
        local current_count = redis.call('ZCARD', key)
        local allowed = 0

        if current_count < limit then
            redis.call('ZADD', key, now_ms, now_ms)
            current_count = current_count + 1
            allowed = 1
        end

        -- 3. Обновляем TTL для ключа (в секундах)
        redis.call('PEXPIRE', key, window_ms / 1000)

        -- 4. Расчет времени до освобождения слота (reset_after)
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        local reset_after = 0
        if #oldest > 0 then
            -- Время сброса = (время самого старого + окно) - сейчас
            local oldest_score = tonumber(oldest[2])
            reset_after = math.ceil((oldest_score + window_ms - now_ms) / 1000000)
        end

        if reset_after < 0 then reset_after = 0 end

        return {allowed, limit - current_count, reset_after}
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

    async def check_rate_limit(
        self,
        key: str,
        limit: int = 100,
        window: int = 60,
    ) -> dict:
        import time
        now = int(time.time() * 1_000_000)
        window_ms = window * 1_000_000

        # ОДИН вызов вместо пяти!
        res = await self._sliding_script(
            keys=[key],
            args=[limit, window_ms, now],
        )

        return {
            "allowed": bool(res[0]),
            "remaining": res[1],
            "reset_after": res[2],
        }
