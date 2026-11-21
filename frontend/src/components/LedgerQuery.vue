<template>
  <section class="query-panel" aria-label="账本查询">
    <div class="section-head"><h2>查询账本</h2><span class="query-agent-badge"><Sparkles :size="12" />AI 查询</span></div>
    <form class="query-row" @submit.prevent="ask"><input v-model.trim="question" :disabled="busy" maxlength="1000" placeholder="我和张三有过哪些人情往来？" aria-label="查询账本问题" /><button class="primary-btn" aria-label="查询账本" :disabled="busy || !enabled || !question"><LoaderCircle v-if="busy" class="query-spin" :size="16" /><Search v-else :size="16" /><span>{{ busy ? '查询中' : '查询' }}</span></button></form>
    <p v-if="!enabled" class="query-helper">连接默认 API Key 后，可以直接询问账本中的收支与人情往来。</p>
    <p v-if="busy" class="query-helper" role="status">正在理解问题、查询账本并整理结果…</p>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    <div v-if="answer" class="ledger-answer">
      <p class="query-answer-text">{{ answer.summary }}</p>
      <details class="query-steps"><summary><ListChecks :size="14" />执行过程 · {{ answer.query_count }} 轮查询<ChevronDown :size="13" /></summary><ol><li v-for="(step, index) in answer.steps" :key="index"><span>{{ index + 1 }}</span><div><strong>{{ step.label }}</strong><small>{{ step.status === 'error' ? '查询条件需要修正' : `找到 ${step.matched_count} 笔记录` }}</small></div></li></ol></details>
      <p class="query-scope">{{ answer.query_count > 1 ? '最后一轮查询' : '本次查询' }}匹配 {{ answer.matched_count }} 笔账单</p>
      <div class="report-metrics query-metrics"><div><span>收入</span><strong class="income-text">{{ money(answer.income) }}</strong></div><div><span>支出</span><strong class="expense-text">{{ money(answer.expense) }}</strong></div><div><span>结余</span><strong :class="answer.balance >= 0 ? 'income-text' : 'expense-text'">{{ money(answer.balance) }}</strong></div></div>
      <ul class="record-list compact-list"><li v-for="record in answer.records" :key="record.id"><span>{{ record.counterparty || record.category }}{{ record.event ? ` · ${record.event}` : '' }}</span><b :class="record.type === 'income' ? 'income-text' : 'expense-text'">{{ record.type === 'income' ? '+' : '−' }}{{ money(record.amount) }}</b><small>{{ formatDateTime(record.createdAt) }}{{ record.note ? ` · ${record.note}` : '' }}</small></li><li v-if="!answer.records.length" class="empty-item">当前账本未找到匹配记录</li></ul>
      <p v-if="answer.truncated" class="query-helper">仅展示最近 {{ answer.records.length }} 笔明细，以上汇总包含全部 {{ answer.matched_count }} 笔。</p>
      <p v-if="answer.limit_reached" class="query-helper">已完成本次最多 3 轮查询，可补充姓名或日期后重新提问。</p>
    </div>
  </section>
</template>

<script setup>
import { onUnmounted, ref, watch } from "vue";
import { ChevronDown, ListChecks, LoaderCircle, Search, Sparkles } from "@lucide/vue";
import { api } from "../services/api";
import { formatDateTime } from "../services/storage";
const props = defineProps({ enabled: Boolean, ledgerVersion: { type: String, default: "" } });
const answer = defineModel({ default: null });
const question = ref(""), busy = ref(false), error = ref("");
let generation = 0, controller;
function invalidate() { generation++; controller?.abort(); busy.value = false; error.value = ""; answer.value = null; }
watch(() => props.ledgerVersion, invalidate);
onUnmounted(invalidate);
function money(value) { return `¥${Number(value || 0).toFixed(2)}`; }
async function ask() {
  if (busy.value || !question.value || !props.enabled) return;
  const current = ++generation;
  const currentController = new AbortController();
  controller = currentController;
  const timeout = setTimeout(() => currentController.abort(), 70000);
  busy.value = true; error.value = ""; answer.value = null;
  try {
    const result = await api("/api/agent/query", { method: "POST", body: { question: question.value }, signal: currentController.signal });
    if (current === generation) answer.value = result;
  } catch (err) { if (current === generation) error.value = err.message; }
  finally { clearTimeout(timeout); if (current === generation) busy.value = false; }
}
</script>

<style scoped>
.query-agent-badge { display: inline-flex; align-items: center; gap: 4px; color: #a0a0ac; font-size: 10px; }
.query-helper, .query-scope { font-size: 11px; color: #a2a2af; line-height: 1.8; margin: 14px 0 0; }
.query-answer-text { font-size: 14px; line-height: 1.95; color: #6f6f7c; white-space: pre-wrap; margin: 0 0 18px; }
.query-steps { border: 1px solid #eaeaf0; border-radius: 11px; padding: 0 14px; background: #fcfcfe; }
.query-steps summary { list-style: none; display: flex; align-items: center; gap: 6px; padding: 12px 0; font-size: 11px; color: #9999a8; cursor: pointer; }
.query-steps summary::-webkit-details-marker { display: none; }
.query-steps summary > svg:last-child { margin-left: auto; }
.query-steps ol { list-style: none; padding: 0; margin: 0 0 13px; }
.query-steps li { display: flex; gap: 10px; padding: 10px 0; border-top: 1px solid #f0f0f5; }
.query-steps li > span { display: grid; place-items: center; width: 20px; height: 20px; border-radius: 6px; background: #f0f0f7; color: #aeaec0; font-size: 10px; flex-shrink: 0; }
.query-steps strong { font-size: 11px; font-weight: 400; color: #898997; }
.query-steps small { display: block; margin-top: 5px; font-size: 10px; color: #adadbc; }
.query-metrics { margin-top: 13px; }
.query-metrics strong { font-size: 20px; }
.query-spin { animation: query-spin 1s linear infinite; }
@keyframes query-spin { to { transform: rotate(360deg); } }
</style>
