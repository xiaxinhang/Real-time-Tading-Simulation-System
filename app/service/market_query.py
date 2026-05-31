from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MarketTick
from app.models.models import KlineResponse


class MarketQueryService:
    _interval_ms = {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
    }

    def klines(self, db: Session, symbol: str, interval: str = "1m", limit: int = 120) -> list[KlineResponse]:
        interval_ms = self._interval_ms.get(interval)
        if interval_ms is None:
            interval = "1m"
            interval_ms = self._interval_ms[interval]

        rows = db.scalars(
            select(MarketTick)
            .where(MarketTick.symbol == symbol.upper())
            .order_by(MarketTick.ts.desc())
            .limit(limit * 20)
        ).all()
        buckets: dict[int, list[MarketTick]] = {}
        for row in reversed(rows):
            bucket_ts = (row.ts // interval_ms) * interval_ms
            buckets.setdefault(bucket_ts, []).append(row)

        klines: list[KlineResponse] = []
        for bucket_ts, items in sorted(buckets.items())[-limit:]:
            prices = [item.price for item in items]
            klines.append(
                KlineResponse(
                    symbol=symbol.upper(),
                    interval=interval,
                    bucket_ts=bucket_ts,
                    open=items[0].price,
                    high=max(prices),
                    low=min(prices),
                    close=items[-1].price,
                    volume=sum(item.volume for item in items),
                )
            )
        return klines


market_query_service = MarketQueryService()
