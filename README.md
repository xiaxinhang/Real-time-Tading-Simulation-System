# Real-time Trading Simulation Backend System

A demo-first financial backend built with FastAPI + WebSocket + Redis.

## Features
- Real-time market simulation for 5 symbols
- WebSocket market snapshot push (`/ws/market`)
- Redis high-concurrency cache for market and trade data
- Market and limit order trading API
- Domain-level order book, matching engine, and trade event stream
- User and market analytics API

## Project Structure
- `app/main.py`: FastAPI entry and lifecycle
- `app/domain/`: exchange domain primitives (`Order`, `OrderBook`, `MatchingEngine`, `TradeEvent`)
- `app/service/market.py`: market tick generator
- `app/service/trade.py`: trading application service, risk checks, account state, event persistence
- `app/service/analysis.py`: analytics metrics
- `app/websocket/market_ws.py`: WS manager and endpoint
- `app/core/redis_client.py`: async Redis client

## Quick Start
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Start Redis (`localhost:6379`).
3. Run service:
```bash
uvicorn app.main:app --reload
```

## APIs
- `GET /health`
- `GET /system/status`
- `GET /api/market/snapshot`
- `POST /api/order`
- `GET /api/order/{order_id}`
- `GET /api/orderbook/{symbol}`
- `GET /api/user/{user_id}/portfolio`
- `GET /api/user/{user_id}/analysis`
- `GET /api/market/analysis`
- `WS /ws/market`

## Order Example
Market order:
```bash
curl -X POST http://127.0.0.1:8000/api/order \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","symbol":"AAPL","side":"buy","quantity":10,"order_type":"market"}'
```

Limit order:
```bash
curl -X POST http://127.0.0.1:8000/api/order \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","symbol":"AAPL","side":"buy","quantity":10,"order_type":"limit","limit_price":180.50}'
```

## Notes
- This version keeps user account state in memory and uses Redis for cache/history.
- If Redis is unavailable, core service still runs with degraded cache persistence.
- Simulated market-maker liquidity is seeded per symbol so learning/demo market orders can execute while still passing through the matching engine.
