import { reactive, readonly } from "vue";
import { tradingApi } from "../api/tradingApi";

const state = reactive({
  userId: "u001",
  selectedSymbol: "AAPL",
  portfolio: null,
  userAnalysis: null,
  marketAnalysis: null,
  orderBook: null,
  latestOrder: null,
  health: null,
  systemStatus: null,
  loading: false,
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

export function useTradingStore() {
  async function refreshHealth() {
    const [health, systemStatus] = await Promise.all([tradingApi.health(), tradingApi.systemStatus()]);
    state.health = health;
    state.systemStatus = systemStatus;
  }

  async function refreshPortfolio() {
    state.portfolio = await tradingApi.portfolio(state.userId);
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
    await Promise.allSettled([refreshPortfolio(), refreshOrderBook(), refreshUserAnalysis()]);
    return response;
  }

  function setUserId(userId) {
    state.userId = userId;
  }

  function setSelectedSymbol(symbol) {
    state.selectedSymbol = symbol.toUpperCase();
  }

  return {
    state: readonly(state),
    refreshHealth: () => run(refreshHealth),
    refreshPortfolio: () => run(refreshPortfolio),
    refreshUserAnalysis: () => run(refreshUserAnalysis),
    refreshMarketAnalysis: () => run(refreshMarketAnalysis),
    refreshOrderBook: () => run(refreshOrderBook),
    placeOrder,
    setUserId,
    setSelectedSymbol,
  };
}
