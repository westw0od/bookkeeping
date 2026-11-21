<template>
  <main class="connections">
    <router-link class="connections-back" to="/"><ArrowLeft :size="15" /> 返回账本</router-link>
    <header class="connections-heading">
      <div><p class="connections-kicker">AI CONNECTIONS</p><h1>API Key 管理<span>让记账，多一点智能。</span></h1>
        <p class="connections-description">连接你喜欢的 AI。保存一次，手机与网页随时可用。</p></div>
      <button ref="addTrigger" class="connect-primary" :disabled="busy || loading || keys.length >= 10" @click="openAdd"><Plus :size="18" /> 添加 Key</button>
    </header>

    <div v-if="error && !showAdd && !pendingDelete" class="connections-notice is-error" role="alert"><CircleAlert :size="17" />{{ error }}<button :disabled="busy" @click="refresh">重试</button></div>
    <div v-if="message" class="connections-notice is-success" role="status"><Check :size="17" />{{ message }}</div>

    <section v-if="loading" class="connection-loading" aria-label="正在加载连接"><span class="skeleton-line"></span><span class="skeleton-line short"></span></section>
    <section v-else-if="defaultKey" class="active-connection" aria-label="当前默认连接">
      <div class="active-orbit" aria-hidden="true"></div>
      <div class="active-topline"><span><i></i> 当前默认连接</span><span class="active-persistence"><RefreshCw :size="13" /> 自动沿用</span></div>
      <div class="active-identity"><div class="provider-symbol active-symbol"><component :is="providerInfo(defaultKey.provider).icon" :size="26" :stroke-width="1.7" /></div>
        <div><h2>{{ defaultKey.label }}</h2><p>{{ providerInfo(defaultKey.provider).name }} <span>·</span> {{ defaultKey.masked_key }}</p></div></div>
      <div class="active-details"><div><span>文字模型</span><code>{{ defaultKey.model }}</code></div><div><span>接口地址</span><code>{{ defaultKey.base_url || providerInfo(defaultKey.provider).url }}</code></div></div>
      <div class="active-footer"><span><Check :size="14" /> 下次登录，无需重复填写</span><span><ImageIcon v-if="defaultKey.vision_model" :size="14" /><MessageSquareText v-else :size="14" />{{ defaultKey.vision_model ? '文字与图片' : '文字记账' }}</span></div>
    </section>
    <section v-else class="connection-welcome">
      <div class="welcome-art" aria-hidden="true"><div class="welcome-grid"></div><div class="welcome-key"><KeyRound :size="36" :stroke-width="1.5" /></div><span class="welcome-spark"><Sparkles :size="16" /></span></div>
      <div class="welcome-copy"><span class="welcome-label">从一句话，开始记账</span><h2>把你的 AI 接进来</h2><p>一句“午饭花了 25 元”，就能生成账单草稿。<br class="desktop-break" />先添加一个 Key，让琐碎的记录简单一点。</p>
        <button class="connect-primary" :disabled="busy" @click="openAdd"><Plus :size="17" /> 添加第一个 Key</button>
        <router-link class="welcome-skip" to="/">先手动记账 <ArrowUpRight :size="13" /></router-link></div>
    </section>

    <div class="connections-grid">
      <section class="connections-library">
        <header class="library-heading"><div><h2>我的 Key <span>{{ keys.length }}</span></h2><p>选择一个默认连接，用于后续 AI 识别与分析。</p></div><span class="library-capacity">最多 10 个</span></header>
        <div v-if="!keys.length && !loading" class="library-empty"><div class="empty-symbol"><KeyRound :size="23" /></div><p>你的 Key 会出现在这里</p><span>添加后，随时切换或删除。</span></div>
        <article v-for="key in keys" :key="key.id" class="connection-row" :class="{ 'is-default': key.is_default }">
          <div class="provider-symbol" :style="{ background: providerInfo(key.provider).tint, color: providerInfo(key.provider).color }"><component :is="providerInfo(key.provider).icon" :size="23" :stroke-width="1.7" /></div>
          <div class="connection-row-info"><div class="connection-row-title"><h3>{{ key.label }}</h3><span v-if="key.is_default" class="connection-default"><Check :size="11" />默认使用</span></div>
            <p>{{ providerInfo(key.provider).name }} <span>·</span> <code>{{ key.masked_key }}</code></p><code class="connection-model">{{ key.model }}</code></div>
          <div class="connection-row-actions"><button v-if="!key.is_default" class="connect-switch" :disabled="busy" @click="makeDefault(key)">设为默认</button><button class="connect-delete" aria-label="删除" :title="`删除 ${key.label}`" :disabled="busy" @click="requestDelete(key)"><Trash2 :size="17" /></button></div>
        </article>
        <button v-if="keys.length" class="library-add" :disabled="busy || keys.length >= 10" @click="openAdd"><Plus :size="16" /> 添加另一个 Key</button>
      </section>

      <aside class="connections-aside">
        <section class="connection-guide"><span class="guide-icon"><Sparkles :size="19" /></span><h2>小配置，大省心</h2><ol><li><span>01</span><div><strong>选一个服务商</strong><p>已预设山大 AI 等常用平台。</p></div></li><li><span>02</span><div><strong>粘贴你的 Key</strong><p>地址和模型会自动填好。</p></div></li><li><span>03</span><div><strong>回到账本，开始记录</strong><p>默认 Key 会一直为你保留。</p></div></li></ol></section>
        <div class="connections-providers"><p>支持的服务商</p><div><span v-for="item in providers" :key="item.id"><component :is="item.icon" :size="14" />{{ item.short }}</span></div></div>
      </aside>
    </div>
    <footer class="connections-security"><ShieldCheck :size="17" /><span>Key 加密保存，仅展示末四位。你的连接，只为你的账本使用。</span></footer>

    <div v-if="showAdd" class="connect-overlay" @click.self="closeAdd" @keydown="dialogKeys">
      <section ref="addDialog" class="connect-dialog" role="dialog" aria-modal="true" aria-labelledby="add-key-title">
        <header class="connect-dialog-heading"><div class="dialog-icon"><KeyRound :size="22" /></div><div><h2 id="add-key-title">添加 AI Key</h2><p>一次连接，每次记账都能用。</p></div><button class="dialog-close" type="button" aria-label="关闭添加窗口" :disabled="busy" @click="closeAdd"><X :size="20" /></button></header>
        <form class="connect-form" @submit.prevent="addKey">
          <label>服务商<select v-model="provider" aria-label="服务商" :disabled="busy" @change="setModels"><option v-for="item in providers" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
          <div class="provider-preview"><span :style="{ color: selectedProvider.color }"><component :is="selectedProvider.icon" :size="19" /></span><div><strong>{{ selectedProvider.name }}</strong><code>{{ selectedProvider.url }}</code></div><span class="compatible-badge">兼容 OpenAI</span></div>
          <label class="key-secret-label" for="new-api-key">API Key</label><div class="secret-field"><input id="new-api-key" ref="secretInput" v-model.trim="secret" :type="revealSecret ? 'text' : 'password'" autocomplete="off" :disabled="busy" required minlength="8" maxlength="512" placeholder="粘贴你的 API Key" /><button type="button" :aria-label="revealSecret ? '隐藏 Key' : '显示 Key'" @click="revealSecret = !revealSecret"><EyeOff v-if="revealSecret" :size="18" /><Eye v-else :size="18" /></button></div>
          <p class="connect-field-hint"><LockKeyhole :size="12" /> 加密保存后，不再展示完整 Key。</p>
          <div class="preset-model"><span>当前文字模型</span><code>{{ model }}</code></div>
          <details class="connect-advanced"><summary>模型与备注 <span>可选设置</span><ChevronDown :size="15" /></summary><div>
            <label>名称<input v-model.trim="label" :disabled="busy" maxlength="50" :placeholder="`${selectedProvider.short} · 日常记账`" /></label>
            <label>文字模型<input v-model.trim="model" :disabled="busy" required maxlength="100" /></label>
            <label>图片模型（可选）<input v-model.trim="visionModel" :disabled="busy" maxlength="100" placeholder="留空则不启用图片识别" /></label>
            <p class="connect-field-hint">模型需在服务商账号中可用；图片识别需单独配置支持图片输入的模型。</p>
          </div></details>
          <label v-if="keys.length" class="connect-checkbox"><input v-model="setAsDefault" type="checkbox" :disabled="busy" /> 保存后设为默认 Key</label>
          <p v-if="error" class="connections-notice is-error dialog-error" role="alert"><CircleAlert :size="16" />{{ error }}</p>
          <div class="connect-dialog-footer"><button class="connect-cancel" type="button" :disabled="busy" @click="closeAdd">取消</button><button class="connect-primary" :disabled="busy"><LoaderCircle v-if="busy" class="connect-spinner" :size="17" /><Plus v-else :size="17" />{{ busy ? '保存中…' : '保存 Key' }}</button></div>
          <p class="connect-billing-note">使用 AI 时，会消耗对应服务商的额度。</p>
        </form>
      </section>
    </div>

    <div v-if="pendingDelete" class="connect-overlay" @click.self="closeDelete" @keydown="dialogKeys">
      <section ref="deleteDialog" class="connect-dialog connect-confirm" role="dialog" aria-modal="true" aria-labelledby="delete-key-title" tabindex="-1">
        <div class="delete-dialog-icon"><Trash2 :size="24" /></div><h2 id="delete-key-title">删除“{{ pendingDelete.label }}”？</h2><p>删除后，本账号将停止使用这个 Key。{{ pendingDelete.is_default && keys.length > 1 ? '剩余的第一个 Key 会自动设为默认。' : '你可以随时重新添加。' }}</p><p class="connect-field-hint">此操作不会注销服务商平台上的密钥。</p>
        <p v-if="error" class="connections-notice is-error" role="alert">{{ error }}</p><div class="connect-dialog-footer"><button class="connect-cancel" :disabled="busy" @click="closeDelete">取消</button><button class="connect-confirm-delete" :disabled="busy" @click="confirmDelete">{{ busy ? '删除中…' : '确认删除' }}</button></div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { ArrowLeft, ArrowUpRight, Bot, Check, ChevronDown, CircleAlert, Cloud, Eye, EyeOff, GraduationCap, Image as ImageIcon, KeyRound, LoaderCircle, LockKeyhole, MessageSquareText, Plus, RefreshCw, ShieldCheck, Sparkles, Trash2, X } from "@lucide/vue";
