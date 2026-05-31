from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db.database import init_db
from app.main import app
from app.models.models import MarketTick
from app.service.market import market_service


def _auth_headers(client: TestClient, suffix: str) -> dict[str, str]:
    username = f"trade_user_{suffix}"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123", "email": f"{username}@example.com"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_market_price(symbol: str = "AAPL") -> float:
    tick = MarketTick(symbol=symbol, price=180.0, change=0.0, volume=1000, ts=1_800_000_000_000)
    market_service.set_latest_ticks_for_tests([tick])
    return tick.price


def test_limit_buy_order_freezes_and_cancel_releases_cash() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])
    price = _seed_market_price()
    limit_price = round(price * 0.5, 2)

    created = client.post(
        "/api/orders",
        headers=headers,
        json={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "limit",
            "limit_price": limit_price,
        },
    )
    assert created.status_code == 200
    order = created.json()
    assert order["status"] == "open"
    assert order["frozen_amount"] == round(limit_price * 10, 2)

    account_after_order = client.get("/api/account", headers=headers).json()
    assert account_after_order["frozen_cash"] == round(limit_price * 10, 2)
    assert account_after_order["available_cash"] == round(1_000_000.0 - (limit_price * 10), 2)

    cancelled = client.delete(f"/api/orders/{order['order_id']}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    account_after_cancel = client.get("/api/account", headers=headers).json()
    assert account_after_cancel["frozen_cash"] == 0.0
    assert account_after_cancel["available_cash"] == 1_000_000.0


def test_market_buy_creates_trade_and_position() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])
    _seed_market_price()

    created = client.post(
        "/api/orders",
        headers=headers,
        json={"symbol": "AAPL", "side": "buy", "quantity": 5, "order_type": "market"},
    )
    assert created.status_code == 200
    order = created.json()
    assert order["status"] == "filled"
    assert order["filled_quantity"] == 5
    assert order["frozen_amount"] == 0.0

    trades = client.get("/api/trades", headers=headers)
    assert trades.status_code == 200
    assert len(trades.json()) >= 1

    positions = client.get("/api/positions", headers=headers)
    assert positions.status_code == 200
    aapl = next(item for item in positions.json() if item["symbol"] == "AAPL")
    assert aapl["quantity"] == 5
    assert aapl["available_quantity"] == 5

    account = client.get("/api/account", headers=headers).json()
    assert account["cash"] < 1_000_000.0
    assert account["available_cash"] < 1_000_000.0


def test_order_rejects_stale_market_data() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])
    _seed_market_price()
    market_service.last_successful_pull_ts = 1

    created = client.post(
        "/api/orders",
        headers=headers,
        json={"symbol": "AAPL", "side": "buy", "quantity": 5, "order_type": "market"},
    )

    assert created.status_code == 503
    assert "stale" in created.json()["detail"]


def test_sell_order_reduces_position_after_market_fill() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])
    _seed_market_price()

    buy = client.post(
        "/api/orders",
        headers=headers,
        json={"symbol": "AAPL", "side": "buy", "quantity": 8, "order_type": "market"},
    )
    assert buy.status_code == 200
    assert buy.json()["status"] == "filled"

    sell = client.post(
        "/api/orders",
        headers=headers,
        json={"symbol": "AAPL", "side": "sell", "quantity": 3, "order_type": "market"},
    )
    assert sell.status_code == 200
    assert sell.json()["status"] == "filled"

    positions = client.get("/api/positions", headers=headers).json()
    aapl = next(item for item in positions if item["symbol"] == "AAPL")
    assert aapl["quantity"] == 5
    assert aapl["available_quantity"] == 5
    assert aapl["frozen_quantity"] == 0
