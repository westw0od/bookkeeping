<template>
  <main class="app-shell transactions-page">
    <header class="workspace-heading"><div><p class="eyebrow">每一笔，都清楚</p><h1>我的账单</h1><p class="page-description">查找收支、补充信息，或继续一笔未完成的记录。</p></div><button class="primary-btn" @click="openEntryEditor()"><Plus :size="16" />记一笔</button></header>
    <section class="panel transaction-period"><PeriodSelector v-model:mode="periodMode" v-model:day="day" v-model:month="month" /></section>
    <section class="transaction-toolbar panel" aria-label="筛选账单"><div class="search-field"><Search :size="17" /><input v-model="search" aria-label="搜索账单" placeholder="搜索备注、分类或往来人" /></div><select v-model="type" aria-label="收支筛选"><option value="all">全部收支</option><option value="expense">支出</option><option value="income">收入</option></select></section>
    <div class="classification-grid" :class="{ single: type !== 'all' }"><CategoryBreakdown v-if="type !== 'income'" :records="periodRecords" type="expense" :period-label="periodLabel" :selected="selected?.type === 'expense' ? selected.category : ''" @select="selectCategory" /><CategoryBreakdown v-if="type !== 'expense'" :records="periodRecords" type="income" :period-label="periodLabel" :selected="selected?.type === 'income' ? selected.category : ''" @select="selectCategory" /></div>
    <section class="transaction-ledger panel" aria-label="全部账单"><header class="section-head"><div><h2>{{ periodLabel }}{{ selected ? ` · ${selected.category}${selected.type === 'income' ? '收入' : '支出'}` : '' }}<span class="count-label">{{ filtered.length }} 笔</span></h2><p class="page-description">收入 {{ money(income) }}<span class="summary-separator">·</span>支出 {{ money(expense) }}</p></div><button v-if="selected" class="text-button" @click="selected = null">显示全部分类</button></header>
      <ul class="transaction-list"><li v-for="record in filtered" :key="record.id"><button class="transaction-open" :aria-label="`编辑账单：${record.note || record.category}`" @click="openEntryEditor(record)"><span class="transaction-symbol" :class="record.type"><ArrowDownLeft v-if="record.type === 'income'" :size="19" /><ArrowUpRight v-else :size="19" /></span><span class="transaction-text"><strong>{{ record.counterparty ? `${record.counterparty} · ${record.event || record.category}` : record.note || record.category }}</strong><small>{{ record.category }} · {{ formatDateTime(record.createdAt) }}</small></span><b :class="record.type === 'income' ? 'income-text' : ''">{{ record.type === 'income' ? '+' : '−' }}{{ money(record.amount) }}</b><ChevronRight :size="16" /></button></li></ul>
      <p v-if="!filtered.length" class="empty-copy">{{ loading ? '正在加载账单…' : '这个范围还没有账单，试试更换筛选条件。' }}</p>
    </section>
    <ImportLedger @imported="load" />
  </main>
</template>
<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ArrowDownLeft, ArrowUpRight, ChevronRight, Plus, Search } from "@lucide/vue";
import { dateInputValue, formatDateTime, inPeriod, loadTransactionsFromStore, totalAmount } from "../services/storage";
import { ledgerRevision, openEntryEditor } from "../services/editor";
import ImportLedger from "../components/ImportLedger.vue";
import CategoryBreakdown from "../components/CategoryBreakdown.vue";
import PeriodSelector from "../components/PeriodSelector.vue";
const route = useRoute(), today = dateInputValue(new Date());
const records = ref([]), search = ref(''), type = ref('all'), month = ref(today.slice(0, 7)), day = ref(today), periodMode = ref('month'), loading = ref(true), selected = ref(null);
const periodRecords = computed(() => records.value.filter(r => !r.revokedAt && (type.value === 'all' || r.type === type.value) && inPeriod(r, periodMode.value, day.value, month.value) && [r.note, r.category, r.counterparty, r.event].join(' ').toLowerCase().includes(search.value.trim().toLowerCase())));
const filtered = computed(() => periodRecords.value.filter(r => !selected.value || (r.type === selected.value.type && r.category === selected.value.category)).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)));
const periodLabel = computed(() => periodMode.value === 'all' ? '全部记录' : periodMode.value === 'day' ? day.value === today ? '今日' : day.value : month.value === today.slice(0, 7) ? '本月' : `${month.value.replace('-', '年')}月`);
watch([periodMode, day, month, type, search], () => { selected.value = null; }, { flush: 'sync' });
watch(() => route.query, query => {
  periodMode.value = ['day', 'month', 'all'].includes(query.period) ? query.period : 'month';
  day.value = /^\d{4}-\d{2}-\d{2}$/.test(query.day || '') ? query.day : today;
  month.value = /^\d{4}-\d{2}$/.test(query.month || '') ? query.month : today.slice(0, 7);
  type.value = ['income', 'expense'].includes(query.type) ? query.type : 'all';
  selected.value = query.category && type.value !== 'all' ? { type: type.value, category: String(query.category) } : null;
}, { immediate: true });
function selectCategory(value) { selected.value = selected.value?.type === value.type && selected.value?.category === value.category ? null : value; }
const income = computed(() => totalAmount(filtered.value.filter(r => r.type === 'income'))), expense = computed(() => totalAmount(filtered.value.filter(r => r.type === 'expense')));
onMounted(load); watch(ledgerRevision, load);
async function load() { records.value = await loadTransactionsFromStore(); loading.value = false; }
function money(value) { return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value); }
</script>
