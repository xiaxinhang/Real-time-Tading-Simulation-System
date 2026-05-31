<script setup>
import { computed } from "vue";
import { formatMoney, formatNumber } from "../utils";

const props = defineProps({ book: Object, symbol: String });

const rows = computed(() => {
  const bids = props.book?.bids || [];
  const asks = props.book?.asks || [];
  const max = Math.max(bids.length, asks.length);
  return Array.from({ length: max }, (_, index) => ({ bid: bids[index], ask: asks[index] }));
});
</script>

<template>
  <section class="panel book-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">价格时间优先</p>
        <h2>{{ symbol }} 订单簿</h2>
      </div>
    </div>

    <div class="book-grid book-head">
      <span>买价</span><span>买量</span><span>卖价</span><span>卖量</span>
    </div>
    <div v-if="rows.length" class="book-levels">
      <div v-for="(row, index) in rows" :key="index" class="book-grid book-row">
        <strong class="positive">{{ row.bid ? formatMoney(row.bid.price) : '-' }}</strong>
        <span>{{ row.bid ? formatNumber(row.bid.quantity) : '-' }}</span>
        <strong class="negative">{{ row.ask ? formatMoney(row.ask.price) : '-' }}</strong>
        <span>{{ row.ask ? formatNumber(row.ask.quantity) : '-' }}</span>
      </div>
    </div>
    <div v-else class="empty">暂无挂单流动性。等待行情到达后提交限价单或刷新。</div>
  </section>
</template>
