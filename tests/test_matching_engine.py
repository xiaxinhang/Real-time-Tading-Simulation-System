from __future__ import annotations

from app.domain.matching_engine import MatchingEngine
from app.domain.orders import Order, OrderSide, OrderStatus, OrderType


def test_limit_order_can_rest_open_on_book() -> None:
    engine = MatchingEngine()
    order = Order(
        order_id="order-1",
        user_id="user-1",
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.LIMIT,
        limit_price=100.0,
        created_at=1,
    )

    events = engine.submit(order)

    assert order.status == OrderStatus.OPEN
    assert order.remaining_quantity == 10
    assert any(event.event_type == "order_open" for event in events)
    assert engine.book_snapshot("AAPL")["bids"][0]["quantity"] == 10


def test_market_order_matches_seeded_liquidity() -> None:
    engine = MatchingEngine()
    engine.seed_liquidity("AAPL", reference_price=100.0, quantity=100)
    order = Order(
        order_id="order-2",
        user_id="user-1",
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
        created_at=1,
    )

    events = engine.submit(order)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 5
    assert any(event.event_type == "trade" for event in events)
