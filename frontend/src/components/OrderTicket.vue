<script setup>
import { reactive, watch } from "vue";

const props = defineProps({ selectedSymbol: String, loading: Boolean, authenticated: Boolean });
const emit = defineEmits(["submit", "update:symbol"]);

const form = reactive({
  symbol: props.selectedSymbol || "AAPL",
  side: "buy",
  quantity: 10,
  order_type: "market",
  limit_price: null,
});

watch(() => props.selectedSymbol, (symbol) => {
  if (symbol) form.symbol = symbol;
});

function submit() {
  const payload = {
    symbol: form.symbol.trim().toUpperCase(),
    side: form.side,
    quantity: Number(form.quantity),
    order_type: form.order_type,
  };
  if (payload.order_type === "limit") payload.limit_price = Number(form.limit_price);
  emit("update:symbol", payload.symbol);
  emit("submit", payload);
}
</script>

<template>
  <section class="panel ticket-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">交易执行</p>
        <h2>下单面板</h2>
      </div>
    </div>

    <form class="ticket-form" @submit.prevent="submit">
      <label>股票代码<input v-model="form.symbol" required maxlength="16" @change="emit('update:symbol', form.symbol.toUpperCase())" /></label>
      <label>方向
        <select v-model="form.side">
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </label>
      <label>订单类型
        <select v-model="form.order_type">
          <option value="market">市价单</option>
          <option value="limit">限价单</option>
        </select>
      </label>
      <label>数量<input v-model.number="form.quantity" type="number" min="1" required /></label>
      <label :class="{ disabled: form.order_type === 'market' }">
        限价
        <input v-model.number="form.limit_price" type="number" min="0.01" step="0.01" :disabled="form.order_type === 'market'" />
      </label>
      <button class="primary-action" :disabled="loading || !authenticated">
        {{ !authenticated ? "请先登录" : loading ? "提交中..." : "提交订单" }}
      </button>
    </form>
  </section>
</template>
