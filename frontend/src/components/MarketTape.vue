<script setup>
import { computed } from "vue";
import { formatMoney, formatNumber, formatTime } from "../utils";

const props = defineProps({ ticks: { type: Array, default: () => [] }, selectedSymbol: String });
const emit = defineEmits(["select-symbol"]);

const sortedTicks = computed(() => [...props.ticks].sort((a, b) => a.symbol.localeCompare(b.symbol)));
</script>

<template>
  <section class="panel market-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">实时 WebSocket</p>
        <h2>市场行情</h2>
      </div>
      <span class="subtle">{{ sortedTicks.length }} 个股票代码</span>
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
