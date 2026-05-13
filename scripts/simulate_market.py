from __future__ import annotations

import asyncio
import json

from app.service.market import market_service


async def _print_tick(snapshot: dict) -> None:
    print(json.dumps(snapshot, ensure_ascii=False))


async def main() -> None:
    market_service.set_broadcast_handler(_print_tick)
    await market_service.start()
    try:
        await asyncio.sleep(10)
    finally:
        await market_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
