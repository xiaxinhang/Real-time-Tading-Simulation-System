from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Allow running this file directly: `python app/main.py`.
if __package__ is None or __package__ == "":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from app.api.account import router as account_router
from app.api.auth import router as auth_router
from app.api.order import router as order_router
from app.api.orders import router as orders_router
from app.api.strategies import router as strategies_router
from app.api.user import router as user_router
from app.core.config import settings
from app.core.redis_client import redis_client
from app.db.database import database
from app.service.market import market_service
from app.service.strategy import strategy_service
from app.service.trade import trade_service
from app.websocket.market_ws import manager, router as ws_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.connect()
    await redis_client.connect()
    market_service.set_broadcast_handler(manager.broadcast)
    trade_service.set_broadcast_handler(manager.broadcast)
    await market_service.start()
    await strategy_service.start()
    try:
        yield
    finally:
        await strategy_service.stop()
        await market_service.stop()
        await redis_client.close()
        await database.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(account_router)
app.include_router(orders_router)
app.include_router(strategies_router)
app.include_router(order_router)
app.include_router(user_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/system/status")
async def system_status() -> dict:
    redis_ok = await redis_client.ping()
    return {
        "market_loop_running": market_service.is_running(),
        "redis_connected": redis_ok,
        "ws_clients": manager.count,
        "tick_interval": market_service.refresh_interval,
        "refresh_interval": market_service.refresh_interval,
        "market_data_source": market_service.last_data_source,
        "market_data_error": market_service.last_data_error,
        "last_successful_pull_ts": market_service.last_successful_pull_ts,
        "market_data_stale": market_service.is_data_stale(),
        "max_data_age_ms": market_service.max_data_age_ms,
    }


@app.get("/api/market/snapshot")
async def market_snapshot() -> dict:
    return market_service.get_latest_snapshot()


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if settings.serve_frontend_dist and frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
