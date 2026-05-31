from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.database import SessionLocal, init_db
from app.db.models import MarketTick
from app.main import app
from app.models.models import MarketTick as MarketTickPayload
from app.service.market import market_service


def _auth_headers(client: TestClient, suffix: str) -> dict[str, str]:
    username = f"strategy_user_{suffix}"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123", "email": f"{username}@example.com"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_ticks() -> None:
    market_service.set_latest_ticks_for_tests(
        [MarketTickPayload(symbol="AAPL", price=108.0, change=0.0, volume=100, ts=1_800_000_000_005)]
    )
    now = 1_800_000_000_000
    with SessionLocal() as db:
        db.execute(delete(MarketTick).where(MarketTick.symbol == "AAPL"))
        db.add_all(
            [
                MarketTick(symbol="AAPL", price=100.0, change=0.0, volume=100, ts=now + 1),
                MarketTick(symbol="AAPL", price=101.0, change=0.0, volume=100, ts=now + 2),
                MarketTick(symbol="AAPL", price=102.0, change=0.0, volume=100, ts=now + 3),
                MarketTick(symbol="AAPL", price=106.0, change=0.0, volume=100, ts=now + 4),
                MarketTick(symbol="AAPL", price=108.0, change=0.0, volume=100, ts=now + 5),
            ]
        )
        db.commit()


def test_create_start_stop_strategy() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])

    created = client.post(
        "/api/strategies",
        headers=headers,
        json={
            "name": "AAPL 均线测试",
            "strategy_type": "moving_average_cross",
            "symbol": "AAPL",
            "params": {"short_window": 2, "long_window": 5, "quantity": 1},
        },
    )
    assert created.status_code == 200
    strategy = created.json()
    assert strategy["status"] == "stopped"

    started = client.post(f"/api/strategies/{strategy['id']}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    stopped = client.post(f"/api/strategies/{strategy['id']}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"


def test_run_strategy_once_submits_order() -> None:
    init_db()
    client = TestClient(app)
    headers = _auth_headers(client, uuid.uuid4().hex[:8])
    _seed_ticks()

    created = client.post(
        "/api/strategies",
        headers=headers,
        json={
            "name": "AAPL 动量试跑",
            "strategy_type": "moving_average_cross",
            "symbol": "AAPL",
            "params": {"short_window": 2, "long_window": 5, "quantity": 1},
        },
    )
    assert created.status_code == 200
    strategy_id = created.json()["id"]

    run = client.post(f"/api/strategies/{strategy_id}/run-once", headers=headers)
    assert run.status_code == 200
    assert run.json()["trade_count"] == 1

    orders = client.get("/api/orders", headers=headers)
    assert orders.status_code == 200
    assert len(orders.json()) >= 1
