from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.models import MarketTick
from app.service.market import market_service


def test_manual_market_refresh_can_generate_klines(monkeypatch) -> None:
    async def fake_real_ticks() -> tuple[list[MarketTick], str]:
        return (
            [MarketTick(symbol="AAPL", price=180.0, change=0.0, volume=1000, ts=1_800_000_000_000)],
            "real_yahoo",
        )

    monkeypatch.setattr(market_service, "_real_ticks", fake_real_ticks)
    client = TestClient(app)

    refresh = client.post("/api/market/refresh-real")
    assert refresh.status_code == 200

    klines = client.get("/api/market/klines?symbol=AAPL&interval=1m&limit=5")
    assert klines.status_code == 200
    assert isinstance(klines.json(), list)
