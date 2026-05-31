<script setup>
import { computed, reactive, ref } from "vue";

const props = defineProps({ loading: Boolean });
const emit = defineEmits(["login", "register"]);
const mode = ref("login");
const form = reactive({ username: "", email: "", password: "", confirmPassword: "" });

const passwordMismatch = computed(() => mode.value === "register" && form.password !== form.confirmPassword);
const passwordMissing = computed(() => mode.value === "register" && !form.confirmPassword);
const canSubmit = computed(() => !props.loading && !passwordMismatch.value && !passwordMissing.value);

function submit() {
  if (mode.value === "register" && (passwordMismatch.value || passwordMissing.value)) return;

  const payload = {
    username: form.username.trim(),
    password: form.password,
  };
  if (mode.value === "register" && form.email.trim()) payload.email = form.email.trim();
  emit(mode.value, payload);
}
</script>

<template>
  <section class="panel auth-panel">
    <div>
      <p class="eyebrow">身份认证</p>
      <h2>{{ mode === "login" ? "登录交易工作台" : "创建模拟账户" }}</h2>
      <p class="subtle">登录后可使用数据库持久化订单、撤单、成交、资金与持仓查询。</p>
    </div>

    <div class="tab-strip auth-tabs">
      <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
      <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <label>用户名<input v-model="form.username" required minlength="3" maxlength="64" autocomplete="username" /></label>
      <label v-if="mode === 'register'">邮箱<input v-model="form.email" type="email" maxlength="255" autocomplete="email" /></label>
      <label>密码<input v-model="form.password" required type="password" minlength="6" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" /></label>
      <label v-if="mode === 'register'">确认密码<input v-model="form.confirmPassword" required type="password" minlength="6" autocomplete="new-password" /></label>
      <p v-if="passwordMismatch" class="subtle negative">两次输入的密码不一致</p>
      <button class="primary-action" :disabled="!canSubmit">
        {{ loading ? "处理中..." : mode === "login" ? "登录" : "注册并进入" }}
      </button>
    </form>
  </section>
</template>
