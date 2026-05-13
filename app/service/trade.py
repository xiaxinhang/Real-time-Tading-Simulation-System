from __future__ import annotations

import time
import uuid
import json
from dataclasses import asdict
from typing import Awaitable, Callable, Dict, List

from fastapi import HTTPException

from app.core.redis_client import redis_client
from app.domain.events import TradeEvent
from app.domain.matching_engine import MatchingEngine
from app.domain.orders import Order, OrderSide, OrderType
from app.models.models import OrderResponse, PlaceOrderRequest, PortfolioResponse, Position, UserAccount
from app.service.market import market_service

BroadcastFn = Callable[[dict], Awaitable[None]]


class TradeService:
    def __init__(self) -> None:
        self._accounts: Dict[str, UserAccount] = {}
        self._orders: Dict[str, Order] = {}
        self._responses: Dict[str, OrderResponse] = {}
        self._applied_fill_counts: Dict[str, int] = {}
        self._fills_by_user: Dict[str, List[OrderResponse]] = {}
        self._engine = MatchingEngine()
        self._broadcast: BroadcastFn | None = None
        self._liquidity_seeded: set[str] = set()

    def set_broadcast_handler(self, fn: BroadcastFn) -> None:
        self._broadcast = fn

    def _get_or_create_account(self, user_id: str) -> UserAccount:
        if user_id not in self._accounts:
            self._accounts[user_id] = UserAccount(user_id=user_id)
        return self._accounts[user_id]

    async def place_order(self, req: PlaceOrderRequest) -> OrderResponse:
        symbol = req.symbol.upper()
        reference_price = self._reference_price(symbol)
        account = self._get_or_create_account(req.user_id)
        self._validate_risk(req, account, reference_price)
        self._seed_liquidity(symbol, reference_price)

        order = Order(
            order_id=str(uuid.uuid4()),
            user_id=req.user_id,
            symbol=symbol,
            side=OrderSide(req.side),
            quantity=req.quantity,
            order_type=OrderType(req.order_type),
            limit_price=round(req.limit_price, 2) if req.limit_price is not None else None,
            created_at=int(time.time() * 1000),
        )

        self._orders[order.order_id] = order
        events = self._engine.submit(order)
        response = self._to_response(order)
        self._responses[order.order_id] = response

        filled_orders = self._apply_execution_side_effects(order, events)
        for filled_order in filled_orders:
            filled_response = self._to_response(filled_order)
            self._responses[filled_order.order_id] = filled_response
            if filled_order.user_id != "market-maker":
                self._fills_by_user.setdefault(filled_order.user_id, []).append(filled_response)

        await self._persist_order(response, events)
        await self._broadcast_events(events, response)
        return response

    def _reference_price(self, symbol: str) -> float:
        snapshot = market_service.get_latest_snapshot()
        ticks = {item["symbol"]: item for item in snapshot.get("data", [])}
        tick = ticks.get(symbol)
        if tick is None:
            raise HTTPException(status_code=400, detail=f"No market price for symbol={symbol}")
        return float(tick["price"])

    def _seed_liquidity(self, symbol: str, reference_price: float) -> None:
        if symbol in self._liquidity_seeded:
            return
        self._engine.seed_liquidity(symbol, reference_price)
        self._liquidity_seeded.add(symbol)

    def _validate_risk(self, req: PlaceOrderRequest, account: UserAccount, reference_price: float) -> None:
        qty = int(req.quantity)
        if req.side == "buy":
            worst_price = req.limit_price if req.order_type == "limit" else reference_price * 1.01
            required_cash = round(float(worst_price or 0.0) * qty, 2)
            if account.cash < required_cash:
                raise HTTPException(status_code=400, detail="Insufficient cash")
            return

        pos = account.positions.get(req.symbol.upper(), {"quantity": 0, "avg_price": 0.0})
        if int(pos["quantity"]) < qty:
            raise HTTPException(status_code=400, detail="Insufficient position")

    def _apply_execution_side_effects(self, incoming: Order, events: list[TradeEvent]) -> list[Order]:
        touched = {incoming.order_id}
        for event in events:
            if event.counterparty_order_id is not None:
                touched.add(event.counterparty_order_id)

        filled_orders: list[Order] = []
        for order_id in touched:
            order = self._orders.get(order_id)
            if order is None or order.user_id == "market-maker":
                continue
            if self._apply_new_fills(order):
                filled_orders.append(order)
        return filled_orders

    def _apply_new_fills(self, order: Order) -> bool:
        applied_count = self._applied_fill_counts.get(order.order_id, 0)
        new_fills = order.fills[applied_count:]
        if not new_fills:
            return False

        account = self._get_or_create_account(order.user_id)
        for price, qty in new_fills:
            notional = round(price * qty, 2)
            if order.side == OrderSide.BUY:
                account.cash = round(account.cash - notional, 2)
                pos = account.positions.get(order.symbol, {"quantity": 0, "avg_price": 0.0})
                old_qty = int(pos["quantity"])
                old_avg = float(pos["avg_price"])
                new_qty = old_qty + qty
                new_avg = ((old_qty * old_avg) + (qty * price)) / new_qty
                account.positions[order.symbol] = {"quantity": new_qty, "avg_price": round(new_avg, 4)}
            else:
                pos = account.positions.get(order.symbol, {"quantity": 0, "avg_price": 0.0})
                old_qty = int(pos["quantity"])
                avg_price = float(pos["avg_price"])
                realized = (price - avg_price) * qty
                account.realized_pnl = round(account.realized_pnl + realized, 2)
                account.cash = round(account.cash + notional, 2)
                remaining = old_qty - qty
                if remaining == 0:
                    account.positions.pop(order.symbol, None)
                else:
                    account.positions[order.symbol] = {"quantity": remaining, "avg_price": avg_price}
        self._applied_fill_counts[order.order_id] = len(order.fills)
        return True

    async def _persist_order(self, order: OrderResponse, events: list[TradeEvent]) -> None:
        try:
            redis = await redis_client.get()
            await redis.lpush(f"trade:orders:{order.user_id}", order.model_dump_json())
            if order.fill_qty > 0:
                await redis.lpush(f"trade:fills:{order.user_id}", order.model_dump_json())
            for event in events:
                await redis.lpush(f"trade:events:{order.symbol}", json.dumps(asdict(event)))
        except Exception:
            return

    async def _broadcast_events(self, events: list[TradeEvent], order: OrderResponse) -> None:
        if self._broadcast is None:
            return
        await self._broadcast(
            {
                "type": "trade_events",
                "order": order.model_dump(),
                "events": [asdict(event) for event in events],
                "ts": int(time.time() * 1000),
            }
        )

    def _to_response(self, order: Order) -> OrderResponse:
        return OrderResponse(
            order_id=order.order_id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.order_type.value,
            status=order.status.value,
            limit_price=order.limit_price,
            fill_price=order.avg_fill_price,
            fill_qty=order.filled_quantity,
            remaining_qty=order.remaining_quantity,
            notional=round(sum(price * qty for price, qty in order.fills), 2),
            ts=order.created_at,
        )

    def get_order(self, order_id: str) -> OrderResponse:
        order = self._responses.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def get_order_book(self, symbol: str, depth: int = 10) -> dict:
        return self._engine.book_snapshot(symbol.upper(), depth=depth)

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
