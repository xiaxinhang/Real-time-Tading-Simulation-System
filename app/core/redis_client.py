from __future__ import annotations

import os
from typing import Optional

from redis.asyncio import Redis


class RedisClient:
    def __init__(self) -> None:
        self._client: Optional[Redis] = None
        self._url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    async def connect(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(self._url, decode_responses=True)
        return self._client

    async def get(self) -> Redis:
        return await self.connect()

    async def ping(self) -> bool:
        try:
            client = await self.get()
            return bool(await client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


redis_client = RedisClient()
