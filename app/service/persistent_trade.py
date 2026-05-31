from __future__ import annotations

import time
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, CashFlow, Order as DbOrder, Position, Trade, User
from app.domain.events import TradeEvent
from app.domain.matching_engine import MatchingEngine
from app.domain.orders import Order, OrderSide, OrderStatus, OrderType
from app.models.models import CreateOrderRequest, DbOrderResponse, DbTradeResponse
from app.service.market import market_service


class PersistentTradeService:
    def __init__(self) -> None:
        self._engine = MatchingEngine()
        self._domain_orders: dict[str, Order] = {}
        self._applied_fill_counts: dict[str, int] = {}
        self._liquidity_seeded: set[str] = set()

    def place_order(self, db: Session, user: User, payload: CreateOrderRequest) -> DbOrderResponse:
        symbol = payload.symbol.upper()
        reference_price = self._reference_price(symbol)
        self._seed_liquidity(symbol, reference_price)

        account = self._account_for_user(db, user)
        order_id = str(uuid.uuid4())
        reserve_amount = 0.0
        reserve_quantity = 0
        status = "accepted"

        try:
            reserve_amount, reserve_quantity = self._reserve_for_order(db, account, payload, symbol, reference_price)
        except HTTPException:
            db_order = self._create_db_order(
                db,
                user=user,
                order_id=order_id,
                payload=payload,
                symbol=symbol,
                status="rejected",
                reserve_amount=0.0,
                reserve_quantity=0,
            )
            db.commit()
            raise

        db_order = self._create_db_order(
            db,
            user=user,
            order_id=order_id,
            payload=payload,
            symbol=symbol,
            status=status,
            reserve_amount=reserve_amount,
            reserve_quantity=reserve_quantity,
        )

        domain_order = Order(
            order_id=order_id,
            user_id=str(user.id),
            symbol=symbol,
            side=OrderSide(payload.side),
            quantity=payload.quantity,
            order_type=OrderType(payload.order_type),
            limit_price=round(payload.limit_price, 2) if payload.limit_price is not None else None,
            created_at=int(time.time() * 1000),
        )
        self._domain_orders[order_id] = domain_order
        events = self._engine.submit(domain_order)
        self._sync_db_order_from_domain(db_order, domain_order)
        self._apply_execution_side_effects(db, events, domain_order)
        db.commit()
        db.refresh(db_order)
        return self._order_response(db_order)

    def cancel_order(self, db: Session, user: User, order_id: str) -> DbOrderResponse:
        db_order = self._get_user_order(db, user, order_id)
        if db_order.status not in {"open", "partially_filled", "accepted"}:
            raise HTTPException(status_code=400, detail=f"Order cannot be cancelled from status={db_order.status}")

        domain_order = self._domain_orders.get(order_id)
        if domain_order is not None:
            self._engine.cancel(db_order.symbol, order_id)
            domain_order.status = OrderStatus.CANCELLED

        account = self._account_for_user(db, user)
        self._release_order_reserve(db, account, db_order, "cancel_release")
        db_order.status = "cancelled"
        db_order.remaining_quantity = max(db_order.quantity - db_order.filled_quantity, 0)
        db.commit()
        db.refresh(db_order)
        return self._order_response(db_order)

    def list_orders(self, db: Session, user: User) -> list[DbOrderResponse]:
        rows = db.scalars(
            select(DbOrder).where(DbOrder.user_id == user.id).order_by(DbOrder.created_at.desc(), DbOrder.id.desc())
        ).all()
        return [self._order_response(row) for row in rows]

    def get_order(self, db: Session, user: User, order_id: str) -> DbOrderResponse:
        return self._order_response(self._get_user_order(db, user, order_id))

    def list_trades(self, db: Session, user: User) -> list[DbTradeResponse]:
        rows = db.scalars(
            select(Trade).where(Trade.user_id == user.id).order_by(Trade.created_at.desc(), Trade.id.desc())
        ).all()
        return [
            DbTradeResponse(
                trade_id=row.trade_id,
                order_id=row.order_id,
                symbol=row.symbol,
                side=row.side,  # type: ignore[arg-type]
                price=round(row.price, 4),
                quantity=row.quantity,
                notional=round(row.notional, 2),
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]

    def _reserve_for_order(
        self,
        db: Session,
        account: Account,
        payload: CreateOrderRequest,
        symbol: str,
        reference_price: float,
    ) -> tuple[float, int]:
        if payload.side == "buy":
            reserve_price = payload.limit_price if payload.order_type == "limit" else reference_price * 1.01
            reserve_amount = round(float(reserve_price or 0.0) * payload.quantity, 2)
            if account.available_cash < reserve_amount:
                raise HTTPException(status_code=400, detail="Insufficient available cash")
            account.available_cash = round(account.available_cash - reserve_amount, 2)
            account.frozen_cash = round(account.frozen_cash + reserve_amount, 2)
            self._cash_flow(db, account.user_id, "freeze_cash", -reserve_amount, account.available_cash)
            return reserve_amount, 0

        position = self._position_for_update(db, account, symbol)
        if position is None or position.available_quantity < payload.quantity:
            raise HTTPException(status_code=400, detail="Insufficient available position")
        position.available_quantity -= payload.quantity
        position.frozen_quantity += payload.quantity
        return 0.0, payload.quantity

    def _apply_execution_side_effects(self, db: Session, events: list[TradeEvent], incoming: Order) -> None:
        touched = {incoming.order_id}
        for event in events:
            if event.counterparty_order_id:
                touched.add(event.counterparty_order_id)

        for order_id in touched:
            domain_order = self._domain_orders.get(order_id)
            if domain_order is None or domain_order.user_id == "market-maker":
                continue
            db_order = db.scalar(select(DbOrder).where(DbOrder.order_id == order_id))
            if db_order is None:
                continue
            self._apply_new_fills(db, domain_order, db_order)
            self._sync_db_order_from_domain(db_order, domain_order)
            if db_order.status in {"filled", "rejected"}:
                account = db.scalar(select(Account).where(Account.user_id == db_order.user_id))
                if account is not None:
                    self._release_order_reserve(db, account, db_order, "release_remaining")

    def _apply_new_fills(self, db: Session, domain_order: Order, db_order: DbOrder) -> None:
        applied_count = self._applied_fill_counts.get(domain_order.order_id, 0)
        new_fills = domain_order.fills[applied_count:]
        if not new_fills:
            return

        account = db.scalar(select(Account).where(Account.user_id == db_order.user_id))
        if account is None:
            return

        for price, quantity in new_fills:
            notional = round(price * quantity, 2)
            db.add(
                Trade(
                    trade_id=str(uuid.uuid4()),
                    order_id=db_order.order_id,
                    user_id=db_order.user_id,
                    symbol=db_order.symbol,
                    side=db_order.side,
                    price=price,
                    quantity=quantity,
                    notional=notional,
                )
            )
            if db_order.side == "buy":
                self._apply_buy_fill(db, account, db_order, price, quantity, notional)
            else:
                self._apply_sell_fill(db, account, db_order, price, quantity, notional)

        self._applied_fill_counts[domain_order.order_id] = len(domain_order.fills)

    def _apply_buy_fill(
        self,
        db: Session,
        account: Account,
        db_order: DbOrder,
        price: float,
        quantity: int,
        notional: float,
    ) -> None:
        reserve_per_share = db_order.frozen_amount / max(db_order.remaining_quantity, 1)
        reserved_portion = round(min(db_order.frozen_amount, reserve_per_share * quantity), 2)
        db_order.remaining_quantity = max(db_order.remaining_quantity - quantity, 0)
        account.cash = round(account.cash - notional, 2)
        account.frozen_cash = round(max(account.frozen_cash - reserved_portion, 0.0), 2)
        account.available_cash = round(account.available_cash + max(reserved_portion - notional, 0.0), 2)
        db_order.frozen_amount = round(max(db_order.frozen_amount - reserved_portion, 0.0), 2)
        self._cash_flow(db, account.user_id, "buy_fill", -notional, account.available_cash, db_order.order_id)

        position = self._position_for_update(db, account, db_order.symbol)
        if position is None:
            position = Position(account_id=account.id, symbol=db_order.symbol)
            db.add(position)
            db.flush()
        old_quantity = position.quantity
        new_quantity = old_quantity + quantity
        position.avg_price = round(((old_quantity * position.avg_price) + notional) / new_quantity, 4)
        position.quantity = new_quantity
        position.available_quantity += quantity

    def _apply_sell_fill(
        self,
        db: Session,
        account: Account,
        db_order: DbOrder,
        price: float,
        quantity: int,
        notional: float,
    ) -> None:
        position = self._position_for_update(db, account, db_order.symbol)
        if position is None:
            return
        realized = round((price - position.avg_price) * quantity, 2)
        db_order.remaining_quantity = max(db_order.remaining_quantity - quantity, 0)
        position.quantity = max(position.quantity - quantity, 0)
        position.frozen_quantity = max(position.frozen_quantity - quantity, 0)
        db_order.frozen_quantity = max(db_order.frozen_quantity - quantity, 0)
        account.cash = round(account.cash + notional, 2)
        account.available_cash = round(account.available_cash + notional, 2)
        account.realized_pnl = round(account.realized_pnl + realized, 2)
        self._cash_flow(db, account.user_id, "sell_fill", notional, account.available_cash, db_order.order_id)

    def _release_order_reserve(self, db: Session, account: Account, db_order: DbOrder, flow_type: str) -> None:
        if db_order.side == "buy" and db_order.frozen_amount > 0:
            amount = round(db_order.frozen_amount, 2)
            account.frozen_cash = round(max(account.frozen_cash - amount, 0.0), 2)
            account.available_cash = round(account.available_cash + amount, 2)
            db_order.frozen_amount = 0.0
            self._cash_flow(db, account.user_id, flow_type, amount, account.available_cash, db_order.order_id)
        if db_order.side == "sell" and db_order.frozen_quantity > 0:
            position = self._position_for_update(db, account, db_order.symbol)
            if position is not None:
                position.frozen_quantity = max(position.frozen_quantity - db_order.frozen_quantity, 0)
                position.available_quantity += db_order.frozen_quantity
            db_order.frozen_quantity = 0

    def _create_db_order(
        self,
        db: Session,
        user: User,
        order_id: str,
        payload: CreateOrderRequest,
        symbol: str,
        status: str,
        reserve_amount: float,
        reserve_quantity: int,
    ) -> DbOrder:
        db_order = DbOrder(
            order_id=order_id,
            user_id=user.id,
            symbol=symbol,
            side=payload.side,
            order_type=payload.order_type,
            status=status,
            quantity=payload.quantity,
            filled_quantity=0,
            remaining_quantity=payload.quantity,
            limit_price=payload.limit_price,
            avg_fill_price=0.0,
            frozen_amount=reserve_amount,
            frozen_quantity=reserve_quantity,
        )
        db.add(db_order)
        db.flush()
        return db_order

    def _sync_db_order_from_domain(self, db_order: DbOrder, domain_order: Order) -> None:
        db_order.status = domain_order.status.value
        db_order.filled_quantity = domain_order.filled_quantity
        db_order.remaining_quantity = domain_order.remaining_quantity
        db_order.avg_fill_price = domain_order.avg_fill_price

    def _reference_price(self, symbol: str) -> float:
        return market_service.reference_price(symbol)

    def _seed_liquidity(self, symbol: str, reference_price: float) -> None:
        if symbol in self._liquidity_seeded:
            return
        self._engine.seed_liquidity(symbol, reference_price)
        self._liquidity_seeded.add(symbol)

    def _account_for_user(self, db: Session, user: User) -> Account:
        account = db.scalar(select(Account).where(Account.user_id == user.id))
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return account

    def _get_user_order(self, db: Session, user: User, order_id: str) -> DbOrder:
        order = db.scalar(select(DbOrder).where(DbOrder.user_id == user.id, DbOrder.order_id == order_id))
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def _position_for_update(self, db: Session, account: Account, symbol: str) -> Position | None:
        return db.scalar(select(Position).where(Position.account_id == account.id, Position.symbol == symbol))

    def _cash_flow(
        self,
        db: Session,
        user_id: int,
        flow_type: str,
        amount: float,
        balance_after: float,
        ref_id: str | None = None,
    ) -> None:
        db.add(
            CashFlow(
                user_id=user_id,
                flow_type=flow_type,
                amount=amount,
                balance_after=round(balance_after, 2),
                ref_id=ref_id,
            )
        )

    def _order_response(self, row: DbOrder) -> DbOrderResponse:
        return DbOrderResponse(
            order_id=row.order_id,
            symbol=row.symbol,
            side=row.side,  # type: ignore[arg-type]
            order_type=row.order_type,  # type: ignore[arg-type]
            status=row.status,  # type: ignore[arg-type]
            quantity=row.quantity,
            filled_quantity=row.filled_quantity,
            remaining_quantity=row.remaining_quantity,
            limit_price=row.limit_price,
            avg_fill_price=round(row.avg_fill_price, 4),
            frozen_amount=round(row.frozen_amount, 2),
            frozen_quantity=row.frozen_quantity,
            created_at=row.created_at.isoformat(),
        )


persistent_trade_service = PersistentTradeService()