import { api } from "../services/api";

const providers = [
  { id: "sdu", name: "山大 AI", short: "山大 AI", icon: GraduationCap, tint: "#fff1f3", color: "#9b2647", url: "https://xplt.sdu.edu.cn:4000/v1", model: "SDU-AI/DeepSeek-V4-Flash", vision: "" },
  { id: "deepseek", name: "DeepSeek", short: "DeepSeek", icon: Sparkles, tint: "#edf2ff", color: "#5269d9", url: "https://api.deepseek.com/v1", model: "deepseek-chat", vision: "" },
  { id: "openai", name: "OpenAI", short: "OpenAI", icon: Bot, tint: "#eaf6f0", color: "#287357", url: "https://api.openai.com/v1", model: "gpt-4o-mini", vision: "gpt-4o-mini" },
  { id: "dashscope", name: "阿里云百炼 · 通义千问", short: "通义千问", icon: Cloud, tint: "#f3edff", color: "#7751be", url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", vision: "qwen-vl-plus" }
];
const keys = ref([]), loading = ref(true), busy = ref(false), error = ref(""), message = ref("");
const showAdd = ref(false), pendingDelete = ref(null), revealSecret = ref(false), setAsDefault = ref(false);
const provider = ref("sdu"), label = ref(""), secret = ref(""), model = ref(providers[0].model), visionModel = ref("");
const addTrigger = ref(null), secretInput = ref(null), addDialog = ref(null), deleteDialog = ref(null);
const defaultKey = computed(() => keys.value.find(key => key.is_default));
const selectedProvider = computed(() => providerInfo(provider.value));
function providerInfo(id) { return providers.find(item => item.id === id) || providers[0]; }
function setModels() { model.value = selectedProvider.value.model; visionModel.value = selectedProvider.value.vision; }
async function load() { keys.value = await api("/api/keys"); }
async function refresh() { loading.value = true; error.value = ""; try { await load(); } catch (err) { error.value = err.message; } finally { loading.value = false; } }
onMounted(refresh);
watch(() => showAdd.value || !!pendingDelete.value, value => { document.body.style.overflow = value ? "hidden" : ""; });
onUnmounted(() => { document.body.style.overflow = ""; secret.value = ""; });
async function openAdd() {
  provider.value = "sdu"; label.value = ""; secret.value = ""; revealSecret.value = false; setAsDefault.value = false;
  setModels(); error.value = ""; message.value = ""; showAdd.value = true;
  await nextTick(); secretInput.value?.focus();
}
function closeAdd() { if (busy.value) return; showAdd.value = false; secret.value = ""; error.value = ""; addTrigger.value?.focus(); }
function closeDelete() { if (!busy.value) { pendingDelete.value = null; error.value = ""; addTrigger.value?.focus(); } }
function dialogKeys(event) {
  if (event.key === "Escape") { event.preventDefault(); showAdd.value ? closeAdd() : closeDelete(); }
  if (event.key !== "Tab") return;
  const dialog = showAdd.value ? addDialog.value : deleteDialog.value;
  const nodes = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, a[href]')].filter(node => node.getClientRects().length);
  const first = nodes[0], last = nodes.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
}
async function addKey() {
  if (busy.value) return;
  busy.value = true; error.value = ""; message.value = "";
  try {
    const saved = await api("/api/keys", { method: "POST", body: { label: label.value || `${selectedProvider.value.short} · 日常记账`,
      provider: provider.value, api_key: secret.value, model: model.value, vision_model: visionModel.value || null } });
    secret.value = "";
    showAdd.value = false;
    if (setAsDefault.value && !saved.is_default) await api(`/api/keys/${saved.id}/default`, { method: "POST" });
    await load(); message.value = "Key 已保存，下次登录可以继续使用。";
    await nextTick(); addTrigger.value?.focus();
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
async function makeDefault(key) {
  busy.value = true; error.value = ""; message.value = "";
  try { await api(`/api/keys/${key.id}/default`, { method: "POST" }); await load(); message.value = `已将「${key.label}」设为默认连接。`; }
  catch (err) { error.value = err.message; } finally { busy.value = false; }
}
async function requestDelete(key) { pendingDelete.value = key; error.value = ""; message.value = ""; await nextTick(); deleteDialog.value?.focus(); }
async function confirmDelete() {
  busy.value = true; error.value = "";
  try { await api(`/api/keys/${pendingDelete.value.id}`, { method: "DELETE" }); pendingDelete.value = null; await load(); message.value = "Key 已删除。"; }
  catch (err) { error.value = err.message; } finally { busy.value = false; }
}
</script>

<style scoped>
.connections { --ink: #20253e; --soft: #81879c; --line: #e8eaf1; --accent: #0071e3; width: min(1056px, calc(100% - 48px)); margin: 0 auto; padding: 29px 0 calc(32px + env(safe-area-inset-bottom)); color: var(--ink); }
.connections button { font-family: inherit; transition: background .18s, transform .18s, box-shadow .18s; }
.connections button:focus-visible, .connections a:focus-visible, .connect-advanced summary:focus-visible { outline: 3px solid #b2adfa; outline-offset: 3px; }
.connections-back { display: inline-flex; align-items: center; gap: 7px; color: #7c8297; font-size: 12px; }
.connections-back:hover { color: var(--accent); }
.connections-heading { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin: 31px 0 29px; }
.connections-kicker { margin: 0 0 12px; color: #8a88b0; letter-spacing: 2.3px; font-size: 10px; font-weight: 700; }
.connections-heading h1 { display: flex; align-items: baseline; gap: 18px; margin: 0; font-size: 30px; letter-spacing: -.8px; font-weight: 750; }
.connections-heading h1 span { color: #a3a7b7; font-size: 14px; font-weight: 400; letter-spacing: 0; }
.connections-description { color: var(--soft); font-size: 13px; line-height: 1.7; margin: 12px 0 0; }
.connect-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 19px; border: 0; border-radius: 12px; color: #fff; background: var(--accent); font-size: 13px; font-weight: 600; box-shadow: 0 4px 10px #6260dd1c; white-space: nowrap; }
.connect-primary:hover:not(:disabled) { background: #5452cd; transform: translateY(-1px); }
.active-connection { position: relative; overflow: hidden; border: 1px solid #383b69; border-radius: 22px; padding: 26px 30px 0; background: linear-gradient(115deg, #282c4d, #353663 78%, #4a447a); color: #fff; box-shadow: 0 12px 28px #272a4e0d; }
.active-orbit { position: absolute; pointer-events: none; width: 340px; height: 340px; border: 1px solid #ffffff08; border-radius: 50%; right: -50px; top: -145px; box-shadow: 0 0 0 40px #ffffff03, 0 0 0 80px #ffffff03; }
.active-topline, .active-footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; position: relative; }
.active-topline > span { display: inline-flex; align-items: center; gap: 8px; color: #cdcde4; font-size: 11px; }
.active-topline i { width: 6px; height: 6px; border-radius: 50%; background: #a6e0c1; box-shadow: 0 0 0 4px #a6e0c111; }
.active-topline .active-persistence { color: #c4c4de; font-size: 10px; }
.active-identity { position: relative; display: flex; align-items: center; gap: 15px; margin-top: 24px; }
.provider-symbol { width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center; flex-shrink: 0; }
.active-symbol { width: 53px; height: 53px; background: #ffffff10; border: 1px solid #ffffff15; border-radius: 16px; color: #d6d6fb; }
.active-identity h2 { margin: 0 0 8px; font-size: 23px; font-weight: 600; letter-spacing: -.3px; overflow-wrap: anywhere; }
.active-identity p { color: #babbd4; margin: 0; font-size: 11px; }
.active-identity p span { padding: 0 6px; color: #73769a; }
.active-details { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 25px 0 23px; position: relative; }
.active-details > div { min-width: 0; }
.active-details span { display: block; color: #9397bc; font-size: 10px; margin-bottom: 7px; }
.active-details code { color: #e2e2f4; font-size: 13px; overflow-wrap: anywhere; line-height: 1.6; }
.active-footer { border-top: 1px solid #ffffff0d; padding: 14px 0; }
.active-footer span { display: inline-flex; align-items: center; gap: 6px; color: #a8adcc; font-size: 10px; }
.active-footer span:first-child svg { color: #a8d4bd; }
.connection-welcome { background: linear-gradient(120deg, #efedff, #f4f4ff 56%, #fafbff); border: 1px solid #e5e3f3; border-radius: 22px; min-height: 250px; display: flex; align-items: center; justify-content: center; gap: 48px; padding: 32px; overflow: hidden; }
.welcome-art { position: relative; width: 160px; height: 160px; display: grid; place-items: center; flex-shrink: 0; }
.welcome-grid { position: absolute; inset: 0; background-image: linear-gradient(#7773b10b 1px, transparent 1px), linear-gradient(90deg, #7773b10b 1px, transparent 1px); background-size: 20px 20px; mask-image: radial-gradient(black, transparent 72%); }
.welcome-key { display: grid; place-items: center; width: 82px; height: 94px; transform: rotate(-12deg); border: 1px solid #ffffff; border-radius: 22px; color: #7770c7; background: linear-gradient(120deg, #fff, #eeedff); box-shadow: 10px 14px 30px #8076ba14; }
.welcome-spark { display: grid; place-items: center; position: absolute; width: 32px; height: 32px; border-radius: 10px; right: 5px; top: 17px; color: #9b8bc1; background: #fff; box-shadow: 0 6px 15px #9b8bc110; transform: rotate(13deg); }
.welcome-label { color: #8f87b3; font-size: 10px; letter-spacing: 1px; }
.welcome-copy h2 { font-size: 27px; font-weight: 650; letter-spacing: -.5px; margin: 11px 0 13px; }
.welcome-copy > p { color: #8b8b9f; font-size: 12px; line-height: 1.9; margin-bottom: 20px; }
.welcome-copy .connect-primary { padding: 11px 15px; font-size: 12px; }
.welcome-skip { display: inline-flex; gap: 3px; align-items: center; font-size: 11px; color: #8a86a2; margin-left: 16px; }
.connections-grid { display: grid; grid-template-columns: minmax(0, 1fr) 265px; gap: 24px; margin-top: 25px; align-items: start; }
.connections-library { background: #fff; border: 1px solid var(--line); border-radius: 20px; overflow: hidden; }
.library-heading { display: flex; align-items: flex-start; justify-content: space-between; padding: 24px 25px 21px; gap: 12px; }
.library-heading h2 { display: flex; align-items: center; gap: 9px; margin: 0 0 7px; font-size: 15px; font-weight: 650; }
.library-heading h2 > span { font-size: 10px; display: grid; place-items: center; padding: 3px 7px; background: #f2f3f9; color: #9396ac; border-radius: 6px; font-weight: 500; }
.library-heading p { color: #9b9fb1; font-size: 11px; margin: 0; line-height: 1.6; }
.library-capacity { color: #adb1c1; font-size: 10px; white-space: nowrap; padding-top: 3px; }
.library-empty { display: flex; align-items: center; flex-direction: column; border-top: 1px solid #f3f4f8; padding: 30px 0 36px; }
.empty-symbol { width: 48px; height: 48px; display: grid; place-items: center; background: #f7f7fb; color: #b6b4cd; border: 1px dashed #e0dfed; border-radius: 15px; }
.library-empty p { color: #9599ac; font-size: 12px; margin: 14px 0 7px; }
.library-empty > span { color: #b6b8c6; font-size: 10px; }
.connection-row { display: flex; align-items: center; gap: 13px; padding: 22px 25px; border-top: 1px solid #f0f1f6; }
.connection-row-info { min-width: 0; flex: 1; }
.connection-row-title { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.connection-row-title h3 { margin: 0; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.connection-default { display: inline-flex; align-items: center; gap: 3px; color: #6c63b4; background: #f1effb; border: 1px solid #e9e5f9; padding: 3px 6px; border-radius: 5px; font-size: 9px; white-space: nowrap; }
.connection-row-info p { font-size: 12px; color: #9195aa; margin: 8px 0 5px; }
.connection-row-info p > span { margin: 0 5px; color: #c7c9d4; }
.connection-row-info p > code { font-size: 10px; letter-spacing: .7px; }
.connection-model { display: block; color: #9397ad; font-size: 11px; overflow-wrap: anywhere; line-height: 1.6; }
.connection-row-actions { display: flex; align-items: center; gap: 10px; }
.connect-switch { border: 1px solid #e5e5f2; color: #8179be; background: #fff; border-radius: 8px; padding: 7px 9px; font-size: 10px; white-space: nowrap; }
.connect-switch:hover { background: #f7f5ff; }
.connect-delete { border: 0; background: transparent; color: #b7bac9; padding: 8px; border-radius: 8px; display: grid; place-items: center; }
.connect-delete:hover { color: #d47486; background: #fff3f6; }
.library-add { display: flex; justify-content: center; align-items: center; gap: 6px; border: 0; border-top: 1px dashed #e9e9f2; background: #fcfcfe; width: 100%; padding: 15px; font-size: 11px; color: #9a96b3; }
.library-add:hover { background: #f7f6fe; color: var(--accent); }
.connection-guide { padding: 24px; background: #f0f1f8; border: 1px solid #e9eaf2; border-radius: 20px; }
.guide-icon { display: grid; place-items: center; width: 35px; height: 35px; border: 1px solid #e2e2f0; border-radius: 11px; color: #8a84ba; background: #f9f9fd; }
.connection-guide h2 { font-size: 15px; font-weight: 600; margin: 15px 0 22px; }
.connection-guide ol { list-style: none; padding: 0; margin: 0; }
.connection-guide li { display: flex; gap: 12px; margin: 0 0 20px; }
.connection-guide li:last-child { margin-bottom: 0; }
.connection-guide li > span { color: #b2b2cb; font-size: 10px; padding-top: 2px; }
.connection-guide strong { font-size: 11px; color: #686d88; font-weight: 500; }
.connection-guide li p { color: #a0a3b6; font-size: 10px; line-height: 1.6; margin: 6px 0 0; }
.connections-providers { padding: 20px 5px 0; }
.connections-providers > p { color: #a1a4b6; font-size: 10px; margin: 0 0 13px; }
.connections-providers > div { display: flex; flex-wrap: wrap; gap: 12px 15px; }
.connections-providers span { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; color: #9498af; }
.connections-security { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 25px 0 0; color: #a2a6ba; font-size: 10px; line-height: 1.7; }
.connections-security svg { color: #9694b6; flex-shrink: 0; }
.connections-notice { display: flex; align-items: center; gap: 8px; border-radius: 10px; padding: 12px 15px; margin-bottom: 16px; font-size: 12px; line-height: 1.6; }
.connections-notice svg { flex-shrink: 0; }
.connections-notice button { border: 0; background: transparent; color: inherit; margin-left: auto; text-decoration: underline; }
.is-error { background: #fff1f3; color: #b95771; }
.is-success { background: #edf7f1; color: #54836c; }
.connection-loading { height: 245px; padding: 50px 32px; background: #ecedf5; border-radius: 22px; }
.skeleton-line { display: block; height: 22px; width: 50%; background: #e0e2ed; border-radius: 6px; }
.skeleton-line.short { height: 14px; width: 30%; margin-top: 18px; }
.connect-overlay { position: fixed; inset: 0; z-index: 150; background: #1b1d3c65; backdrop-filter: blur(5px); display: flex; align-items: center; justify-content: center; padding: 24px; overflow-y: auto; }
.connect-dialog { width: min(100%, 490px); max-height: calc(100dvh - 48px); overflow-y: auto; background: #fff; border: 1px solid #fff8; border-radius: 22px; box-shadow: 0 30px 100px #16192e30; padding: 27px 28px 20px; }
.connect-dialog-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 26px; }
.dialog-icon { background: #f0effb; color: #8176c6; border-radius: 12px; width: 43px; height: 43px; display: grid; place-items: center; }
.connect-dialog-heading h2 { font-size: 18px; margin: 0 0 6px; font-weight: 650; }
.connect-dialog-heading p { margin: 0; font-size: 11px; color: #a5a6b5; }
.dialog-close { margin-left: auto; background: none; border: 0; color: #b0b2c1; display: grid; place-items: center; padding: 7px; border-radius: 8px; }
.dialog-close:hover { background: #f3f3f9; }
.connect-form label { display: block; font-size: 12px; font-weight: 500; color: #686c85; margin-bottom: 17px; }
.connect-form input:not([type=checkbox]), .connect-form select { display: block; width: 100%; padding: 12px; margin-top: 9px; border: 1px solid #e3e5ee; border-radius: 10px; background: #fcfcff; font-size: 13px; font-weight: 400; color: #444962; outline: none; }
.connect-form input:focus, .connect-form select:focus { border-color: #a39ae5; box-shadow: 0 0 0 3px #a39ae514; }
.connect-form input::placeholder { color: #b9bbc9; }
.provider-preview { display: flex; align-items: center; gap: 10px; background: #f8f8fc; padding: 13px; border: 1px solid #f0f0f7; border-radius: 10px; margin: -3px 0 23px; }
.provider-preview > span:first-child { display: flex; align-items: center; }
.provider-preview > div { flex: 1; min-width: 0; }
.provider-preview strong { display: block; font-size: 11px; font-weight: 500; margin-bottom: 4px; color: #777a91; }
.provider-preview code { font-size: 9px; color: #a3a6b9; overflow-wrap: anywhere; }
.compatible-badge { font-size: 8px; white-space: nowrap; color: #a2a1ba; }
.connect-form .key-secret-label { margin-bottom: 0; }
.secret-field { position: relative; }
.secret-field input { padding-right: 43px !important; }
.secret-field button { display: grid; place-items: center; position: absolute; right: 6px; top: 50%; transform: translateY(-50%); border: 0; background: none; padding: 9px; color: #a6a7bd; }
.connect-field-hint { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #a1a4b8; line-height: 1.7; margin: 9px 0 0; }
.preset-model { margin-top: 23px; padding: 12px 0; display: flex; gap: 10px; align-items: flex-start; justify-content: space-between; }
.preset-model > span { font-size: 10px; color: #9fa2b4; white-space: nowrap; padding-top: 2px; }
.preset-model > code { font-size: 11px; color: #7d759e; overflow-wrap: anywhere; text-align: right; line-height: 1.6; }
.connect-advanced { border-top: 1px solid #f0f0f6; border-bottom: 1px solid #f0f0f6; }
.connect-advanced summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 9px; padding: 15px 0; color: #7f8299; font-size: 11px; }
.connect-advanced summary::-webkit-details-marker { display: none; }
.connect-advanced summary > span { color: #b6b8c7; font-size: 9px; }
.connect-advanced summary > svg { margin-left: auto; color: #b7b8ca; transition: transform .2s; }
.connect-advanced[open] summary > svg { transform: rotate(180deg); }
.connect-advanced > div { padding: 8px 0 17px; }
.connect-form .connect-checkbox { display: flex; align-items: center; gap: 8px; margin: 18px 0 0; font-size: 11px; color: #8b8da5; }
.connect-checkbox input { accent-color: var(--accent); }
.connect-dialog-footer { display: flex; justify-content: flex-end; gap: 9px; margin-top: 23px; }
.connect-dialog-footer > button { padding: 12px 20px; }
.connect-cancel { border: 1px solid #e9e9f1; border-radius: 11px; background: #fff; color: #989aae; font-size: 12px; }
.connect-cancel:hover { background: #f7f7fc; }
.connect-billing-note { text-align: center; margin: 17px 0 0; color: #b7b8c7; font-size: 9px; }
.dialog-error { margin-top: 15px; margin-bottom: 0; }
.connect-confirm { max-width: 410px; padding: 28px; }
.delete-dialog-icon { display: grid; place-items: center; width: 48px; height: 48px; background: #fdf0f3; border: 1px solid #f9e2e9; border-radius: 15px; color: #cb8298; margin-bottom: 20px; }
.connect-confirm h2 { font-size: 19px; overflow-wrap: anywhere; margin-bottom: 14px; }
.connect-confirm > p:not(.connect-field-hint):not(.connections-notice) { font-size: 12px; line-height: 1.9; color: #9497ab; }
.connect-confirm-delete { border: 0; border-radius: 11px; background: #bd667f; color: white; font-size: 12px; }
.connect-spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 760px) {
  .connections { width: calc(100% - 32px); padding-top: 23px; }
  .connections-heading { align-items: flex-start; margin-top: 25px; }
  .connections-heading h1 { font-size: 26px; }
  .connections-heading h1 span { display: none; }
  .connections-heading > .connect-primary { font-size: 11px; padding: 11px 13px; margin-top: 22px; }
  .connections-description { font-size: 12px; max-width: 215px; line-height: 1.9; }
  .connections-grid { grid-template-columns: 1fr; gap: 18px; }
  .connections-aside { display: flex; gap: 15px; flex-direction: column; }
  .connection-guide { padding: 20px; }
  .connection-guide ol { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .connection-guide li { margin: 0; flex-direction: column; gap: 5px; }
  .connection-guide strong { font-size: 11px; }
  .connection-guide li p { font-size: 10px; }
  .connection-guide .guide-icon { display: none; }
  .connection-guide h2 { margin-top: 0; margin-bottom: 19px; font-size: 13px; }
  .connections-providers { padding-top: 0; }
  .connections-security { padding: 22px 12px 0; justify-content: flex-start; font-size: 10px; }
  .active-connection { padding: 22px 21px 0; border-radius: 18px; }
  .active-identity { gap: 12px; margin-top: 22px; }
  .active-identity h2 { font-size: 20px; }
  .active-identity p { font-size: 11px; }
  .active-symbol { width: 47px; height: 47px; border-radius: 14px; }
  .active-details { grid-template-columns: 1fr; gap: 15px; margin-top: 22px; margin-bottom: 20px; }
  .active-details > div { display: grid; grid-template-columns: 60px minmax(0, 1fr); gap: 10px; align-items: baseline; }
  .active-details span { font-size: 10px; margin: 0; }
  .active-details code { font-size: 11px; }
  .active-footer { gap: 8px; padding: 13px 0; }
  .active-footer span { font-size: 10px; }
  .active-topline > span { font-size: 10px; }
  .connection-row { gap: 11px; padding: 20px 18px; }
  .connection-row .provider-symbol { width: 37px; height: 37px; border-radius: 12px; }
  .connection-row-title h3 { font-size: 12px; }
  .connection-row-actions { gap: 3px; }
  .connect-switch { padding: 6px; font-size: 9px; }
  .connection-model { font-size: 10px; }
  .library-heading { padding: 21px 19px; }
  .library-heading p { font-size: 11px; }
  .connection-welcome { padding: 28px 23px; gap: 10px; flex-direction: column; text-align: center; }
  .welcome-art { width: 100px; height: 95px; }
  .welcome-key { width: 62px; height: 72px; border-radius: 18px; }
  .welcome-key svg { width: 29px; }
  .welcome-spark { width: 26px; height: 26px; top: 0; right: -1px; }
  .welcome-copy h2 { font-size: 23px; }
  .welcome-copy > p { font-size: 11px; }
  .welcome-copy .connect-primary { font-size: 11px; }
  .welcome-skip { font-size: 10px; margin-left: 10px; }
  .connect-overlay { padding: 16px; }
  .connect-dialog { max-height: calc(100dvh - 32px); padding: 24px 21px 18px; border-radius: 20px; }
  .connect-form input:not([type=checkbox]), .connect-form select { font-size: 16px; }
  .provider-preview code { font-size: 8px; }
  .compatible-badge { display: none; }
}
@media (prefers-reduced-motion: reduce) { .connections button { transition: none; } .connect-spinner { animation: none; } }
</style>
