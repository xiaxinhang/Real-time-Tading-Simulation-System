from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow running this file directly: `python app/main.py`.
if __package__ is None or __package__ == "":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from app.api.order import router as order_router
from app.api.user import router as user_router
from app.core.redis_client import redis_client
from app.service.market import market_service
from app.websocket.market_ws import manager, router as ws_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await redis_client.connect()
    market_service.set_broadcast_handler(manager.broadcast)
    await market_service.start()
    try:
        yield
    finally:
        await market_service.stop()
        await redis_client.close()


app = FastAPI(title="Trading Simulation Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "tick_interval": market_service.tick_interval,
    }


@app.get("/api/market/snapshot")
async def market_snapshot() -> dict:
    return market_service.get_latest_snapshot()
