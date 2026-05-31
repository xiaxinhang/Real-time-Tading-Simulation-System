import { reactive, readonly } from "vue";
import { config } from "../config";

const state = reactive({
  connected: false,
  connecting: false,
  lastMessageAt: null,
  reconnectAttempts: 0,
  ticks: [],
  marketStatus: null,
  tradeEvents: [],
  latestOrder: null,
  error: "",
});

let socket = null;
let reconnectTimer = null;
let shouldReconnect = true;

function scheduleReconnect() {
  if (!shouldReconnect || reconnectTimer) return;
  const delay = Math.min(1000 * 2 ** state.reconnectAttempts, 10000);
  state.reconnectAttempts += 1;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

function handleMessage(event) {
  state.lastMessageAt = Date.now();
  const message = JSON.parse(event.data);

  if (message.type === "snapshot" && Array.isArray(message.data)) {
    state.ticks = message.data;
    state.marketStatus = {
      market_data_source: message.market_data_source,
      market_data_error: message.market_data_error,
      last_successful_pull_ts: message.last_successful_pull_ts,
      market_data_stale: message.market_data_stale,
      max_data_age_ms: message.max_data_age_ms,
      refresh_interval: message.refresh_interval,
    };
    return;
  }

  if (message.type === "trade_events" && Array.isArray(message.events)) {
    state.latestOrder = message.order || null;
    state.tradeEvents = [...message.events, ...state.tradeEvents].slice(0, 80);
  }
}

function connect() {
  if (socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)) return;
  shouldReconnect = true;
  state.connecting = true;
  state.error = "";

  socket = new WebSocket(`${config.wsBase}/ws/market`);
  socket.onopen = () => {
    state.connected = true;
    state.connecting = false;
    state.reconnectAttempts = 0;
  };
  socket.onmessage = (event) => {
    try {
      handleMessage(event);
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error);
    }
  };
  socket.onerror = () => {
    state.error = "WebSocket connection error";
  };
  socket.onclose = () => {
    state.connected = false;
    state.connecting = false;
    scheduleReconnect();
  };
}

function disconnect() {
  shouldReconnect = false;
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) socket.close();
}

export function useMarketSocket() {
  return {
    state: readonly(state),
    connect,
    disconnect,
  };
}
