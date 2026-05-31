import { reactive, readonly } from "vue";
import { tradingApi } from "../api/tradingApi";

const state = reactive({
  userId: "u001",
  selectedSymbol: "AAPL",
  currentUser: null,
  authenticated: false,
  account: null,
  positions: [],
  cashflows: [],
  orders: [],
  trades: [],
  strategies: [],
  portfolio: null,
  userAnalysis: null,
  marketAnalysis: null,
  orderBook: null,
  latestOrder: null,
  health: null,
  systemStatus: null,
  loading: false,
  authLoading: false,
  refreshingMarket: false,
  error: "",
});

async function run(task) {
  state.loading = true;
  state.error = "";
  try {
    return await task();
  } catch (error) {
    state.error = error instanceof Error ? error.message : String(error);
    throw error;
  } finally {
    state.loading = false;
  }
}

function applyAuth(payload) {
  tradingApi.setToken(payload.access_token);
  state.currentUser = payload.user;
  state.authenticated = true;
  state.userId = String(payload.user.id);
}

export function useTradingStore() {
  async function bootstrapAuth() {
    if (!tradingApi.getToken()) return null;
    try {
      const user = await tradingApi.me();
      state.currentUser = user;
      state.authenticated = true;
      state.userId = String(user.id);
      await refreshPrivateData();
      return user;
    } catch {
      logout();
      return null;
    }
  }

  async function login(payload) {
    state.authLoading = true;
    state.error = "";
    try {
      const response = await tradingApi.login(payload);
      applyAuth(response);
      await refreshPrivateData();
      return response;
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error);
      throw error;
    } finally {
      state.authLoading = false;
    }
  }

  async function register(payload) {
    state.authLoading = true;
    state.error = "";
    try {
      const response = await tradingApi.register(payload);
      applyAuth(response);
      await refreshPrivateData();
      return response;
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error);
      throw error;
    } finally {
      state.authLoading = false;
    }
  }

  function logout() {
    tradingApi.setToken("");
    state.currentUser = null;
    state.authenticated = false;
    state.account = null;
    state.positions = [];
    state.cashflows = [];
    state.orders = [];
    state.trades = [];
    state.strategies = [];
  }

  async function refreshHealth() {
    const [health, systemStatus] = await Promise.all([tradingApi.health(), tradingApi.systemStatus()]);
    state.health = health;
    state.systemStatus = systemStatus;
  }

  async function refreshPrivateData() {
    if (!state.authenticated) return;
    const [account, positions, cashflows, orders, trades, strategies] = await Promise.all([
      tradingApi.account(),
      tradingApi.positions(),
      tradingApi.cashflows(),
      tradingApi.orders(),
      tradingApi.trades(),
      tradingApi.strategies(),
    ]);
    state.account = account;
    state.positions = positions;
    state.cashflows = cashflows;
    state.orders = orders;
    state.trades = trades;
    state.strategies = strategies;
  }

  async function refreshPortfolio() {
    if (state.authenticated) {
      await refreshPrivateData();
      return;
    }
    state.portfolio = await tradingApi.legacyPortfolio(state.userId);
  }

  async function refreshUserAnalysis() {
    state.userAnalysis = await tradingApi.userAnalysis(state.userId);
  }

  async function refreshMarketAnalysis() {
    state.marketAnalysis = await tradingApi.marketAnalysis();
  }

  async function refreshOrderBook() {
    state.orderBook = await tradingApi.orderBook(state.selectedSymbol);
  }

  async function placeOrder(order) {
    const response = await run(() => tradingApi.placeOrder(order));
    state.latestOrder = response;
    await Promise.allSettled([refreshPrivateData(), refreshOrderBook(), refreshUserAnalysis()]);
    return response;
  }

  async function cancelOrder(orderId) {
    const response = await run(() => tradingApi.cancelOrder(orderId));
    state.latestOrder = response;
    await Promise.allSettled([refreshPrivateData(), refreshOrderBook()]);
    return response;
  }

  async function createStrategy(payload) {
    const response = await run(() => tradingApi.createStrategy(payload));
    await refreshPrivateData();
    return response;
  }

  async function startStrategy(strategyId) {
    const response = await run(() => tradingApi.startStrategy(strategyId));
    await refreshPrivateData();
    return response;
  }

  async function stopStrategy(strategyId) {
    const response = await run(() => tradingApi.stopStrategy(strategyId));
    await refreshPrivateData();
    return response;
  }

  async function runStrategyOnce(strategyId) {
    const response = await run(() => tradingApi.runStrategyOnce(strategyId));
    await Promise.allSettled([refreshPrivateData(), refreshOrderBook()]);
    return response;
  }

  async function refreshRealMarketNow() {
    state.refreshingMarket = true;
    state.error = "";
    try {
      const payload = await tradingApi.refreshRealMarket();
      await refreshHealth();
      return payload;
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error);
      throw error;
    } finally {
      state.refreshingMarket = false;
    }
  }

  function setUserId(userId) {
    state.userId = userId;
  }

  function setSelectedSymbol(symbol) {
    state.selectedSymbol = symbol.toUpperCase();
  }

  return {
    state: readonly(state),
    bootstrapAuth: () => run(bootstrapAuth),
    login,
    register,
    logout,
    refreshHealth: () => run(refreshHealth),
    refreshPortfolio: () => run(refreshPortfolio),
    refreshPrivateData: () => run(refreshPrivateData),
    refreshUserAnalysis: () => run(refreshUserAnalysis),
    refreshMarketAnalysis: () => run(refreshMarketAnalysis),
    refreshOrderBook: () => run(refreshOrderBook),
    refreshRealMarketNow,
    placeOrder,
    cancelOrder,
    createStrategy,
    startStrategy,
    stopStrategy,
    runStrategyOnce,
    setUserId,
    setSelectedSymbol,
  };
}
