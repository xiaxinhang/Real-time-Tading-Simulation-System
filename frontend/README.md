# Trading Simulation Dashboard

Vue 3 dashboard for the real-time trading simulation backend.

## Stack
- Vue 3
- Vite
- Native WebSocket client
- Decoupled HTTP API layer

## Local Development

```powershell
cd frontend
npm install
npm run dev
```

Open:
`http://127.0.0.1:5173`

Backend defaults:
- HTTP API: `http://127.0.0.1:8000`
- WebSocket: `ws://127.0.0.1:8000/ws/market`

Override with a local `.env` file:

```env
VITE_API_BASE=http://127.0.0.1:8000
VITE_WS_BASE=ws://127.0.0.1:8000
```

## Dashboard Modules
- Live market tape from WebSocket snapshots
- Market/limit order ticket
- Price-time priority order book panel
- Trade event stream from WebSocket `trade_events`
- Portfolio and analytics console
