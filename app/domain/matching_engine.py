from __future__ import annotations

import time
import uuid

from app.domain.events import TradeEvent
from app.domain.order_book import OrderBook
from app.domain.orders import Order, OrderSide, OrderStatus, OrderType


class MatchingEngine:
    def __init__(self) -> None:
        self._books: dict[str, OrderBook] = {}

    def submit(self, order: Order) -> list[TradeEvent]:
        book = self._book(order.symbol)
        events = [
            self._event(
                event_type="order_accepted",
                order=order,
                price=order.limit_price or 0.0,
                quantity=0,
                counterparty_order_id=None,
            )
        ]

        contra = book.best_ask if order.side == OrderSide.BUY else book.best_bid
        while order.remaining_quantity > 0:
            resting = contra()
            if resting is None or not order.can_cross(resting):
                break

            fill_qty = min(order.remaining_quantity, resting.remaining_quantity)
            fill_price = resting.limit_price
            if fill_price is None:
                break

            order.record_fill(fill_price, fill_qty)
            resting.record_fill(fill_price, fill_qty)
            events.append(
                self._event(
                    event_type="trade",
                    order=order,
                    price=fill_price,
                    quantity=fill_qty,
                    counterparty_order_id=resting.order_id,
                )
            )
            book.remove_empty_levels()

        if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
            book.add(order)
            events.append(
                self._event(
                    event_type="order_open",
                    order=order,
                    price=order.limit_price or 0.0,
                    quantity=0,
                    counterparty_order_id=None,
                )
            )
        elif order.remaining_quantity > 0:
            order.status = OrderStatus.REJECTED
        else:
            events.append(
                self._event(
                    event_type="order_filled",
                    order=order,
                    price=order.avg_fill_price,
                    quantity=order.filled_quantity,
                    counterparty_order_id=None,
                )
            )

        return events

    def seed_liquidity(self, symbol: str, reference_price: float, quantity: int = 100_000) -> None:
        book = self._book(symbol)
        bid = Order(
            order_id=f"mm-bid-{symbol}-{uuid.uuid4()}",
            user_id="market-maker",
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=round(reference_price * 0.999, 2),
            created_at=self._now_ms(),
        )
        ask = Order(
            order_id=f"mm-ask-{symbol}-{uuid.uuid4()}",
            user_id="market-maker",
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=round(reference_price * 1.001, 2),
            created_at=self._now_ms(),
        )
        book.add(bid)
        book.add(ask)

    def book_snapshot(self, symbol: str, depth: int = 10) -> dict:
        return self._book(symbol).snapshot(depth=depth)

    def _book(self, symbol: str) -> OrderBook:
        normalized = symbol.upper()
        if normalized not in self._books:
            self._books[normalized] = OrderBook(normalized)
        return self._books[normalized]

    def _event(
        self,
        event_type: str,
        order: Order,
        price: float,
        quantity: int,
        counterparty_order_id: str | None,
    ) -> TradeEvent:
        return TradeEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,  # type: ignore[arg-type]
            symbol=order.symbol,
            order_id=order.order_id,
            user_id=order.user_id,
            side=order.side.value,
            price=round(price, 4),
            quantity=quantity,
            remaining_quantity=order.remaining_quantity,
            counterparty_order_id=counterparty_order_id,
            ts=self._now_ms(),
        )

    def _now_ms(self) -> int:
        return int(time.time() * 1000)
