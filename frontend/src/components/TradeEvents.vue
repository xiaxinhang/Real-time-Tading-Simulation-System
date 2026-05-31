<script setup>
import { formatMoney, formatNumber, formatTime } from "../utils";

const props = defineProps({ events: { type: Array, default: () => [] }, latestOrder: Object });

function filledQty(order) {
  return order?.filled_quantity ?? order?.fill_qty ?? 0;
}

function orderNotional(order) {
  if (order?.notional !== undefined) return order.notional;
  return Number(order?.avg_fill_price || 0) * Number(order?.filled_quantity || 0);
}
</script>

<template>
  <section class="panel event-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">事件驱动</p>
        <h2>交易事件</h2>
      </div>
      <span class="subtle">保留 {{ props.events.length }} 条</span>
    </div>

    <div v-if="latestOrder" class="latest-order">
      <span>{{ latestOrder.symbol }} {{ latestOrder.side }}</span>
      <strong>{{ latestOrder.status }}</strong>
      <span>已成交 {{ formatNumber(filledQty(latestOrder)) }}</span>
      <span>{{ formatMoney(orderNotional(latestOrder)) }}</span>
    </div>

    <div class="event-list">
      <article v-for="event in props.events" :key="event.event_id" class="event-item">
        <div>
          <strong>{{ event.event_type }}</strong>
          <p>{{ event.symbol }} {{ event.side }} {{ formatNumber(event.quantity) }} @ {{ formatMoney(event.price) }}</p>
        </div>
        <time>{{ formatTime(event.ts) }}</time>
      </article>
      <div v-if="!props.events.length" class="empty">连接 WebSocket 后提交订单，即可看到撮合事件。</div>
    </div>
  </section>
</template>
