<template>
  <section class="draft-review" :class="{ 'has-draft': visible }" aria-label="AI 识别结果" :aria-busy="analyzing">
    <div v-if="analyzing" class="draft-placeholder" role="status"><LoaderCircle class="draft-spinner" :size="22" /><div><strong>正在整理这次输入…</strong><p>AI 会提取收支、金额和分类，完成后在这里确认。</p></div></div>
    <template v-else-if="visible">
      <header class="draft-heading"><div><p class="draft-eyebrow">AI 识别结果</p><h2>待确认的账单 <span>{{ draft.length }} 笔</span></h2><p>核对金额、分类和备注，确认后才会记入账本。</p></div><span class="draft-badge"><Clock3 :size="13" /> 尚未入账</span></header>
      <form v-if="draft.length" @submit.prevent="$emit('confirm')">
        <fieldset :disabled="saving">
          <article v-for="(record, index) in draft" :key="record.id" class="draft-entry">
            <div class="draft-entry-head"><span>账单 {{ index + 1 }}</span><small>{{ formatDateTime(record.createdAt) }}</small></div>
            <div class="draft-fields">
              <label>收支<select v-model="record.type" @change="resetCategory(record)"><option value="expense">支出</option><option value="income">收入</option></select></label>
              <label>分类<select v-model="record.category"><option v-for="category in categories(record.type)" :key="category">{{ category }}</option></select></label>
              <label>金额（元）<input v-model.number="record.amount" type="number" min="0.01" max="9999999999.99" step="0.01" required inputmode="decimal" /></label>
              <label class="draft-note">备注<input v-model.trim="record.note" maxlength="2000" placeholder="可补充这笔账的说明" /></label>
              <label class="draft-date">记账时间<input :value="datetimeLocalValue(new Date(record.createdAt))" type="datetime-local" required @change="setDate(record, $event.target.value)" /></label>
              <label v-if="record.category === '人情'">往来人<input v-model.trim="record.counterparty" maxlength="80" placeholder="例如：张三" /></label>
              <label v-if="record.category === '人情'">事由<input v-model.trim="record.event" maxlength="120" placeholder="例如：婚礼" /></label>
            </div>
          </article>
        </fieldset>
        <div class="draft-totals"><span>本次识别</span><span>收入 <b class="income-text">{{ money(income) }}</b></span><span>支出 <b class="expense-text">{{ money(expense) }}</b></span></div>
        <p v-if="advice" class="draft-advice"><Sparkles :size="15" /><span>{{ advice }}</span></p>
        <p v-if="error" class="draft-error" role="alert">{{ error }}</p>
        <footer class="draft-actions"><span><ShieldCheck :size="14" /> 确认后才入账</span><div><button type="button" class="secondary-btn" :disabled="saving" @click="$emit('discard')">取消</button><button class="primary-btn" :disabled="saving"><LoaderCircle v-if="saving" class="draft-spinner" :size="16" /><Check v-else :size="16" />{{ saving ? '保存中…' : '确认记账' }}</button></div></footer>
      </form>
      <div v-else class="draft-empty"><p>{{ advice || '这次输入中没有识别到明确的收支和金额，可以补充金额后再分析。' }}</p><button type="button" class="secondary-btn" @click="$emit('discard')">重新输入</button></div>
    </template>
    <div v-else class="draft-placeholder"><ListChecks :size="23" /><div><strong>分析结果会显示在这里</strong><p>核对后，再确认记账。</p></div></div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Check, Clock3, ListChecks, LoaderCircle, ShieldCheck, Sparkles } from "@lucide/vue";
import { expenseCategories, incomeCategories, formatDateTime, datetimeLocalValue, totalAmount } from "../services/storage";
const draft = defineModel({ type: Array, default: () => [] });
defineProps({ visible: Boolean, analyzing: Boolean, saving: Boolean, advice: { type: String, default: "" }, error: { type: String, default: "" } });
defineEmits(["confirm", "discard"]);
const income = computed(() => totalAmount(draft.value.filter(record => record.type === "income")));
const expense = computed(() => totalAmount(draft.value.filter(record => record.type === "expense")));
function categories(type) { return type === "income" ? incomeCategories : expenseCategories; }
function resetCategory(record) { if (!categories(record.type).includes(record.category)) record.category = categories(record.type)[0]; }
function setDate(record, value) { const date = new Date(value); if (Number.isFinite(date.getTime())) record.createdAt = date.toISOString(); }
function money(value) { return `¥${Number(value || 0).toFixed(2)}`; }
</script>

