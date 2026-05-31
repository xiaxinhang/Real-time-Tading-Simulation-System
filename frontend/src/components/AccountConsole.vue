<script setup>
import { ref } from "vue";
import { formatMoney, formatNumber, formatPercent } from "../utils";
import StrategyPanel from "./StrategyPanel.vue";

const props = defineProps({
  authenticated: Boolean,
  account: Object,
  positions: { type: Array, default: () => [] },
  orders: { type: Array, default: () => [] },
  trades: { type: Array, default: () => [] },
  cashflows: { type: Array, default: () => [] },
  strategies: { type: Array, default: () => [] },
  portfolio: Object,
  userAnalysis: Object,
  marketAnalysis: Object,
});
const emit = defineEmits([
  "refresh-portfolio",
  "refresh-user",
  "refresh-market",
  "cancel-order",
  "create-strategy",
  "start-strategy",
  "stop-strategy",
  "run-strategy-once",
]);
const active = ref("account");

function switchTab(tab) {
  active.value = tab;
  if (tab === "analysis") emit("refresh-user");
  if (tab === "market") emit("refresh-market");
  if (["account", "positions", "orders", "trades", "cashflows", "strategies"].includes(tab)) emit("refresh-portfolio");
}

function canCancel(order) {
  return ["accepted", "open", "partially_filled"].includes(order.status);
}
</script>

