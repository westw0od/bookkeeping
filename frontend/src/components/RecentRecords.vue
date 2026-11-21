<template>
  <section class="recent-panel" aria-label="最近账单">
    <header class="recent-heading"><h2><button class="recent-collapse" type="button" :aria-expanded="!collapsed" :aria-controls="contentId" @click="collapsed = !collapsed">{{ showRemoved ? '已删除' : '最近记录' }}<span class="recent-count" aria-hidden="true">{{ displayed.length }}</span><ChevronDown :size="15" aria-hidden="true" :class="{ collapsed }" /></button></h2><button class="recent-filter" type="button" :disabled="busy || loading" @click="toggleRemoved">{{ showRemoved ? '返回记录' : '已删除' }}<ChevronRight :size="12" /></button></header>
    <div v-show="!collapsed" :id="contentId">
    <p v-if="notice" class="recent-notice" role="status">{{ notice }}<button v-if="lastRemoved" type="button" :disabled="busy" @click="restore(lastRemoved)"><Undo2 :size="13" />撤销删除</button></p>
    <div v-if="error && !pending" class="recent-error" role="alert">{{ error }}<button v-if="showRemoved" :disabled="busy || loading" @click="loadRemoved">重试</button></div>
    <div v-if="loading" class="recent-empty" role="status"><LoaderCircle class="recent-spinner" :size="22" /><p>加载中…</p></div>
    <ul v-else-if="displayed.length" class="recent-records" :class="{ 'removed-list': showRemoved }">
      <li v-for="record in displayed" :key="record.id" :class="{ 'removed-record': showRemoved }">
        <span class="recent-icon" :class="record.type"><ArrowDownLeft v-if="record.type === 'income'" :size="17" /><ArrowUpRight v-else :size="17" /></span>
        <div><button v-if="!showRemoved" class="recent-open" :aria-label="`编辑账单：${entryLabel(record)}`" @click="openEntryEditor(record)"><strong :title="entryLabel(record)">{{ entryLabel(record) }}</strong><small>{{ record.category }} · {{ shortDate(record.createdAt) }}</small></button><template v-else><strong>{{ entryLabel(record) }}</strong><small>{{ record.category }} · {{ shortDate(record.createdAt) }} · 已删除</small></template></div>
        <b :class="record.type === 'income' && !showRemoved ? 'income-text' : ''">{{ record.type === 'income' ? '+' : '−' }}{{ money(record.amount) }}</b>
        <button v-if="showRemoved" class="recent-restore" type="button" :aria-label="`恢复账单：${entryLabel(record)}`" title="恢复账单" :disabled="busy" @click="restore(record)"><RotateCcw :size="15" /></button>
        <button v-else class="recent-delete" type="button" :aria-label="`删除账单：${entryLabel(record)}`" title="删除账单" :disabled="busy" @click="askRemove(record)"><Trash2 :size="15" /></button>
      </li>
    </ul>
    <div v-else-if="!error" class="recent-empty"><ReceiptText :size="31" :stroke-width="1.3" /><strong>{{ showRemoved ? '没有已删除的账单' : '还没有记录' }}</strong><p>{{ showRemoved ? '删除的账单可以在这里恢复。' : '确认记账后，会显示在这里。' }}</p></div>
    </div>

    <div v-if="pending" class="modal-mask" @click.self="closeDialog" @keydown="dialogKeys">
      <section ref="dialog" class="modal-card remove-confirm" role="dialog" aria-modal="true" aria-labelledby="remove-entry-title">
        <span class="remove-confirm-icon"><Trash2 :size="23" :stroke-width="1.7" /></span><h2 id="remove-entry-title">删除这笔账单？</h2>
        <div class="remove-entry-summary"><div><strong>{{ entryLabel(pending) }}</strong><small>{{ pending.category }} · {{ formatDateTime(pending.createdAt) }}</small></div><b>{{ money(pending.amount) }}</b></div>
        <p class="remove-explanation">删除后不再计入收支统计。误删时，可以在“已删除”中恢复。</p>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <div class="modal-actions"><button ref="cancelButton" class="secondary-btn" type="button" :disabled="busy" @click="closeDialog">取消</button><button class="remove-confirm-button" type="button" :disabled="busy" @click="confirmRemove">{{ busy ? '删除中…' : '确认删除' }}</button></div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, useId, watch } from "vue";
import { ArrowDownLeft, ArrowUpRight, ChevronDown, ChevronRight, LoaderCircle, ReceiptText, RotateCcw, Trash2, Undo2 } from "@lucide/vue";
import { formatDateTime, loadRemovedTransactions, removeTransaction, restoreTransaction } from "../services/storage";
import { openEntryEditor } from "../services/editor";
import { currentUser } from "../services/api";
const contentId = useId();
const preferenceKey = `bookkeeping-recent-collapsed:${currentUser.value?.id || 'guest'}`;
let savedCollapsed = false;
try { savedCollapsed = localStorage.getItem(preferenceKey) === 'true'; } catch {}
const collapsed = ref(savedCollapsed);
watch(collapsed, value => { try { localStorage.setItem(preferenceKey, String(value)); } catch {} });
const active = defineModel({ type: Array, default: () => [] });
const emit = defineEmits(["changed"]);
const showRemoved = ref(false), removed = ref([]), loading = ref(false), busy = ref(false);
const pending = ref(null), error = ref(""), notice = ref(""), lastRemoved = ref(null);
const dialog = ref(null), cancelButton = ref(null);
let previousFocus;
const displayed = computed(() => showRemoved.value ? removed.value : [...active.value].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 5));
watch(pending, value => { document.body.style.overflow = value ? "hidden" : ""; });
onUnmounted(() => { document.body.style.overflow = ""; });
function entryLabel(record) { return record.counterparty ? `${record.counterparty} · ${record.event || record.note || record.category}` : record.note || record.category; }
function money(value) { return `¥${Number(value || 0).toFixed(2)}`; }
function shortDate(value) { return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(new Date(value)); }
async function loadRemoved() {
  loading.value = true; error.value = "";
  try { removed.value = await loadRemovedTransactions(); }
  catch (err) { error.value = err.message; }
  finally { loading.value = false; }
}
async function toggleRemoved() {
  if (busy.value || loading.value) return;
  showRemoved.value = !showRemoved.value;
  collapsed.value = false;
  error.value = "";
  if (showRemoved.value) await loadRemoved();
}
async function askRemove(record) {
  if (busy.value) return;
  previousFocus = document.activeElement;
  pending.value = record; error.value = "";
  await nextTick(); cancelButton.value?.focus();
}
function closeDialog() {
  if (busy.value) return;
  pending.value = null; error.value = "";
  previousFocus?.focus();
}
function dialogKeys(event) {
  if (event.key === "Escape") { event.preventDefault(); closeDialog(); }
  if (event.key !== "Tab") return;
  const nodes = [...dialog.value.querySelectorAll("button:not(:disabled)")];
  const first = nodes[0], last = nodes.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
}
async function confirmRemove() {
  if (busy.value || !pending.value) return;
  busy.value = true; error.value = "";
  try {
    const record = await removeTransaction(pending.value.id);
    active.value = active.value.filter(row => row.id !== record.id);
    removed.value = [record, ...removed.value.filter(row => row.id !== record.id)];
    lastRemoved.value = record;
    notice.value = "账单已删除";
    pending.value = null;
    emit("changed");
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
async function restore(record) {
  if (busy.value) return;
  busy.value = true; error.value = "";
  try {
    const restored = await restoreTransaction(record.id);
    active.value = [restored, ...active.value.filter(row => row.id !== restored.id)];
    removed.value = removed.value.filter(row => row.id !== restored.id);
    if (lastRemoved.value?.id === restored.id) lastRemoved.value = null;
    notice.value = "账单已恢复，已重新计入收支";
    emit("changed");
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
</script>

<style scoped>
.recent-filter { display: inline-flex; align-items: center; gap: 2px; padding: 5px 0; border: 0; background: transparent; color: #9999a3; font-size: 11px; }
.recent-filter:hover { color: var(--blue); }
.recent-collapse { display: flex; align-items: center; gap: 7px; background: none; border: 0; padding: 5px 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.recent-collapse > svg { color: #858592; transition: transform .18s ease; }
.recent-collapse > svg.collapsed { transform: rotate(-90deg); }
.recent-count { color: #777783; background: #f1f1f5; border-radius: 6px; font-size: 10px; font-weight: 400; padding: 2px 5px; }
.recent-open { border: 0; padding: 2px 0; background: none; text-align: left; width: 100%; }
.recent-open:hover strong { color: var(--blue); }
.recent-records { padding: 0 18px; }
.recent-records li { gap: 7px; }
.recent-records b { font-size: 11px; }
.recent-records .recent-icon { width: 28px; height: 28px; }
.recent-delete, .recent-restore { display: grid; place-items: center; min-width: 28px; min-height: 32px; padding: 6px 3px; border: 0; border-radius: 7px; background: transparent; color: #b0b0b9; }
.recent-delete:hover { color: #c46665; background: #fff3f1; }
.recent-restore { color: #849e85; }
.recent-restore:hover { color: #3a845c; background: #f0f7f2; }
.removed-list { max-height: 410px; overflow-y: auto; }
.removed-record .recent-icon { opacity: .5; }
.removed-record b { color: #a4a4ad; }
.recent-notice { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 5px 10px; padding: 11px 15px; margin: 0 13px 10px; border-radius: 9px; background: #f1f6f1; color: #66836c; font-size: 11px; line-height: 1.7; }
.recent-notice button { display: inline-flex; align-items: center; gap: 4px; border: 0; padding: 2px 0; background: none; color: #35754c; font-size: 11px; }
.recent-error { padding: 11px 15px; margin: 0 13px 10px; border-radius: 9px; background: #fff2f2; color: #b36262; font-size: 11px; line-height: 1.7; }
.recent-error button { background: none; border: 0; color: inherit; text-decoration: underline; }
.remove-confirm { text-align: left; }
.remove-confirm-icon { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px; background: #fff0ee; color: #ca8076; margin-bottom: 22px; }
.remove-confirm h2 { font-size: 21px; }
.remove-entry-summary { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 16px; margin-top: 20px; border-radius: 11px; background: #f7f7fa; }
.remove-entry-summary > div { min-width: 0; }
.remove-entry-summary strong { font-size: 14px; font-weight: 500; display: block; overflow-wrap: anywhere; }
.remove-entry-summary small { display: block; margin-top: 7px; color: #a0a0aa; font-size: 11px; }
.remove-entry-summary b { color: #6e6e78; font-size: 17px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.remove-explanation { font-size: 12px; line-height: 1.9; color: #95959f; margin: 18px 0 0; }
.remove-confirm-button { display: inline-flex; align-items: center; justify-content: center; min-height: 40px; border-radius: 20px; border: 0; padding: 0 18px; background: #bd6864; color: white; font-size: 13px; font-weight: 500; }
.remove-confirm-button:hover:not(:disabled) { background: #b75b58; }
.recent-spinner { animation: recent-spin 1s linear infinite; }
@keyframes recent-spin { to { transform: rotate(360deg); } }
</style>