<style scoped>
.draft-review { margin-top: 20px; border: 0; border-top: 1px solid #eeeef2; border-radius: 0; background: transparent; overflow: hidden; }
.draft-review.has-draft { border: 1px solid #e7e7ed; border-radius: 15px; background: #fcfcfd; }
.draft-placeholder { display: flex; align-items: center; gap: 14px; padding: 20px 0 0; color: #a3a3ad; }
.draft-placeholder > svg { flex-shrink: 0; color: #b1b1bc; }
.draft-placeholder strong { color: #9696a0; font-size: 13px; font-weight: 500; }
.draft-placeholder p { margin: 6px 0 0; color: #a6a6af; font-size: 12px; line-height: 1.7; }
.draft-heading { display: flex; justify-content: space-between; gap: 15px; padding: 22px 24px 0; }
.draft-eyebrow { color: #a0a0aa; font-size: 10px; letter-spacing: 1px; margin: 0 0 7px; }
.draft-heading h2 { display: flex; align-items: center; gap: 9px; font-size: 17px; margin: 0; color: #393940; }
.draft-heading h2 span { color: #9a9aa5; font-size: 11px; font-weight: 400; background: #f0f0f4; padding: 4px 7px; border-radius: 6px; white-space: nowrap; }
.draft-heading > div > p:last-child { color: #95959f; font-size: 12px; margin: 10px 0 0; line-height: 1.7; }
.draft-badge { display: inline-flex; align-items: center; align-self: flex-start; gap: 5px; color: #9b8347; background: #f7f1e3; font-size: 11px; border-radius: 20px; padding: 6px 9px; white-space: nowrap; }
.draft-review form { padding: 0 24px; }
.draft-review fieldset { padding: 0; border: 0; margin: 0; min-width: 0; }
.draft-entry { border: 1px solid #eaeaf0; background: #fff; border-radius: 12px; padding: 17px; margin-top: 17px; }
.draft-entry-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; gap: 10px; }
.draft-entry-head > span { color: #9696a0; font-size: 11px; }
.draft-entry-head small { font-size: 11px; color: #aaaab3; }
.draft-fields { display: grid; grid-template-columns: 85px 110px 140px minmax(0, 1fr); gap: 12px; }
.draft-fields label { display: flex; flex-direction: column; gap: 8px; font-size: 12px; color: #62626e; min-width: 0; }
.draft-fields .draft-date { grid-column: span 2; }
.draft-fields input, .draft-fields select { margin: 0; padding: 10px; border-radius: 9px; background: #fcfcfd; color: #4b4b56; border: 1px solid #e1e1e8; font-size: 14px; width: 100%; }
.draft-totals { display: flex; justify-content: flex-end; align-items: center; flex-wrap: wrap; gap: 20px; font-size: 12px; padding: 16px 2px; color: #9aa3b8; }
.draft-totals > span:first-child { margin-right: auto; color: #a0a9bd; font-size: 11px; }
.draft-totals b { margin-left: 5px; font-size: 14px; }
.draft-advice { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.9; color: #85858f; padding: 12px 15px; margin: 0 0 18px; background: #f2f2f6; border-radius: 10px; }
.draft-advice svg { flex-shrink: 0; margin-top: 3px; color: #9797a7; }
.draft-actions { display: flex; align-items: center; justify-content: space-between; gap: 15px; border-top: 1px solid #ebebf0; padding: 18px 0; }
.draft-actions > span { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #a6a6af; }
.draft-actions > div { display: flex; gap: 9px; }
.draft-actions button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; font-size: 13px; font-weight: 600; border-radius: 20px; }
.draft-actions .secondary-btn { color: #8d8d99; background: #ededf2; }
.draft-error { color: #b55f72; font-size: 12px; padding: 11px 14px; background: #fff1f3; border-radius: 9px; line-height: 1.7; }
.draft-empty { padding: 18px 24px 24px; color: #929bb0; font-size: 13px; line-height: 1.8; }
.draft-spinner { animation: draft-spin 1s linear infinite; }
@keyframes draft-spin { to { transform: rotate(360deg); } }
@media (max-width: 1050px) {
  .draft-heading { padding: 18px 16px 0; gap: 8px; }
  .draft-heading h2 { font-size: 17px; }
  .draft-heading > div > p:last-child { font-size: 11px; }
  .draft-badge { font-size: 10px; padding: 5px 7px; gap: 3px; }
  .draft-review form { padding: 0 15px; }
  .draft-entry { padding: 13px; }
  .draft-fields { grid-template-columns: 1fr 1fr; gap: 12px 10px; }
  .draft-note { grid-column: 1 / -1; }
  .draft-fields input, .draft-fields select { font-size: 16px; padding: 9px; }
  .draft-entry-head { align-items: flex-start; flex-direction: column; gap: 5px; }
  .draft-totals { gap: 8px 12px; }
  .draft-totals > span:first-child { flex-basis: 100%; }
  .draft-actions { flex-wrap: wrap; }
  .draft-actions > div { margin-left: auto; }
  .draft-placeholder { padding: 18px 0 0; gap: 10px; }
}
@media (prefers-reduced-motion: reduce) { .draft-spinner { animation: none; } }
</style>
