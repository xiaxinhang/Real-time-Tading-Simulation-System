from __future__ import annotations

"""Database placeholder for future persistent storage integration."""


class Database:
    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None


database = Database()
