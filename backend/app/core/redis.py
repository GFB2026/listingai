import redis.asyncio as aioredis

from app.config import get_settings


class RedisPool:
    def __init__(self):
        self._pool: aioredis.Redis | None = None

    async def initialize(self):
        settings = get_settings()
        self._pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )

    @property
    def client(self) -> aioredis.Redis:
        if self._pool is None:
            raise RuntimeError("Redis pool not initialized. Call initialize() first.")
        return self._pool

    async def close(self):
        if self._pool:
            await self._pool.close()


redis_pool = RedisPool()


async def get_redis() -> aioredis.Redis:
    return redis_pool.client
