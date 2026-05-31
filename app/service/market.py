from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import time
from collections import deque
from typing import Awaitable, Callable, Deque, Dict, Optional

import httpx
from fastapi import HTTPException, status

from app.core.redis_client import redis_client
from app.db.database import SessionLocal
from app.db.models import MarketTick as MarketTickRecord
from app.models.models import MarketTick

BroadcastFn = Callable[[dict], Awaitable[None]]


def _bounded_seconds(raw: str | None, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(raw) if raw is not None else default
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


class MarketService:
    def __init__(self) -> None:
        self.symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN"]
        raw_interval = os.getenv("MARKET_REFRESH_INTERVAL", os.getenv("MARKET_TICK_INTERVAL"))
        self.refresh_interval = _bounded_seconds(raw_interval, default=30.0, minimum=30.0, maximum=60.0)
        self.tick_interval = self.refresh_interval
        self.market_data_timeout = float(os.getenv("MARKET_DATA_TIMEOUT", "5.0"))
        self.max_data_age_ms = int(float(os.getenv("MARKET_DATA_MAX_AGE_SECONDS", "90")) * 1000)
        self._latest: Dict[str, MarketTick] = {}
        self._price_history: Deque[float] = deque(maxlen=20)
        self._task: Optional[asyncio.Task] = None
        self._broadcast: Optional[BroadcastFn] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._refresh_lock = asyncio.Lock()
        self.last_data_source = "not_loaded"
        self.last_data_error = ""
        self.last_successful_pull_ts: int | None = None

    def set_broadcast_handler(self, fn: BroadcastFn) -> None:
        self._broadcast = fn

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def get_latest_snapshot(self) -> dict:
        now_ms = self._now_ms()
        return {
            "type": "snapshot",
            "ts": now_ms,
            "data": [tick.model_dump() for tick in self._latest.values()],
            "market_data_source": self.last_data_source,
            "market_data_error": self.last_data_error,
            "last_successful_pull_ts": self.last_successful_pull_ts,
            "market_data_stale": self.is_data_stale(now_ms),
            "max_data_age_ms": self.max_data_age_ms,
            "refresh_interval": self.refresh_interval,
        }

    def get_recent_prices(self) -> list[float]:
        return list(self._price_history)

    def is_data_stale(self, now_ms: int | None = None) -> bool:
        if self.last_successful_pull_ts is None:
            return True
        now = now_ms or self._now_ms()
        return now - self.last_successful_pull_ts > self.max_data_age_ms

    def reference_price(self, symbol: str) -> float:
        normalized = symbol.upper()
        if self.last_successful_pull_ts is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data is unavailable; pull real market data before trading",
            )
        if self.is_data_stale():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data is stale; refresh real market data before trading",
            )
        tick = self._latest.get(normalized)
        if tick is None:
            raise HTTPException(status_code=400, detail=f"No market price for symbol={normalized}")
        return float(tick.price)

    def set_latest_ticks_for_tests(self, ticks: list[MarketTick], source: str = "test_seed") -> None:
        self._apply_successful_ticks(ticks, source=source, pulled_at=self._now_ms())

    async def _save_to_redis(self, ticks: list[MarketTick]) -> None:
        try:
            redis = await redis_client.get()
            for tick in ticks:
                await redis.set(f"market:latest:{tick.symbol}", tick.model_dump_json())
            await redis.set("market:latest:all", json.dumps(self.get_latest_snapshot()))
        except Exception:
            return

    async def _save_to_db(self, ticks: list[MarketTick]) -> None:
        try:
            with SessionLocal() as db:
                db.add_all(
                    MarketTickRecord(
                        symbol=tick.symbol,
                        price=tick.price,
                        change=tick.change,
                        volume=tick.volume,
                        ts=tick.ts,
                    )
                    for tick in ticks
                )
                db.commit()
        except Exception:
            return

    async def _real_ticks_yahoo(self) -> list[MarketTick]:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.market_data_timeout)
        symbol_query = ",".join(self.symbols)
        last_error: Exception | None = None
        payload: dict = {}
        for attempt in range(3):
            try:
                response = await self._http.get(
                    "https://query1.finance.yahoo.com/v7/finance/quote",
                    params={"symbols": symbol_query},
                )
                response.raise_for_status()
                payload = response.json()
                last_error = None
                break
            except Exception as error:
                last_error = error
                if attempt < 2:
                    await asyncio.sleep(1.0)
        if last_error is not None:
            raise last_error

        rows = payload.get("quoteResponse", {}).get("result", [])
        by_symbol = {str(item.get("symbol", "")).upper(): item for item in rows}
        ticks: list[MarketTick] = []
        now_ms = self._now_ms()
        for symbol in self.symbols:
            row = by_symbol.get(symbol)
            if row is None:
                raise ValueError(f"yahoo missing symbol={symbol}")
            raw_price = row.get("regularMarketPrice")
            if raw_price is None:
                raise ValueError(f"yahoo missing regularMarketPrice for symbol={symbol}")

            change_pct = row.get("regularMarketChangePercent")
            price = max(1.0, float(raw_price))
            change = (
                float(change_pct) / 100.0
                if change_pct is not None
                else self._change_from_previous(symbol, price)
            )
            tick = MarketTick(
                symbol=symbol,
                price=round(price, 2),
                change=round(change, 6),
                volume=int(row.get("regularMarketVolume") or 0),
                ts=now_ms,
            )
            ticks.append(tick)
        return ticks

    async def _real_ticks_stooq(self) -> list[MarketTick]:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.market_data_timeout)

        async def fetch_one(symbol: str) -> dict:
            response = await self._http.get(
                "https://stooq.com/q/l/",
                params={
                    "s": f"{symbol.lower()}.us",
                    "f": "sd2t2ohlcv",
                    "h": "1",
                    "e": "csv",
                },
            )
            response.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(response.text)))
            if not rows:
                raise ValueError(f"stooq empty response for symbol={symbol}")
            return rows[0]

        rows = await asyncio.gather(*(fetch_one(symbol) for symbol in self.symbols))
        ticks: list[MarketTick] = []
        now_ms = self._now_ms()
        for symbol, row in zip(self.symbols, rows):
            close_raw = str(row.get("Close", "N/D")).strip()
            if close_raw in {"N/D", ""}:
                raise ValueError(f"stooq invalid close for symbol={symbol}")

            open_price = self._safe_float(row.get("Open"))
            price = max(1.0, float(close_raw))
            change = (
                (price - open_price) / open_price
                if open_price and open_price > 0
                else self._change_from_previous(symbol, price)
            )
            volume_raw = str(row.get("Volume", "0")).strip()
            ticks.append(
                MarketTick(
                    symbol=symbol,
                    price=round(price, 2),
                    change=round(change, 6),
                    volume=int(volume_raw) if volume_raw.isdigit() else 0,
                    ts=now_ms,
                )
            )
        return ticks

    async def _real_ticks(self) -> tuple[list[MarketTick], str]:
        try:
            return await self._real_ticks_yahoo(), "real_yahoo"
        except Exception as yahoo_error:
            try:
                return await self._real_ticks_stooq(), "real_stooq"
            except Exception as stooq_error:
                raise RuntimeError(
                    f"yahoo_error={type(yahoo_error).__name__}: {yahoo_error}; "
                    f"stooq_error={type(stooq_error).__name__}: {stooq_error}"
                ) from stooq_error

    def _apply_successful_ticks(self, ticks: list[MarketTick], source: str, pulled_at: int) -> None:
        self._latest = {tick.symbol: tick for tick in ticks}
        self.last_successful_pull_ts = pulled_at
        self.last_data_source = source
        self.last_data_error = ""
        for tick in ticks:
            self._price_history.append(tick.price)

    async def _publish_ticks(self, ticks: list[MarketTick], *, persist: bool) -> None:
        await self._save_to_redis(ticks)
        if persist:
            await self._save_to_db(ticks)
        if self._broadcast is not None:
            await self._broadcast(self.get_latest_snapshot())

    async def refresh_real_now(self) -> dict:
        async with self._refresh_lock:
            pulled_at = self._now_ms()
            persist = False
            try:
                ticks, source = await self._real_ticks()
                self._apply_successful_ticks(ticks, source=source, pulled_at=pulled_at)
                persist = True
            except Exception as error:
                self.last_data_source = "fallback_cache" if self._latest else "unavailable"
                self.last_data_error = f"{type(error).__name__}: {error}"
                ticks = list(self._latest.values())

            if ticks:
                await self._publish_ticks(ticks, persist=persist)
            return {
                "ok": persist,
                "snapshot": self.get_latest_snapshot(),
            }

    async def _run_loop(self) -> None:
        while True:
            await self.refresh_real_now()
            await asyncio.sleep(self.refresh_interval)

    async def start(self) -> None:
        if self.is_running():
            return
        self._task = asyncio.create_task(self._run_loop(), name="market-refresh-loop")

    async def stop(self) -> None:
        if self._task is None:
            if self._http is not None:
                await self._http.aclose()
                self._http = None
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _change_from_previous(self, symbol: str, price: float) -> float:
        previous = self._latest.get(symbol)
        if previous is None or previous.price <= 0:
            return 0.0
        return (price - previous.price) / previous.price

    def _safe_float(self, value: object) -> float | None:
        try:
            text = str(value).strip()
            return float(text) if text and text != "N/D" else None
        except (TypeError, ValueError):
            return None

    def _now_ms(self) -> int:
        return int(time.time() * 1000)


market_service = MarketService()