<template>
  <section class="panel account-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">风控与分析</p>
        <h2>交易工作台</h2>
      </div>
    </div>

    <div class="tab-strip">
      <button :class="{ active: active === 'account' }" @click="switchTab('account')">资金</button>
      <button :class="{ active: active === 'positions' }" @click="switchTab('positions')">持仓</button>
      <button :class="{ active: active === 'orders' }" @click="switchTab('orders')">订单</button>
      <button :class="{ active: active === 'trades' }" @click="switchTab('trades')">成交</button>
      <button :class="{ active: active === 'cashflows' }" @click="switchTab('cashflows')">流水</button>
      <button :class="{ active: active === 'strategies' }" @click="switchTab('strategies')">策略</button>
      <button :class="{ active: active === 'analysis' }" @click="switchTab('analysis')">用户分析</button>
      <button :class="{ active: active === 'market' }" @click="switchTab('market')">市场分析</button>
    </div>

    <div v-if="active === 'account'" class="account-body">
      <div v-if="authenticated && account" class="metric-grid">
        <div class="metric"><span>现金</span><strong>{{ formatMoney(account.cash) }}</strong></div>
        <div class="metric"><span>可用资金</span><strong>{{ formatMoney(account.available_cash) }}</strong></div>
        <div class="metric"><span>冻结资金</span><strong>{{ formatMoney(account.frozen_cash) }}</strong></div>
        <div class="metric"><span>总权益</span><strong>{{ formatMoney(account.total_equity) }}</strong></div>
      </div>
      <div v-else class="empty">登录后查看持久化账户资金。</div>
    </div>

    <div v-if="active === 'positions'" class="table-shell compact">
      <table>
        <thead><tr><th>股票代码</th><th>总数量</th><th>可用</th><th>冻结</th><th>成本均价</th></tr></thead>
        <tbody>
          <tr v-for="position in props.positions" :key="position.symbol">
            <td><strong>{{ position.symbol }}</strong></td>
            <td>{{ formatNumber(position.quantity) }}</td>
            <td>{{ formatNumber(position.available_quantity) }}</td>
            <td>{{ formatNumber(position.frozen_quantity) }}</td>
            <td>{{ formatMoney(position.avg_price) }}</td>
          </tr>
          <tr v-if="!props.positions.length"><td colspan="5" class="empty">暂无持仓。</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="active === 'orders'" class="table-shell compact">
      <table>
        <thead><tr><th>股票代码</th><th>方向</th><th>类型</th><th>状态</th><th>数量</th><th>成交</th><th>限价</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="order in props.orders" :key="order.order_id">
            <td><strong>{{ order.symbol }}</strong></td>
            <td>{{ order.side === "buy" ? "买入" : "卖出" }}</td>
            <td>{{ order.order_type === "market" ? "市价" : "限价" }}</td>
            <td>{{ order.status }}</td>
            <td>{{ formatNumber(order.quantity) }}</td>
            <td>{{ formatNumber(order.filled_quantity) }}</td>
            <td>{{ order.limit_price ? formatMoney(order.limit_price) : '-' }}</td>
            <td><button v-if="canCancel(order)" class="small-action" @click="emit('cancel-order', order.order_id)">撤单</button></td>
          </tr>
          <tr v-if="!props.orders.length"><td colspan="8" class="empty">暂无订单。</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="active === 'trades'" class="table-shell compact">
      <table>
        <thead><tr><th>股票代码</th><th>方向</th><th>价格</th><th>数量</th><th>成交额</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="trade in props.trades" :key="trade.trade_id">
            <td><strong>{{ trade.symbol }}</strong></td>
            <td>{{ trade.side === "buy" ? "买入" : "卖出" }}</td>
            <td>{{ formatMoney(trade.price) }}</td>
            <td>{{ formatNumber(trade.quantity) }}</td>
            <td>{{ formatMoney(trade.notional) }}</td>
            <td>{{ trade.created_at }}</td>
          </tr>
          <tr v-if="!props.trades.length"><td colspan="6" class="empty">暂无成交。</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="active === 'cashflows'" class="table-shell compact">
      <table>
        <thead><tr><th>类型</th><th>金额</th><th>余额</th><th>关联单号</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="flow in props.cashflows" :key="flow.id">
            <td>{{ flow.flow_type }}</td>
            <td :class="flow.amount >= 0 ? 'positive' : 'negative'">{{ formatMoney(flow.amount) }}</td>
            <td>{{ formatMoney(flow.balance_after) }}</td>
            <td>{{ flow.ref_id || '-' }}</td>
            <td>{{ flow.created_at }}</td>
          </tr>
          <tr v-if="!props.cashflows.length"><td colspan="5" class="empty">暂无资金流水。</td></tr>
        </tbody>
      </table>
    </div>

    <StrategyPanel
      v-if="active === 'strategies'"
      :strategies="props.strategies"
      :loading="false"
      :authenticated="authenticated"
      @create="emit('create-strategy', $event)"
      @start="emit('start-strategy', $event)"
      @stop="emit('stop-strategy', $event)"
      @run-once="emit('run-strategy-once', $event)"
    />

    <div v-if="active === 'analysis'" class="metric-grid">
      <div class="metric"><span>交易次数</span><strong>{{ formatNumber(userAnalysis?.trade_count) }}</strong></div>
      <div class="metric"><span>胜率</span><strong>{{ formatPercent(userAnalysis?.win_rate) }}</strong></div>
      <div class="metric"><span>总盈亏</span><strong>{{ formatMoney(userAnalysis?.total_pnl) }}</strong></div>
      <div class="metric"><span>风险敞口</span><strong>{{ formatMoney(userAnalysis?.exposure_notional) }}</strong></div>
    </div>

    <div v-if="active === 'market'" class="metric-grid">
      <div class="metric"><span>股票代码数量</span><strong>{{ formatNumber(marketAnalysis?.symbol_count) }}</strong></div>
      <div class="metric"><span>平均价格</span><strong>{{ formatMoney(marketAnalysis?.avg_price) }}</strong></div>
      <div class="metric"><span>总成交量</span><strong>{{ formatNumber(marketAnalysis?.total_volume) }}</strong></div>
      <div class="metric"><span>20 窗口波动率</span><strong>{{ formatMoney(marketAnalysis?.volatility_20) }}</strong></div>
    </div>
  </section>
</template>
