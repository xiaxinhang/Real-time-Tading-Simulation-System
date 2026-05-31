<script setup>
import { computed } from "vue";
import { formatTime } from "../utils";

const props = defineProps({ status: Object, health: Object, currentUser: Object, authenticated: Boolean });
const emit = defineEmits(["logout"]);

const checks = computed(() => ({
  api: props.health?.status === "ok",
  redis: !!props.status?.redis_connected,
  market: !!props.status?.market_loop_running,
}));

const allHealthy = computed(() => checks.value.api && checks.value.redis && checks.value.market);

const dataSourceLabel = computed(() => {
  const source = props.status?.market_data_source || "unknown";
  if (source === "real_yahoo") return "真实行情（Yahoo）";
  if (source === "real_stooq") return "真实行情（Stooq）";
  if (source === "fallback_cache") return "拉取失败，显示最近一次成功数据";
  if (source === "unavailable") return "暂无可用真实行情";
  if (source === "not_loaded") return "等待首次真实行情";
  return "未知";
});

const dataSourceTone = computed(() => {
  const source = props.status?.market_data_source || "unknown";
  if ((source === "real_yahoo" || source === "real_stooq") && !props.status?.market_data_stale) return "good";
  if (source === "fallback_cache" || source === "unavailable" || props.status?.market_data_stale) return "warn";
  return "";
});

const lastPullLabel = computed(() => {
  const ts = props.status?.last_successful_pull_ts;
  return ts ? formatTime(ts) : "暂无";
});

const dataSourceErrorShort = computed(() => {
  const raw = String(props.status?.market_data_error || "").trim();
  if (!raw) return "";
  return raw.length > 120 ? `${raw.slice(0, 120)}...` : raw;
});
</script>

<template>
  <section class="hero-card">
    <div>
      <p class="eyebrow">实时撮合实验室</p>
      <h1>交易模拟仪表盘</h1>
      <p class="hero-copy">
        用 WebSocket 推送实时行情，用撮合引擎产生交易事件，并在同一个控制台观察账户、订单簿和市场分析。
      </p>
    </div>
    <div class="status-stack">
      <div class="status-pill" :class="allHealthy ? 'good' : 'warn'">
        系统状态：{{ allHealthy ? "正常" : "需检查" }}<br />
        API {{ checks.api ? "正常" : "异常" }} /
        Redis {{ checks.redis ? "已连接" : "未连接" }} /
        行情循环 {{ checks.market ? "运行中" : "已停止" }}
      </div>
      <div class="status-pill" :class="dataSourceTone">
        行情数据：{{ dataSourceLabel }}
        <span class="status-subline">上次成功：{{ lastPullLabel }}</span>
        <span v-if="dataSourceErrorShort" class="status-subline">原因：{{ dataSourceErrorShort }}</span>
      </div>
      <div class="status-pill" :class="authenticated ? 'good' : 'warn'">
        账户：{{ authenticated ? currentUser?.username : "未登录" }}
        <button v-if="authenticated" class="link-button" @click="emit('logout')">退出</button>
      </div>
    </div>
  </section>
</template>
