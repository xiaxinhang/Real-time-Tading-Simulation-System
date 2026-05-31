# Real-time Trading Simulation System

A FastAPI + Vue3 real-time trading simulation platform for learning backend engineering, exchange concepts, and full-stack system design.

## Current Capabilities
- FastAPI REST API and WebSocket market stream.
- Vue3 + Vite trading dashboard.
- Domain-level `Order`, `OrderBook`, `MatchingEngine`, and `TradeEvent`.
- Market and limit order flow with an in-memory matching engine.
- Redis cache for market snapshots and trade events.
- SQLite + SQLAlchemy persistence foundation.
- User registration, login, JWT authentication, and `/api/auth/me`.
- Persistent `User`, `Account`, `Position`, `Order`, `Trade`, `CashFlow`, `MarketTick`, and `Strategy` tables.
- Auto-created practice account with 1,000,000 initial cash after registration.
- Protected account, positions, and cashflow query APIs.
- Authenticated database-backed order APIs with market/limit orders, order status tracking, trade records, and cancellation.
- Account reserve logic for buy cash freezing, sell position freezing, fill settlement, and cancel release.
- Market tick persistence and simple K-line aggregation.
- Basic strategy execution with moving-average cross and grid strategies, including start/stop and manual run-once execution.
- Docker Compose skeleton for backend, frontend, Redis, and SQLite-backed data volume.
- Basic pytest coverage for auth/account, market K-lines, matching engine behavior, order placement, fill settlement, cancellation, and strategy execution.

## Architecture
- `app/core`: configuration, security, Redis client.
- `app/db`: SQLAlchemy engine, session dependency, ORM models.
- `app/domain`: exchange domain logic independent of API/storage.
- `app/service`: application services for account, market, analysis, and trading.
- `app/api`: FastAPI routers.
- `app/websocket`: WebSocket connection manager and market stream endpoint.
- `frontend`: Vue3 dashboard.

## Local Development
Install backend dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start backend API:

```powershell
$env:SERVE_FRONTEND_DIST="0"
$env:MARKET_REFRESH_INTERVAL="30"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start frontend HMR:

```powershell
cd frontend
npm install
npm run dev
```

Open:
- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

## Docker Compose
Build frontend once before backend image packaging if you want FastAPI to serve `dist`, or use the dedicated frontend container:

```powershell
docker compose up --build
```

Services:
- Backend API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- Redis: `127.0.0.1:6379`

## Important APIs
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/account`
- `GET /api/positions`
- `GET /api/cashflows`
- `POST /api/orders`
- `GET /api/orders`
- `GET /api/orders/{order_id}`
- `DELETE /api/orders/{order_id}`
- `GET /api/trades`
- `POST /api/strategies`
- `GET /api/strategies`
- `POST /api/strategies/{strategy_id}/start`
- `POST /api/strategies/{strategy_id}/stop`
- `POST /api/strategies/{strategy_id}/run-once`
- `GET /api/market/snapshot`
- `POST /api/market/refresh-real`
- `GET /api/market/klines?symbol=AAPL&interval=1m`
- `POST /api/order`
- `GET /api/order/{order_id}`
- `GET /api/orderbook/{symbol}`
- `WS /ws/market`

`/api/order` remains as the legacy in-memory demo endpoint. New authenticated product flow should use `/api/orders`.

## Tests
```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Roadmap
- Add frontend login flow and token-aware API client.
- Expand frontend pages for orders, trades, holdings, and account cashflows.
- Add K-line chart rendering and richer strategy performance metrics.
- Broadcast persisted orderbook and trade events through WebSocket.
- Add PostgreSQL profile for production-style deployment.
