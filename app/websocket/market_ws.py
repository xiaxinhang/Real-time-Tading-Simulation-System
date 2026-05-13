from __future__ import annotations

import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis_client import redis_client

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        text = json.dumps(payload)
        for conn in self._connections:
            try:
                await conn.send_text(text)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        redis = await redis_client.get()
        raw = await redis.get("market:latest:all")
        if raw:
            await websocket.send_text(raw)
    except Exception:
        pass

    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=20)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)
