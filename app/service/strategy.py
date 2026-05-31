from __future__ import annotations

import asyncio
import json
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Account, MarketTick, Position, Strategy, User
from app.models.models import CreateOrderRequest, CreateStrategyRequest, StrategyResponse
from app.service.persistent_trade import persistent_trade_service


class StrategyService:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._interval = settings.strategy_tick_interval

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def create_strategy(self, db: Session, user: User, payload: CreateStrategyRequest) -> StrategyResponse:
        params = self._normalized_params(payload.strategy_type, payload.params)
        strategy = Strategy(
            user_id=user.id,
            name=payload.name,
            strategy_type=payload.strategy_type,
            status="stopped",
            symbol=payload.symbol.upper(),
            params_json=json.dumps(params),
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return self._response(strategy)

    def list_strategies(self, db: Session, user: User) -> list[StrategyResponse]:
        rows = db.scalars(
            select(Strategy).where(Strategy.user_id == user.id).order_by(Strategy.created_at.desc(), Strategy.id.desc())
        ).all()
        return [self._response(row) for row in rows]

    def start_strategy(self, db: Session, user: User, strategy_id: int) -> StrategyResponse:
        strategy = self._get_user_strategy(db, user, strategy_id)
        strategy.status = "running"
        db.commit()
        db.refresh(strategy)
        return self._response(strategy)

    def stop_strategy(self, db: Session, user: User, strategy_id: int) -> StrategyResponse:
        strategy = self._get_user_strategy(db, user, strategy_id)
        strategy.status = "stopped"
        db.commit()
        db.refresh(strategy)
        return self._response(strategy)

    def run_once(self, db: Session, user: User, strategy_id: int) -> StrategyResponse:
        strategy = self._get_user_strategy(db, user, strategy_id)
        self._evaluate_strategy(db, strategy)
        db.commit()
        db.refresh(strategy)
        return self._response(strategy)

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                with SessionLocal() as db:
                    strategies = db.scalars(select(Strategy).where(Strategy.status == "running")).all()
                    for strategy in strategies:
                        self._evaluate_strategy(db, strategy)
                    db.commit()
            except Exception:
                # Strategy execution must never stop market streaming or API availability.
                continue

    def _evaluate_strategy(self, db: Session, strategy: Strategy) -> None:
        if strategy.strategy_type == "moving_average_cross":
            self._evaluate_moving_average_cross(db, strategy)
        elif strategy.strategy_type == "grid":
            self._evaluate_grid(db, strategy)

    def _evaluate_moving_average_cross(self, db: Session, strategy: Strategy) -> None:
        params = self._params(strategy)
        short_window = int(params.get("short_window", 3))
        long_window = int(params.get("long_window", 5))
        quantity = int(params.get("quantity", 1))
        prices = self._latest_prices(db, strategy.symbol, long_window)
        if len(prices) < long_window:
            return

        short_avg = mean(prices[-short_window:])
        long_avg = mean(prices[-long_window:])
        signal = "buy" if short_avg > long_avg else "sell"
        if params.get("last_signal") == signal:
            return

        if signal == "sell" and not self._has_available_position(db, strategy.user_id, strategy.symbol, quantity):
            params["last_signal"] = signal
            strategy.params_json = json.dumps(params)
            return

        if self._submit_strategy_order(db, strategy, signal, quantity):
            params["last_signal"] = signal
            params["short_avg"] = round(short_avg, 4)
            params["long_avg"] = round(long_avg, 4)
            strategy.params_json = json.dumps(params)

    def _evaluate_grid(self, db: Session, strategy: Strategy) -> None:
        params = self._params(strategy)
        quantity = int(params.get("quantity", 1))
        grid_pct = float(params.get("grid_pct", 0.01))
        price = self._latest_price(db, strategy.symbol)
        if price is None:
            return

        base_price = float(params.get("base_price") or price)
        upper = base_price * (1 + grid_pct)
        lower = base_price * (1 - grid_pct)
        side: str | None = None
        if price <= lower:
            side = "buy"
        elif price >= upper and self._has_available_position(db, strategy.user_id, strategy.symbol, quantity):
            side = "sell"

        if side and self._submit_strategy_order(db, strategy, side, quantity):
            params["base_price"] = round(price, 4)
            params["last_side"] = side
            strategy.params_json = json.dumps(params)

    def _submit_strategy_order(self, db: Session, strategy: Strategy, side: str, quantity: int) -> bool:
        user = db.get(User, strategy.user_id)
        if user is None:
            return False
        before = strategy.trade_count
        try:
            order = persistent_trade_service.place_order(
                db,
                user,
                CreateOrderRequest(symbol=strategy.symbol, side=side, quantity=quantity, order_type="market"),
            )
        except Exception:
            return False
        if order.filled_quantity > 0:
            strategy.trade_count = before + 1
            return True
        return False

    def _latest_prices(self, db: Session, symbol: str, limit: int) -> list[float]:
        rows = db.scalars(
            select(MarketTick)
            .where(MarketTick.symbol == symbol.upper())
            .order_by(MarketTick.ts.desc(), MarketTick.id.desc())
            .limit(limit)
        ).all()
        return [row.price for row in reversed(rows)]

    def _latest_price(self, db: Session, symbol: str) -> float | None:
        row = db.scalar(
            select(MarketTick)
            .where(MarketTick.symbol == symbol.upper())
            .order_by(MarketTick.ts.desc(), MarketTick.id.desc())
            .limit(1)
        )
        return row.price if row else None

    def _has_available_position(self, db: Session, user_id: int, symbol: str, quantity: int) -> bool:
        account = db.scalar(select(Account).where(Account.user_id == user_id))
        if account is None:
            return False
        position = db.scalar(select(Position).where(Position.account_id == account.id, Position.symbol == symbol.upper()))
        return bool(position and position.available_quantity >= quantity)

    def _get_user_strategy(self, db: Session, user: User, strategy_id: int) -> Strategy:
        strategy = db.scalar(select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id))
        if strategy is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy

    def _normalized_params(self, strategy_type: str, params: dict[str, Any]) -> dict[str, Any]:
        if strategy_type == "moving_average_cross":
            return {
                "short_window": int(params.get("short_window", 3)),
                "long_window": int(params.get("long_window", 5)),
                "quantity": int(params.get("quantity", 1)),
            }
        if strategy_type == "grid":
            return {
                "grid_pct": float(params.get("grid_pct", 0.01)),
                "quantity": int(params.get("quantity", 1)),
                **({"base_price": float(params["base_price"])} if params.get("base_price") else {}),
            }
        return dict(params)

    def _params(self, strategy: Strategy) -> dict[str, Any]:
        try:
            return json.loads(strategy.params_json or "{}")
        except json.JSONDecodeError:
            return {}

    def _response(self, strategy: Strategy) -> StrategyResponse:
        return StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            strategy_type=strategy.strategy_type,  # type: ignore[arg-type]
            status=strategy.status,  # type: ignore[arg-type]
            symbol=strategy.symbol,
            params=self._params(strategy),
            realized_pnl=round(strategy.realized_pnl, 2),
            trade_count=strategy.trade_count,
            updated_at=strategy.updated_at.isoformat(),
        )


strategy_service = StrategyService()
