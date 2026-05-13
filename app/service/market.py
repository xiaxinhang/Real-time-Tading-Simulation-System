from __future__ import annotations

import asyncio
import json
import os
import random
import time
from collections import deque
from typing import Awaitable, Callable, Deque, Dict, Optional

from app.core.redis_client import redis_client
from app.models.models import MarketTick

BroadcastFn = Callable[[dict], Awaitable[None]]


class MarketService:
    def __init__(self) -> None:
        self.symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN"]
        self.tick_interval = float(os.getenv("MARKET_TICK_INTERVAL", "1.0"))
        self._last_prices: Dict[str, float] = {
            "AAPL": 180.0,
            "MSFT": 420.0,
            "TSLA": 240.0,
            "NVDA": 980.0,
            "AMZN": 185.0,
        }
        self._latest: Dict[str, MarketTick] = {}
        self._price_history: Deque[float] = deque(maxlen=20)
        self._task: Optional[asyncio.Task] = None
        self._broadcast: Optional[BroadcastFn] = None

    def set_broadcast_handler(self, fn: BroadcastFn) -> None:
        self._broadcast = fn

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def get_latest_snapshot(self) -> dict:
        return {
            "type": "snapshot",
            "ts": int(time.time() * 1000),
            "data": [tick.model_dump() for tick in self._latest.values()],
        }

    def get_recent_prices(self) -> list[float]:
        return list(self._price_history)

    async def _save_to_redis(self, ticks: list[MarketTick]) -> None:
        try:
            redis = await redis_client.get()
            for tick in ticks:
                await redis.set(f"market:latest:{tick.symbol}", tick.model_dump_json())
            all_snapshot = {
                "type": "snapshot",
                "ts": int(time.time() * 1000),
                "data": [t.model_dump() for t in ticks],
            }
            await redis.set("market:latest:all", json.dumps(all_snapshot))
        except Exception:
            # Degrade gracefully when Redis is temporarily unavailable.
            return

    def _next_tick(self, symbol: str) -> MarketTick:
        old_price = self._last_prices[symbol]
        drift = random.uniform(-0.02, 0.02)
        new_price = max(1.0, old_price * (1 + drift))
        self._last_prices[symbol] = new_price
        change = (new_price - old_price) / old_price
        volume = random.randint(100, 8000)
        tick = MarketTick(
            symbol=symbol,
            price=round(new_price, 2),
            change=round(change, 6),
            volume=volume,
            ts=int(time.time() * 1000),
        )
        self._latest[symbol] = tick
        self._price_history.append(tick.price)
        return tick

    async def _run_loop(self) -> None:
        while True:
            ticks = [self._next_tick(symbol) for symbol in self.symbols]
            await self._save_to_redis(ticks)
            if self._broadcast is not None:
                await self._broadcast(
                    {
                        "type": "snapshot",
                        "ts": int(time.time() * 1000),
                        "data": [tick.model_dump() for tick in ticks],
                    }
                )
            await asyncio.sleep(self.tick_interval)

    async def start(self) -> None:
        if self.is_running():
            return
        self._task = asyncio.create_task(self._run_loop(), name="market-tick-loop")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


market_service = MarketService()
