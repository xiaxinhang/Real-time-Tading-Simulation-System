from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


EventType = Literal["order_accepted", "order_filled", "order_partially_filled", "order_open", "trade"]


@dataclass(frozen=True, slots=True)
class TradeEvent:
    event_id: str
    event_type: EventType
    symbol: str
    order_id: str
    user_id: str
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    remaining_quantity: int
    counterparty_order_id: str | None
    ts: int
