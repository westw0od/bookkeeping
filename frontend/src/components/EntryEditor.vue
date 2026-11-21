<template>
  <Teleport to="body">
    <div class="modal-mask" @click.self="close" @keydown="keys">
      <section ref="dialog" class="modal-card entry-editor" role="dialog" aria-modal="true" aria-labelledby="editor-title">
        <header class="editor-heading"><div><p class="eyebrow">{{ original ? '账单详情' : '新的记录' }}</p><h2 id="editor-title">{{ original ? '编辑账单' : '记一笔' }}</h2></div><button class="icon-button" aria-label="关闭账单编辑" :disabled="busy" @click="close"><X :size="20" /></button></header>
        <p v-if="restored" class="draft-recovered" role="status">已恢复上次未提交的编辑。</p>
        <form @submit.prevent="submit">
          <fieldset :disabled="busy" class="editor-fields">
            <label>收支类型<select v-model="form.type" @change="ensureCategory"><option value="expense">支出</option><option value="income">收入</option></select></label>
            <label>分类<select v-model="form.category"><option v-for="name in categories" :key="name">{{ name }}</option></select></label>
            <label class="editor-wide">金额<input ref="amountInput" v-model="form.amount" type="number" min="0.01" max="9999999999.99" step="0.01" inputmode="decimal" required /></label>
            <label class="editor-wide">记账时间<input v-model="form.localTime" type="datetime-local" step="1" required /></label>
            <label v-if="form.category === '人情'">往来人<input v-model="form.counterparty" maxlength="80" placeholder="例如：张三" /></label>
            <label v-if="form.category === '人情'">事由<input v-model="form.event" maxlength="120" placeholder="例如：婚礼、生日" /></label>
            <label class="editor-wide">备注<textarea v-model="form.note" maxlength="2000" rows="2" placeholder="补充这笔账的说明"></textarea></label>
          </fieldset>
          <p v-if="error" class="error-text" role="alert">{{ error }}</p>
          <p v-if="draftError" class="error-text" role="alert">{{ draftError }}</p>
          <p v-else class="editor-draft-status"><Check :size="13" />草稿自动保存在此设备，提交后才更新账本</p>
          <footer class="editor-footer"><button type="button" class="text-button" :disabled="busy" @click="discard">放弃草稿</button><div><button type="button" class="secondary-btn" :disabled="busy" @click="close">保存草稿并关闭</button><button class="primary-btn" :disabled="busy">{{ busy ? '保存中…' : original ? '保存修改' : '确认' }}</button></div></footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { Check, X } from "@lucide/vue";
import { api, currentUser } from "../services/api";
import { deleteDraft, draftError, readDraft, saveDraft } from "../services/drafts";
import { editorRequest, ledgerRevision } from "../services/editor";
import { createTransaction, datetimeLocalValue, expenseCategories, incomeCategories } from "../services/storage";
const props = defineProps({ request: { type: Object, required: true } });
const owner = currentUser.value.id;
const slot = props.request.record ? `edit-${props.request.record.id}` : "new-entry";
const previous = readDraft(slot)?.data;
const original = previous?.original || props.request.record;
const source = original || { type: "expense", category: "饮食", amount: "", note: "", counterparty: "", event: "", createdAt: new Date().toISOString(), ...props.request.defaults };
const form = ref(previous?.form || { ...source, localTime: datetimeLocalValue(new Date(source.createdAt)) + `:${String(new Date(source.createdAt).getSeconds()).padStart(2, '0')}` });
const restored = ref(Boolean(previous)), error = ref(""), busy = ref(false), amountInput = ref(null), dialog = ref(null);
const previousFocus = document.activeElement;
let finished = false;
const categories = computed(() => [...new Set([...(form.value.type === "income" ? incomeCategories : expenseCategories), form.value.category].filter(Boolean))]);
watch(form, () => {
  if (!finished) saveDraft(slot, { original, form: form.value }, { kind: original ? "edit" : "create", title: `${original ? '编辑' : '新增'} · ${form.value.counterparty || form.value.note || form.value.category}`, path: "" }, owner);
}, { deep: true, flush: "sync", immediate: true });
onMounted(async () => { document.body.style.overflow = "hidden"; await nextTick(); amountInput.value?.focus(); });
onUnmounted(() => { document.body.style.overflow = ""; previousFocus?.focus(); });
function ensureCategory() {
  const names = form.value.type === "income" ? incomeCategories : expenseCategories;
  if (!names.includes(form.value.category)) form.value.category = names[0];
}
function close() { if (!busy.value) editorRequest.value = null; }
function discard() { if (busy.value) return; finished = true; deleteDraft(slot, owner); close(); }
function keys(event) {
  if (event.key === "Escape") { event.preventDefault(); close(); }
  if (event.key !== "Tab") return;
  const nodes = [...dialog.value.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)')];
  if (event.shiftKey && document.activeElement === nodes[0]) { event.preventDefault(); nodes.at(-1)?.focus(); }
  else if (!event.shiftKey && document.activeElement === nodes.at(-1)) { event.preventDefault(); nodes[0]?.focus(); }
}
async function submit() {
  if (busy.value) return;
  error.value = "";
  const date = new Date(form.value.localTime);
  if (!Number.isFinite(date.getTime())) { error.value = "请选择有效的记账时间"; return; }
  const changes = { type: form.value.type, category: form.value.category, amount: form.value.amount, note: form.value.note || "", counterparty: (form.value.counterparty || "").trim(), event: (form.value.event || "").trim(), createdAt: date.toISOString() };
  busy.value = true;
  try {
    if (original) await api(`/api/ledger/${encodeURIComponent(original.id)}`, { method: "PUT", body: { original, changes } });
    else {
      // Persist the client id before sending: retrying an interrupted save is idempotent.
      if (!form.value.clientId) form.value.clientId = createTransaction(changes).id;
      await api("/api/ledger", { method: "POST", body: [{ ...changes, id: form.value.clientId }] });
    }
    finished = true; deleteDraft(slot, owner); ledgerRevision.value++;
    editorRequest.value = null;
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
</script>
<style scoped>
.entry-editor { width: min(540px, 100%); }
.editor-heading { display: flex; justify-content: space-between; gap: 16px; }
.editor-heading h2 { color: var(--ink); margin: 0; }
.editor-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0; margin: 23px 0 0; border: 0; min-width: 0; }
.editor-fields label { margin: 0; color: #545461; min-width: 0; }
.editor-fields input, .editor-fields select, .editor-fields textarea { width: 100%; margin: 0; color: var(--ink); }
.editor-wide { grid-column: 1 / -1; }
.editor-draft-status { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #667568; margin-top: 20px; line-height: 1.7; }
.editor-footer { border-top: 1px solid var(--line); padding-top: 18px; margin-top: 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.editor-footer > div { display: flex; gap: 8px; }
.editor-footer button { font-size: 12px; }
@media (max-width: 480px) { .editor-footer { flex-wrap: wrap; } .editor-footer > div { width: 100%; justify-content: flex-end; } }
</style>
