<script setup>
defineProps({ status: Object, health: Object });
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
      <div class="status-pill" :class="health?.status === 'ok' ? 'good' : 'warn'">
        API {{ health?.status === 'ok' ? '正常' : '检查中' }}
      </div>
      <div class="status-pill" :class="status?.redis_connected ? 'good' : 'warn'">
        Redis {{ status?.redis_connected ? '已连接' : '未知' }}
      </div>
      <div class="status-pill" :class="status?.market_loop_running ? 'good' : 'warn'">
        行情循环 {{ status?.market_loop_running ? '运行中' : '已停止' }}
      </div>
    </div>
  </section>
</template>
