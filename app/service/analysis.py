from __future__ import annotations

import time
from statistics import pstdev

from app.models.models import MarketMetricsResponse, UserMetricsResponse
from app.service.market import market_service
from app.service.trade import trade_service


class AnalysisService:
    def market_metrics(self) -> MarketMetricsResponse:
        snapshot = market_service.get_latest_snapshot()
        data = snapshot.get("data", [])
        prices = [float(i["price"]) for i in data]
        volumes = [int(i["volume"]) for i in data]
        changes = [abs(float(i["change"])) for i in data]

        total_volume = sum(volumes)
        total_notional = round(sum(p * v for p, v in zip(prices, volumes)), 2)
        avg_price = round(sum(prices) / len(prices), 4) if prices else 0.0
        avg_abs_change_pct = round((sum(changes) / len(changes)) * 100, 4) if changes else 0.0

        recent = market_service.get_recent_prices()
        vol = round(pstdev(recent), 6) if len(recent) > 1 else 0.0

        return MarketMetricsResponse(
            ts=int(time.time() * 1000),
            symbol_count=len(data),
            avg_price=avg_price,
            total_volume=total_volume,
            total_notional=total_notional,
            avg_abs_change_pct=avg_abs_change_pct,
            volatility_20=vol,
        )

    def user_metrics(self, user_id: str) -> UserMetricsResponse:
        fills = trade_service.get_user_fills(user_id)
        portfolio = trade_service.get_user_portfolio(user_id)

        wins = 0
        exposure_notional = 0.0
        position_distribution = {}
        total_unrealized = 0.0

        for p in portfolio.positions:
            notional = p.market_price * p.quantity
            exposure_notional += notional
            total_unrealized += p.unrealized_pnl
            position_distribution[p.symbol] = round(notional, 2)
            if p.unrealized_pnl > 0:
                wins += 1

        for fill in fills:
            if fill.side == "sell":
                wins += 1

        trade_count = len(fills)
        win_rate = round((wins / trade_count) * 100, 2) if trade_count > 0 else 0.0
        total_pnl = round(portfolio.realized_pnl + total_unrealized, 2)

        return UserMetricsResponse(
            user_id=user_id,
            ts=int(time.time() * 1000),
            trade_count=trade_count,
            win_rate=win_rate,
            realized_pnl=round(portfolio.realized_pnl, 2),
            unrealized_pnl=round(total_unrealized, 2),
            total_pnl=total_pnl,
            exposure_notional=round(exposure_notional, 2),
            position_distribution=position_distribution,
        )


analysis_service = AnalysisService()
