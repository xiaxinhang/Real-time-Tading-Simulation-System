import { config } from "../config";

async function request(path, options = {}) {
  const response = await fetch(`${config.apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
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
  health: () => request("/health"),
  systemStatus: () => request("/system/status"),
  marketSnapshot: () => request("/api/market/snapshot"),
  placeOrder: (payload) => request("/api/order", { method: "POST", body: JSON.stringify(payload) }),
  orderBook: (symbol, depth = 10) => request(`/api/orderbook/${encodeURIComponent(symbol)}?depth=${depth}`),
  portfolio: (userId) => request(`/api/user/${encodeURIComponent(userId)}/portfolio`),
  userAnalysis: (userId) => request(`/api/user/${encodeURIComponent(userId)}/analysis`),
  marketAnalysis: () => request("/api/market/analysis"),
};
