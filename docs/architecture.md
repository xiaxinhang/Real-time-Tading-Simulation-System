# System Architecture

## Components
- FastAPI app: HTTP API + WebSocket endpoint
- MarketService: real-time market tick generator (5 symbols)
- Redis cache: latest symbol snapshot and user trade history
- TradeService: market-order execution and in-memory account state
- AnalysisService: market metrics and user PnL metrics

## Data Flow
1. `MarketService` updates prices every tick.
2. Tick snapshots are cached into Redis (`market:latest:*`).
3. Snapshot is broadcast to all `/ws/market` clients.
4. `POST /api/order` reads latest price and executes immediately.
5. Orders/fills are stored to Redis lists and in-memory index.
6. Analysis APIs aggregate market and user stats.

## Redis Keys (v1)
- `market:latest:{symbol}`: latest tick per symbol (JSON)
- `market:latest:all`: full snapshot payload (JSON)
- `trade:orders:{user_id}`: order history list
- `trade:fills:{user_id}`: fills history list

## Reliability Notes
- Redis temporary failures do not crash the service.
- WebSocket dead connections are cleaned automatically.
- Current version is demo-first and keeps account state in memory.
