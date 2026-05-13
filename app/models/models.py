from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, model_validator


Side = Literal["buy", "sell"]
OrderKind = Literal["market", "limit"]
OrderState = Literal["accepted", "open", "partially_filled", "filled", "rejected", "cancelled"]


class MarketTick(BaseModel):
    type: Literal["tick"] = "tick"
    symbol: str
    price: float
    change: float
    volume: int
    ts: int


class PlaceOrderRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    symbol: str = Field(..., min_length=1, max_length=16)
    side: Side
    quantity: int = Field(..., gt=0)
    order_type: OrderKind = "market"
    limit_price: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_limit_price_for_limit_orders(self) -> "PlaceOrderRequest":
        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("limit_price is required for limit orders")
        return self


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    symbol: str
    side: Side
    order_type: OrderKind = "market"
    status: OrderState
    limit_price: float | None = None
    fill_price: float = 0.0
    fill_qty: int = 0
    remaining_qty: int = 0
    notional: float
    ts: int


class TradeEventResponse(BaseModel):
    event_id: str
    event_type: Literal["order_accepted", "order_filled", "order_partially_filled", "order_open", "trade"]
    symbol: str
    order_id: str
    user_id: str
    side: Side
    price: float
    quantity: int
    remaining_quantity: int
    counterparty_order_id: str | None
    ts: int


class OrderBookLevel(BaseModel):
    price: float
    quantity: int
    order_count: int


class OrderBookResponse(BaseModel):
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]


class Position(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    market_price: float
    unrealized_pnl: float


class PortfolioResponse(BaseModel):
    user_id: str
    cash: float
    realized_pnl: float
    total_equity: float
    positions: List[Position]


class UserAccount(BaseModel):
    user_id: str
    cash: float = 1_000_000.0
    realized_pnl: float = 0.0
    positions: Dict[str, Dict[str, float | int]] = Field(default_factory=dict)


class MarketMetricsResponse(BaseModel):
    ts: int
    symbol_count: int
    avg_price: float
    total_volume: int
    total_notional: float
    avg_abs_change_pct: float
    volatility_20: float


class UserMetricsResponse(BaseModel):
    user_id: str
    ts: int
    trade_count: int
    win_rate: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    exposure_notional: float
    position_distribution: Dict[str, float]
