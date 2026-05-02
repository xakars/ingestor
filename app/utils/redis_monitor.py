import redis.asyncio as redis


async def get_pool_stats(pool: redis.ConnectionPool):
    return {
        "max_connections": pool.max_connections,
        "current_connections": len(pool._in_use_connections) if hasattr(pool, '_in_use_connections') else 0,
        "available_connections": len(pool._available_connections) if hasattr(pool, '_available_connections') else 0,
        "owner": pool.owner if hasattr(pool, 'owner') else None,
    }
