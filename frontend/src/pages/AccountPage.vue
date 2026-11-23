<template>
  <main class="app-shell account-shell">
    <router-link class="back-link" to="/">返回账本</router-link>
    <section class="auth-card account-card">
      <p class="eyebrow">Account</p><h1>账号设置</h1>
      <p>当前账号：<strong>{{ currentUser?.username }}</strong></p>
      <p class="muted">账单保存在服务器，每个账号独立。登录有效期为 7 天。</p>
      <form @submit.prevent="changePassword">
        <h2>修改密码</h2>
        <label>当前密码<input v-model="oldPassword" type="password" autocomplete="current-password" required maxlength="128" /></label>
        <label>新密码<input v-model="newPassword" type="password" autocomplete="new-password" required minlength="10" maxlength="128" /></label>
        <label>确认新密码<input v-model="confirmation" type="password" autocomplete="new-password" required minlength="10" maxlength="128" /></label>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <button class="primary-btn" :disabled="busy">修改并重新登录</button>
      </form>
      <button class="secondary-btn logout-btn" :disabled="busy" @click="signOut">退出登录</button>
    </section>
    <section v-if="updates.supported" class="auth-card update-settings" aria-label="应用更新">
      <div><h2>应用更新</h2><p class="muted">{{ updates.current ? `当前版本 ${updates.current.versionName}` : '打开应用时自动检查新版本' }}</p></div>
      <button class="secondary-btn" :disabled="updates.checking || updates.phase === 'downloading'" @click="checkForUpdates(true)">{{ updates.checking ? '检查中…' : '检查更新' }}</button>
      <p v-if="updates.message" class="update-feedback" role="status">{{ updates.message }}</p>
      <button v-if="updates.release" class="text-button update-feedback" @click="showAvailableUpdate">查看 {{ updates.release.version_name }} 更新</button>
    </section>
  </main>
</template>
<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, clearSession, currentUser, logout } from "../services/api";
import { updateState as updates, checkForUpdates, showAvailableUpdate } from "../services/appUpdates";
const router = useRouter();
const oldPassword = ref(""), newPassword = ref(""), confirmation = ref(""), error = ref(""), busy = ref(false);
async function changePassword() {
  if (newPassword.value !== confirmation.value) { error.value = "两次新密码不一致"; return; }
  busy.value = true;
  try {
    await api("/api/auth/password", { method: "POST", body: { current_password: oldPassword.value, new_password: newPassword.value } });
    await clearSession();
    await router.replace("/login");
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
async function signOut() {
  busy.value = true;
  try { await logout(); await router.replace("/login"); }
  catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
</script>
