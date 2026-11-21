<template>
  <main class="auth-shell">
    <section class="auth-card">
      <p class="eyebrow">Bookkeeping</p>
      <h1>记好每一天</h1>
      <p class="auth-intro">登录你的专属账本，在手机和网页同步收支。</p>
      <div class="period-tabs auth-tabs">
        <button type="button" :class="{ active: !registering }" @click="registering = false">登录</button>
        <button type="button" :class="{ active: registering }" @click="registering = true">注册</button>
      </div>
      <form @submit.prevent="submit">
        <label>用户名<input v-model.trim="username" autocomplete="username" minlength="3" maxlength="40" required placeholder="3–40 个字符" /></label>
        <label>密码<input v-model="password" type="password" :autocomplete="registering ? 'new-password' : 'current-password'" minlength="10" maxlength="128" required placeholder="至少 10 个字符" /></label>
        <label v-if="registering">确认密码<input v-model="confirmation" type="password" autocomplete="new-password" minlength="10" maxlength="128" required /></label>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <button class="primary-btn auth-submit" :disabled="busy">{{ busy ? '连接中…' : registering ? '创建账号' : '登录账本' }}</button>
      </form>
      <p class="auth-footnote">手动记账免费使用，无需配置 AI 密钥。</p>
      <details v-if="native" class="server-settings">
        <summary>服务器设置</summary>
        <form @submit.prevent="saveServer">
          <label>服务器地址<input v-model.trim="server" type="url" placeholder="https://你的服务器域名" required /></label>
          <p class="muted">本机测试：USB 连接电脑并执行 adb reverse tcp:8000 tcp:8000，地址填写 http://127.0.0.1:8000。</p>
          <button class="secondary-btn" :disabled="busy">保存地址</button>
          <p v-if="serverMessage" role="status">{{ serverMessage }}</p>
        </form>
      </details>
    </section>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Capacitor } from "@capacitor/core";
import { api, authenticate, serverAddress, setServerAddress } from "../services/api";
const router = useRouter();
const native = Capacitor.isNativePlatform();
const registering = ref(false), username = ref(""), password = ref(""), confirmation = ref("");
const busy = ref(false), error = ref(""), server = ref(serverAddress.value), serverMessage = ref("");
async function submit() {
  if (registering.value && password.value !== confirmation.value) { error.value = "两次密码不一致"; return; }
  busy.value = true;
  error.value = "";
  try {
    await authenticate(registering.value ? "register" : "login", username.value, password.value);
    password.value = "";
    confirmation.value = "";
    const keys = await api("/api/keys");
    await router.replace(keys.length ? "/" : "/keys");
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
async function saveServer() {
  try { await setServerAddress(server.value); serverMessage.value = "地址已保存，可以登录或注册"; }
  catch (err) { serverMessage.value = err.message; }
}
</script>
