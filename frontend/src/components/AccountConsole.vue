<script setup>
import { ref } from "vue";
import { formatMoney, formatNumber, formatPercent } from "../utils";

const props = defineProps({ portfolio: Object, userAnalysis: Object, marketAnalysis: Object });
const emit = defineEmits(["refresh-portfolio", "refresh-user", "refresh-market"]);
const active = ref("portfolio");

function switchTab(tab) {
  active.value = tab;
  if (tab === "portfolio") emit("refresh-portfolio");
  if (tab === "user") emit("refresh-user");
  if (tab === "market") emit("refresh-market");
}
</script>

<template>
  <section class="panel account-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">风控与分析</p>
        <h2>账户控制台</h2>
      </div>
    </div>

    <div class="tab-strip">
      <button :class="{ active: active === 'portfolio' }" @click="switchTab('portfolio')">持仓</button>
      <button :class="{ active: active === 'user' }" @click="switchTab('user')">用户分析</button>
      <button :class="{ active: active === 'market' }" @click="switchTab('market')">市场分析</button>
    </div>

    <div v-if="active === 'portfolio'" class="account-body">
      <div v-if="portfolio" class="metric-grid">
        <div class="metric"><span>现金</span><strong>{{ formatMoney(portfolio.cash) }}</strong></div>
        <div class="metric"><span>总权益</span><strong>{{ formatMoney(portfolio.total_equity) }}</strong></div>
        <div class="metric"><span>已实现盈亏</span><strong>{{ formatMoney(portfolio.realized_pnl) }}</strong></div>
        <div class="metric"><span>持仓数</span><strong>{{ formatNumber(portfolio.positions?.length) }}</strong></div>
      </div>
      <div class="table-shell compact">
        <table>
          <thead><tr><th>股票代码</th><th>数量</th><th>成本均价</th><th>市场价</th><th>未实现盈亏</th></tr></thead>
          <tbody>
            <tr v-for="position in portfolio?.positions || []" :key="position.symbol">
              <td><strong>{{ position.symbol }}</strong></td>
              <td>{{ formatNumber(position.quantity) }}</td>
              <td>{{ formatMoney(position.avg_price) }}</td>
              <td>{{ formatMoney(position.market_price) }}</td>
              <td :class="position.unrealized_pnl >= 0 ? 'positive' : 'negative'">{{ formatMoney(position.unrealized_pnl) }}</td>
            </tr>
            <tr v-if="!portfolio?.positions?.length"><td colspan="5" class="empty">暂无持仓。</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="active === 'user'" class="metric-grid">
      <div class="metric"><span>交易次数</span><strong>{{ formatNumber(userAnalysis?.trade_count) }}</strong></div>
      <div class="metric"><span>胜率</span><strong>{{ formatPercent(userAnalysis?.win_rate) }}</strong></div>
      <div class="metric"><span>总盈亏</span><strong>{{ formatMoney(userAnalysis?.total_pnl) }}</strong></div>
      <div class="metric"><span>风险敞口</span><strong>{{ formatMoney(userAnalysis?.exposure_notional) }}</strong></div>
    </div>

    <div v-if="active === 'market'" class="metric-grid">
      <div class="metric"><span>股票代码数量</span><strong>{{ formatNumber(marketAnalysis?.symbol_count) }}</strong></div>
      <div class="metric"><span>平均价格</span><strong>{{ formatMoney(marketAnalysis?.avg_price) }}</strong></div>
      <div class="metric"><span>总成交量</span><strong>{{ formatNumber(marketAnalysis?.total_volume) }}</strong></div>
      <div class="metric"><span>20窗口波动率</span><strong>{{ formatMoney(marketAnalysis?.volatility_20) }}</strong></div>
    </div>
  </section>
</template>
