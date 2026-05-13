from __future__ import annotations

import time
import uuid
from typing import Dict, List

from fastapi import HTTPException

from app.core.redis_client import redis_client
from app.models.models import OrderResponse, PlaceOrderRequest, PortfolioResponse, Position, UserAccount
from app.service.market import market_service


class TradeService:
    def __init__(self) -> None:
        self._accounts: Dict[str, UserAccount] = {}
        self._orders: Dict[str, OrderResponse] = {}
        self._fills_by_user: Dict[str, List[OrderResponse]] = {}

    def _get_or_create_account(self, user_id: str) -> UserAccount:
        if user_id not in self._accounts:
            self._accounts[user_id] = UserAccount(user_id=user_id)
        return self._accounts[user_id]

    async def place_order(self, req: PlaceOrderRequest) -> OrderResponse:
        snapshot = market_service.get_latest_snapshot()
        ticks = {item["symbol"]: item for item in snapshot.get("data", [])}
        tick = ticks.get(req.symbol)
        if tick is None:
            raise HTTPException(status_code=400, detail=f"No market price for symbol={req.symbol}")

        price = float(tick["price"])
        qty = int(req.quantity)
        notional = round(price * qty, 2)
        account = self._get_or_create_account(req.user_id)

        if req.side == "buy":
            if account.cash < notional:
                raise HTTPException(status_code=400, detail="Insufficient cash")
            account.cash = round(account.cash - notional, 2)
            pos = account.positions.get(req.symbol, {"quantity": 0, "avg_price": 0.0})
            old_qty = int(pos["quantity"])
            old_avg = float(pos["avg_price"])
            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + (qty * price)) / new_qty
            account.positions[req.symbol] = {"quantity": new_qty, "avg_price": round(new_avg, 4)}
        else:
            pos = account.positions.get(req.symbol, {"quantity": 0, "avg_price": 0.0})
            old_qty = int(pos["quantity"])
            if old_qty < qty:
                raise HTTPException(status_code=400, detail="Insufficient position")
            avg_price = float(pos["avg_price"])
            realized = (price - avg_price) * qty
            account.realized_pnl = round(account.realized_pnl + realized, 2)
            account.cash = round(account.cash + notional, 2)
            remaining = old_qty - qty
            if remaining == 0:
                account.positions.pop(req.symbol, None)
            else:
                account.positions[req.symbol] = {"quantity": remaining, "avg_price": avg_price}

        order = OrderResponse(
            order_id=str(uuid.uuid4()),
            user_id=req.user_id,
            symbol=req.symbol,
            side=req.side,
            fill_price=price,
            fill_qty=qty,
            notional=notional,
            ts=int(time.time() * 1000),
        )
        self._orders[order.order_id] = order
        self._fills_by_user.setdefault(req.user_id, []).append(order)
        await self._persist_trade(order)
        return order

    async def _persist_trade(self, order: OrderResponse) -> None:
        try:
            redis = await redis_client.get()
            await redis.lpush(f"trade:orders:{order.user_id}", order.model_dump_json())
            await redis.lpush(f"trade:fills:{order.user_id}", order.model_dump_json())
        except Exception:
            return

    def get_order(self, order_id: str) -> OrderResponse:
        order = self._orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def get_user_portfolio(self, user_id: str) -> PortfolioResponse:
        account = self._get_or_create_account(user_id)
        snapshot = market_service.get_latest_snapshot()
        ticks = {item["symbol"]: item for item in snapshot.get("data", [])}

        positions: list[Position] = []
        total_unrealized = 0.0
        exposure = 0.0
        for symbol, raw in account.positions.items():
            qty = int(raw["quantity"])
            avg_price = float(raw["avg_price"])
            mkt_price = float(ticks.get(symbol, {}).get("price", avg_price))
            unrealized = round((mkt_price - avg_price) * qty, 2)
            total_unrealized += unrealized
            exposure += mkt_price * qty
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=qty,
                    avg_price=round(avg_price, 4),
                    market_price=round(mkt_price, 2),
                    unrealized_pnl=unrealized,
                )
            )

        equity = round(account.cash + exposure, 2)
        return PortfolioResponse(
            user_id=user_id,
            cash=round(account.cash, 2),
            realized_pnl=round(account.realized_pnl, 2),
            total_equity=equity,
            positions=positions,
        )

    def get_user_fills(self, user_id: str) -> list[OrderResponse]:
        return self._fills_by_user.get(user_id, [])


trade_service = TradeService()
