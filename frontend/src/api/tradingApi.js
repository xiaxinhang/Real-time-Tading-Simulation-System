import { config } from "../config";

const TOKEN_KEY = "trading_sim_token";

function getToken() {
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(token) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${config.apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || `Request failed with status ${response.status}`;
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join("; ") : message);
  }
  return payload;
}

export const tradingApi = {
  getToken,
  setToken,
  health: () => request("/health"),
  systemStatus: () => request("/system/status"),
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/api/auth/me"),
  account: () => request("/api/account"),
  positions: () => request("/api/positions"),
  cashflows: () => request("/api/cashflows"),
  orders: () => request("/api/orders"),
  trades: () => request("/api/trades"),
  strategies: () => request("/api/strategies"),
  createStrategy: (payload) => request("/api/strategies", { method: "POST", body: JSON.stringify(payload) }),
  startStrategy: (strategyId) => request(`/api/strategies/${encodeURIComponent(strategyId)}/start`, { method: "POST" }),
  stopStrategy: (strategyId) => request(`/api/strategies/${encodeURIComponent(strategyId)}/stop`, { method: "POST" }),
  runStrategyOnce: (strategyId) => request(`/api/strategies/${encodeURIComponent(strategyId)}/run-once`, { method: "POST" }),
  placeOrder: (payload) => request("/api/orders", { method: "POST", body: JSON.stringify(payload) }),
  cancelOrder: (orderId) => request(`/api/orders/${encodeURIComponent(orderId)}`, { method: "DELETE" }),
  marketSnapshot: () => request("/api/market/snapshot"),
  refreshRealMarket: () => request("/api/market/refresh-real", { method: "POST" }),
  orderBook: (symbol, depth = 10) => request(`/api/orderbook/${encodeURIComponent(symbol)}?depth=${depth}`),
  legacyPortfolio: (userId) => request(`/api/user/${encodeURIComponent(userId)}/portfolio`),
  userAnalysis: (userId) => request(`/api/user/${encodeURIComponent(userId)}/analysis`),
  marketAnalysis: () => request("/api/market/analysis"),
};
