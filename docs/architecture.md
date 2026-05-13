# System Architecture

## Components
- FastAPI app: HTTP API + WebSocket endpoint
- MarketService: real-time market tick generator (5 symbols)
- Domain layer: exchange primitives isolated from HTTP and storage concerns
- MatchingEngine: symbol-scoped price-time priority matching
- OrderBook: in-memory bid/ask levels for resting limit orders
- Redis cache: latest symbol snapshot and user trade history
- TradeService: application orchestration, risk checks, account state, persistence, event broadcast
- AnalysisService: market metrics and user PnL metrics

## Data Flow
1. `MarketService` updates prices every tick.
2. Tick snapshots are cached into Redis (`market:latest:*`).
3. Snapshot is broadcast to all `/ws/market` clients.
4. `POST /api/order` validates account risk in `TradeService`.
5. The order is submitted to `MatchingEngine`.
6. Marketable orders match against the contra side of the `OrderBook`.
7. Unfilled limit quantity rests on the book with price-time priority.
8. Order responses, fills, and trade events are stored in Redis/in-memory indexes.
9. Trade events are broadcast through WebSocket as `trade_events` messages.
10. Analysis APIs aggregate market and user stats.

## Redis Keys (v1)
- `market:latest:{symbol}`: latest tick per symbol (JSON)
- `market:latest:all`: full snapshot payload (JSON)
- `trade:orders:{user_id}`: order history list
- `trade:fills:{user_id}`: fills history list
- `trade:events:{symbol}`: trade/order event history list

## Reliability Notes
- Redis temporary failures do not crash the service.
- WebSocket dead connections are cleaned automatically.
- Current version is demo-first and keeps account state in memory.
- Current risk checks do not reserve buying power for open orders yet; production evolution should add reservation/hold accounting.
