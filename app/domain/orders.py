from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(StrEnum):
    ACCEPTED = "accepted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Order:
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    created_at: int
    limit_price: float | None = None
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.ACCEPTED
    fills: list[tuple[float, int]] = field(default_factory=list)

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    @property
    def is_market(self) -> bool:
        return self.order_type == OrderType.MARKET

    def can_cross(self, resting: "Order") -> bool:
        if self.is_market:
            return True
        if self.limit_price is None or resting.limit_price is None:
            return False
        if self.is_buy:
            return self.limit_price >= resting.limit_price
        return self.limit_price <= resting.limit_price

    def record_fill(self, price: float, quantity: int) -> None:
        previous_notional = self.avg_fill_price * self.filled_quantity
        new_notional = previous_notional + (price * quantity)
        self.filled_quantity += quantity
        self.avg_fill_price = round(new_notional / self.filled_quantity, 4)
        self.fills.append((price, quantity))
        self.status = OrderStatus.FILLED if self.remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED
