from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque

from app.domain.orders import Order, OrderSide, OrderStatus


@dataclass(frozen=True, slots=True)
class PriceLevel:
    price: float
    quantity: int
    order_count: int


class OrderBook:
    """In-memory price-time priority order book for one symbol."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._bids: dict[float, Deque[Order]] = {}
        self._asks: dict[float, Deque[Order]] = {}

    def add(self, order: Order) -> None:
        if order.limit_price is None:
            raise ValueError("Only limit orders can rest on the book")
        side = self._bids if order.side == OrderSide.BUY else self._asks
        side.setdefault(order.limit_price, deque()).append(order)
        order.status = OrderStatus.OPEN

    def best_bid(self) -> Order | None:
        return self._best(self._bids, reverse=True)

    def best_ask(self) -> Order | None:
        return self._best(self._asks, reverse=False)

    def remove_empty_levels(self) -> None:
        for book in (self._bids, self._asks):
            for price in list(book.keys()):
                queue = book[price]
                while queue and queue[0].remaining_quantity == 0:
                    queue.popleft()
                if not queue:
                    del book[price]

    def snapshot(self, depth: int = 10) -> dict:
        return {
            "symbol": self.symbol,
            "bids": [asdict(level) for level in self._levels(self._bids, reverse=True, depth=depth)],
            "asks": [asdict(level) for level in self._levels(self._asks, reverse=False, depth=depth)],
        }

    def _best(self, book: dict[float, Deque[Order]], reverse: bool) -> Order | None:
        for price in sorted(book.keys(), reverse=reverse):
            queue = book[price]
            while queue and queue[0].remaining_quantity == 0:
                queue.popleft()
            if queue:
                return queue[0]
            del book[price]
        return None

    def _levels(self, book: dict[float, Deque[Order]], reverse: bool, depth: int) -> list[PriceLevel]:
        levels: list[PriceLevel] = []
        for price in sorted(book.keys(), reverse=reverse):
            live_orders = [order for order in book[price] if order.remaining_quantity > 0]
            if not live_orders:
                continue
            levels.append(
                PriceLevel(
                    price=price,
                    quantity=sum(order.remaining_quantity for order in live_orders),
                    order_count=len(live_orders),
                )
            )
            if len(levels) >= depth:
                break
        return levels
