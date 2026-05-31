<script setup>
import { computed, reactive } from "vue";
import { formatMoney, formatNumber } from "../utils";

const props = defineProps({ strategies: { type: Array, default: () => [] }, loading: Boolean, authenticated: Boolean });
const emit = defineEmits(["create", "start", "stop", "run-once"]);

const form = reactive({
  name: "AAPL 均线策略",
  strategy_type: "moving_average_cross",
  symbol: "AAPL",
  quantity: 1,
  short_window: 3,
  long_window: 5,
  grid_pct: 0.01,
});

const strategyLabel = computed(() => form.strategy_type === "moving_average_cross" ? "均线交叉" : "网格交易");

function submit() {
  const params = { quantity: Number(form.quantity) };
  if (form.strategy_type === "moving_average_cross") {
    params.short_window = Number(form.short_window);
    params.long_window = Number(form.long_window);
  } else {
    params.grid_pct = Number(form.grid_pct);
  }
  emit("create", {
    name: form.name.trim() || `${form.symbol.toUpperCase()} ${strategyLabel.value}`,
    strategy_type: form.strategy_type,
    symbol: form.symbol.trim().toUpperCase(),
    params,
  });
}
</script>

<template>
  <div class="strategy-layout">
    <form class="strategy-form" @submit.prevent="submit">
      <label>策略名称<input v-model="form.name" required maxlength="128" /></label>
      <label>策略类型
        <select v-model="form.strategy_type">
          <option value="moving_average_cross">均线交叉</option>
          <option value="grid">网格交易</option>
        </select>
      </label>
      <label>股票代码<input v-model="form.symbol" required maxlength="16" /></label>
      <label>下单数量<input v-model.number="form.quantity" type="number" min="1" required /></label>
      <template v-if="form.strategy_type === 'moving_average_cross'">
        <label>短均线窗口<input v-model.number="form.short_window" type="number" min="1" required /></label>
        <label>长均线窗口<input v-model.number="form.long_window" type="number" min="2" required /></label>
      </template>
      <template v-else>
        <label>网格间距<input v-model.number="form.grid_pct" type="number" min="0.001" step="0.001" required /></label>
      </template>
      <button class="primary-action" :disabled="loading || !authenticated">
        {{ authenticated ? "创建策略" : "请先登录" }}
      </button>
    </form>

    <div class="table-shell compact">
      <table>
        <thead><tr><th>名称</th><th>类型</th><th>股票代码</th><th>状态</th><th>交易次数</th><th>收益</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="strategy in strategies" :key="strategy.id">
            <td><strong>{{ strategy.name }}</strong></td>
            <td>{{ strategy.strategy_type === "moving_average_cross" ? "均线交叉" : "网格交易" }}</td>
            <td>{{ strategy.symbol }}</td>
            <td>{{ strategy.status === "running" ? "运行中" : "已停止" }}</td>
            <td>{{ formatNumber(strategy.trade_count) }}</td>
            <td>{{ formatMoney(strategy.realized_pnl) }}</td>
            <td class="action-cell">
              <button v-if="strategy.status !== 'running'" class="small-action" @click="emit('start', strategy.id)">启动</button>
              <button v-else class="small-action" @click="emit('stop', strategy.id)">停止</button>
              <button class="small-action ghost-action" @click="emit('run-once', strategy.id)">试跑一次</button>
            </td>
          </tr>
          <tr v-if="!strategies.length"><td colspan="7" class="empty">暂无策略。可以先创建一个均线交叉策略试跑。</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
