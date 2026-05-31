<script setup>
import { computed, onMounted, onUnmounted, watch } from "vue";
import AccountConsole from "./components/AccountConsole.vue";
import AuthPanel from "./components/AuthPanel.vue";
import HeroStatus from "./components/HeroStatus.vue";
import MarketTape from "./components/MarketTape.vue";
import OrderBook from "./components/OrderBook.vue";
import OrderTicket from "./components/OrderTicket.vue";
import TradeEvents from "./components/TradeEvents.vue";
import { useTradingStore } from "./stores/tradingStore";
import { useMarketSocket } from "./ws/marketSocket";

const trading = useTradingStore();
const socket = useMarketSocket();
let healthTimer = null;

const connectionLabel = computed(() => {
  if (socket.state.connected) return "已连接";
  if (socket.state.connecting) return "连接中";
  return "未连接";
});

async function selectSymbol(symbol) {
  trading.setSelectedSymbol(symbol);
  await trading.refreshOrderBook();
}

async function submitOrder(payload) {
  await trading.placeOrder(payload);
}

async function cancelOrder(orderId) {
  await trading.cancelOrder(orderId);
}

async function createStrategy(payload) {
  await trading.createStrategy(payload);
}

async function startStrategy(strategyId) {
  await trading.startStrategy(strategyId);
}

async function stopStrategy(strategyId) {
  await trading.stopStrategy(strategyId);
}

async function runStrategyOnce(strategyId) {
  await trading.runStrategyOnce(strategyId);
}

async function refreshRealMarket() {
  await trading.refreshRealMarketNow();
}

async function loadDashboard() {
  socket.connect();
  await Promise.allSettled([
    trading.refreshPortfolio(),
    trading.refreshMarketAnalysis(),
    trading.refreshOrderBook(),
  ]);
}

watch(() => socket.state.latestOrder, async (order) => {
  if (!order) return;
  if (order.user_id === trading.state.userId) {
    await Promise.allSettled([trading.refreshPortfolio(), trading.refreshUserAnalysis()]);
  }
  if (order.symbol === trading.state.selectedSymbol) {
    await trading.refreshOrderBook();
  }
});

watch(() => trading.state.authenticated, async (authenticated) => {
  if (authenticated) {
    await loadDashboard();
  } else {
    socket.disconnect();
  }
});

onMounted(async () => {
  await Promise.allSettled([
    trading.bootstrapAuth(),
    trading.refreshHealth(),
  ]);
  healthTimer = window.setInterval(() => {
    trading.refreshHealth().catch(() => {});
  }, 10000);
});

onUnmounted(() => {
  if (healthTimer) {
    window.clearInterval(healthTimer);
    healthTimer = null;
  }
});
</script>

<template>
  <main v-if="!trading.state.authenticated" class="auth-shell">
    <p v-if="trading.state.error || socket.state.error" class="error-banner">
      {{ trading.state.error || socket.state.error }}
    </p>

    <AuthPanel
      :loading="trading.state.authLoading"
      @login="trading.login"
      @register="trading.register"
    />
  </main>

  <main v-else class="dashboard-shell">
    <HeroStatus
      :health="trading.state.health"
      :status="trading.state.systemStatus"
      :current-user="trading.state.currentUser"
      :authenticated="trading.state.authenticated"
      @logout="trading.logout"
    />

    <section class="connection-bar">
      <div>
        <span class="pulse" :class="{ online: socket.state.connected }"></span>
        WebSocket {{ connectionLabel }}
      </div>
      <div class="connection-actions">
        <button @click="socket.connect">连接</button>
        <button class="ghost" @click="socket.disconnect">断开</button>
      </div>
    </section>

    <p v-if="trading.state.error || socket.state.error" class="error-banner">
      {{ trading.state.error || socket.state.error }}
    </p>

    <section class="dashboard-grid">
      <MarketTape
        :ticks="socket.state.ticks"
        :selected-symbol="trading.state.selectedSymbol"
        :refreshing-market="trading.state.refreshingMarket"
        :market-status="socket.state.marketStatus || trading.state.systemStatus"
        @select-symbol="selectSymbol"
        @refresh-real="refreshRealMarket"
      />
      <OrderTicket
        :selected-symbol="trading.state.selectedSymbol"
        :loading="trading.state.loading"
        :authenticated="trading.state.authenticated"
        @update:symbol="selectSymbol"
        @submit="submitOrder"
      />
      <OrderBook :book="trading.state.orderBook" :symbol="trading.state.selectedSymbol" />
      <TradeEvents :events="socket.state.tradeEvents" :latest-order="socket.state.latestOrder || trading.state.latestOrder" />
      <AccountConsole
        :authenticated="trading.state.authenticated"
        :account="trading.state.account"
        :positions="trading.state.positions"
        :orders="trading.state.orders"
        :trades="trading.state.trades"
        :cashflows="trading.state.cashflows"
        :strategies="trading.state.strategies"
        :portfolio="trading.state.portfolio"
        :user-analysis="trading.state.userAnalysis"
        :market-analysis="trading.state.marketAnalysis"
        @refresh-portfolio="trading.refreshPortfolio"
        @refresh-user="trading.refreshUserAnalysis"
        @refresh-market="trading.refreshMarketAnalysis"
        @cancel-order="cancelOrder"
        @create-strategy="createStrategy"
        @start-strategy="startStrategy"
        @stop-strategy="stopStrategy"
        @run-strategy-once="runStrategyOnce"
      />
    </section>
  </main>
</template>
