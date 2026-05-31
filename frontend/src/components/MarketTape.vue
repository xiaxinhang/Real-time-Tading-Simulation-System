<script setup>
import { computed } from "vue";
import { formatMoney, formatNumber, formatTime } from "../utils";

const props = defineProps({
  ticks: { type: Array, default: () => [] },
  selectedSymbol: String,
  refreshingMarket: Boolean,
  marketStatus: Object,
});
const emit = defineEmits(["select-symbol", "refresh-real"]);

const sortedTicks = computed(() => [...props.ticks].sort((a, b) => a.symbol.localeCompare(b.symbol)));

const lastPullLabel = computed(() => {
  const ts = props.marketStatus?.last_successful_pull_ts;
  return ts ? formatTime(ts) : "暂无";
});

const sourceLabel = computed(() => {
  const source = props.marketStatus?.market_data_source || "unknown";
  if (source === "real_yahoo") return "Yahoo";
  if (source === "real_stooq") return "Stooq";
  if (source === "fallback_cache") return "缓存";
  if (source === "unavailable") return "不可用";
  return "等待";
});
</script>

<template>
  <section class="panel market-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">实时 WebSocket</p>
        <h2>市场行情</h2>
      </div>
      <div class="row">
        <span class="subtle market-meta">{{ sortedTicks.length }} 个股票代码</span>
        <span class="subtle market-meta">来源：{{ sourceLabel }}</span>
        <span class="subtle market-meta">上次成功：{{ lastPullLabel }}</span>
        <button class="refresh-real-btn" :disabled="refreshingMarket" @click="emit('refresh-real')">
          {{ refreshingMarket ? "拉取中..." : "重新拉取真实数据" }}
        </button>
      </div>
    </div>

    <div class="table-shell">
      <table>
        <thead>
          <tr><th>股票代码</th><th>价格</th><th>涨跌</th><th>成交量</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="tick in sortedTicks"
            :key="tick.symbol"
            :class="{ selected: tick.symbol === selectedSymbol }"
            @click="emit('select-symbol', tick.symbol)"
          >
            <td><strong>{{ tick.symbol }}</strong></td>
            <td>{{ formatMoney(tick.price) }}</td>
            <td :class="Number(tick.change) >= 0 ? 'positive' : 'negative'">
              {{ (Number(tick.change) * 100).toFixed(3) }}%
            </td>
            <td>{{ formatNumber(tick.volume) }}</td>
            <td>{{ formatTime(tick.ts) }}</td>
          </tr>
          <tr v-if="!sortedTicks.length"><td colspan="5" class="empty">等待行情推送...</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
