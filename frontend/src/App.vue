<script setup>
import { computed, onMounted, watch } from "vue";
import AccountConsole from "./components/AccountConsole.vue";
import HeroStatus from "./components/HeroStatus.vue";
import MarketTape from "./components/MarketTape.vue";
import OrderBook from "./components/OrderBook.vue";
import OrderTicket from "./components/OrderTicket.vue";
import TradeEvents from "./components/TradeEvents.vue";
import { useTradingStore } from "./stores/tradingStore";
import { useMarketSocket } from "./ws/marketSocket";

const trading = useTradingStore();
const socket = useMarketSocket();

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

watch(() => socket.state.latestOrder, async (order) => {
  if (!order) return;
  if (order.user_id === trading.state.userId) {
    await Promise.allSettled([trading.refreshPortfolio(), trading.refreshUserAnalysis()]);
  }
  if (order.symbol === trading.state.selectedSymbol) {
    await trading.refreshOrderBook();
  }
});

onMounted(async () => {
  socket.connect();
  await Promise.allSettled([
    trading.refreshHealth(),
    trading.refreshPortfolio(),
    trading.refreshMarketAnalysis(),
  ]);
});
</script>

<template>
  <main class="dashboard-shell">
    <HeroStatus :health="trading.state.health" :status="trading.state.systemStatus" />

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
        @select-symbol="selectSymbol"
      />
      <OrderTicket
        :selected-symbol="trading.state.selectedSymbol"
        :user-id="trading.state.userId"
        :loading="trading.state.loading"
        @update:user-id="trading.setUserId"
        @update:symbol="selectSymbol"
        @submit="submitOrder"
      />
      <OrderBook :book="trading.state.orderBook" :symbol="trading.state.selectedSymbol" />
      <TradeEvents :events="socket.state.tradeEvents" :latest-order="socket.state.latestOrder || trading.state.latestOrder" />
      <AccountConsole
        :portfolio="trading.state.portfolio"
        :user-analysis="trading.state.userAnalysis"
        :market-analysis="trading.state.marketAnalysis"
        @refresh-portfolio="trading.refreshPortfolio"
        @refresh-user="trading.refreshUserAnalysis"
        @refresh-market="trading.refreshMarketAnalysis"
      />
    </section>
  </main>
</template>
