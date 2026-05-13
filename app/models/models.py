from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


Side = Literal["buy", "sell"]


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


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    symbol: str
    side: Side
    status: Literal["filled"] = "filled"
    fill_price: float
    fill_qty: int
    notional: float
    ts: int


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
