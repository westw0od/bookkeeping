<template>
  <main class="app-shell people-page">
    <header class="workspace-heading"><div><p class="eyebrow">每一次心意，都有记录</p><h1>人情往来</h1><p class="page-description">按人查看送出与收到的礼金，回顾每次相聚的事由。</p></div><button class="primary-btn" @click="addGift"><Plus :size="16" />记一笔人情</button></header>
    <section class="people-stats" aria-label="人情汇总"><article><span>往来人数</span><strong>{{ namedPeople.length }}<small> 人</small></strong></article><article><span>累计送出</span><strong>{{ money(totalExpense) }}</strong></article><article><span>累计收到</span><strong>{{ money(totalIncome) }}</strong></article></section>
    <p v-if="loading" class="empty-copy" role="status">正在加载往来记录…</p>
    <div v-else class="people-workspace">
      <aside class="people-directory panel"><div class="section-head"><h2>往来人</h2><span class="count-label">{{ groups.length }}</span></div><div class="search-field"><Search :size="16" /><input v-model="search" aria-label="搜索往来人" placeholder="搜索姓名" /></div>
        <div class="people-list"><button v-for="person in visiblePeople" :key="person.name" :class="{ active: selectedName === person.name }" @click="selectedName = person.name"><span class="person-avatar">{{ person.name ? person.name.slice(0, 1) : '?' }}</span><span><strong>{{ person.name || '未填写往来人' }}</strong><small>{{ person.records.length }} 笔往来 · {{ shortDate(person.latest) }}</small></span><ChevronRight :size="15" /></button><p v-if="!visiblePeople.length" class="empty-copy">{{ search ? '没有匹配的姓名' : '还没有人情往来记录' }}</p></div>
      </aside>
      <section v-if="selectedPerson" class="person-detail panel" aria-label="往来详情">
        <header class="person-heading"><div><p class="eyebrow">{{ selectedPerson.name ? '往来档案' : '待补充信息' }}</p><h2>{{ selectedPerson.name || '未填写往来人' }}</h2><p class="page-description">{{ selectedPerson.records.length }} 笔记录{{ selectedPerson.name ? '' : '，点击编辑补上姓名后，会自动归入对应往来人。' }}</p></div><button v-if="selectedPerson.name" class="secondary-btn" @click="addGift">再记一笔</button></header>
        <div class="person-totals"><div><span>送出</span><strong>{{ money(selectedPerson.expense) }}</strong></div><div><span>收到</span><strong>{{ money(selectedPerson.income) }}</strong></div><div><span>收送差额</span><strong>{{ money(selectedPerson.income - selectedPerson.expense) }}</strong></div></div>
        <p class="gift-explanation">收送差额仅反映礼金往来，不代表欠款或应还金额。</p>
        <div class="section-head timeline-heading"><h3>往来时间线</h3><select v-model="direction" aria-label="筛选往来方向"><option value="all">全部往来</option><option value="expense">送出</option><option value="income">收到</option></select></div>
        <ol class="gift-timeline"><li v-for="record in selectedRecords" :key="record.id"><span class="timeline-dot"><Gift :size="16" /></span><div class="timeline-content"><div><strong>{{ record.event || record.note || '人情往来' }}</strong><b :class="record.type === 'income' ? 'income-text' : ''">{{ record.type === 'income' ? '+' : '−' }}{{ money(record.amount) }}</b></div><small>{{ record.type === 'income' ? '收到礼金' : '送出礼金' }} · {{ formatDateTime(record.createdAt) }}</small><p v-if="record.note && record.note !== record.event">{{ record.note }}</p><button class="text-button" :aria-label="`编辑往来：${record.event || record.note || '人情往来'}`" @click="openEntryEditor(record)"><Pencil :size="12" />编辑记录</button></div></li></ol>
        <p v-if="!selectedRecords.length" class="empty-copy">这个方向还没有往来记录。</p>
      </section>
      <section v-else class="panel people-empty"><Gift :size="40" :stroke-width="1.3" /><h2>从第一笔心意开始</h2><p>记录随礼、生日红包或收到的礼金，<br />以后按姓名就能找到。</p><button class="secondary-btn" @click="addGift">添加往来记录</button></section>
    </div>
  </main>
</template>
<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ChevronRight, Gift, Pencil, Plus, Search } from "@lucide/vue";
import { loadTransactionsFromStore, formatDateTime } from "../services/storage";
import { ledgerRevision, openEntryEditor } from "../services/editor";
const records = ref([]), loading = ref(true), search = ref(""), selectedName = ref(null), direction = ref("all");
const gifts = computed(() => records.value.filter(row => row.category === "人情"));
const cents = row => Math.round(Number(row.amount) * 100);
const totalExpense = computed(() => gifts.value.filter(r => r.type === "expense").reduce((sum, row) => sum + cents(row), 0) / 100);
const totalIncome = computed(() => gifts.value.filter(r => r.type === "income").reduce((sum, row) => sum + cents(row), 0) / 100);
const groups = computed(() => {
  const map = new Map();
  for (const record of gifts.value) {
    const name = (record.counterparty || "").trim();
    if (!map.has(name)) map.set(name, { name, records: [], expenseCents: 0, incomeCents: 0, latest: record.createdAt });
    const group = map.get(name); group.records.push(record); group[record.type === "income" ? "incomeCents" : "expenseCents"] += cents(record);
    if (new Date(record.createdAt) > new Date(group.latest)) group.latest = record.createdAt;
  }
  return [...map.values()].map(p => ({ ...p, expense: p.expenseCents / 100, income: p.incomeCents / 100 })).sort((a, b) => new Date(b.latest) - new Date(a.latest));
});
const namedPeople = computed(() => groups.value.filter(p => p.name));
const visiblePeople = computed(() => groups.value.filter(p => (p.name || '未填写往来人').includes(search.value.trim())));
const selectedPerson = computed(() => groups.value.find(p => p.name === selectedName.value));
const selectedRecords = computed(() => [...(selectedPerson.value?.records || [])].filter(r => direction.value === "all" || r.type === direction.value).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)));
watch(visiblePeople, list => { if (!list.some(p => p.name === selectedName.value)) selectedName.value = list[0]?.name ?? null; });
watch(selectedName, () => { direction.value = "all"; });
onMounted(load); watch(ledgerRevision, load);
async function load() { records.value = await loadTransactionsFromStore(); loading.value = false; }
function addGift() { openEntryEditor(null, { category: "人情", counterparty: selectedPerson.value?.name || "" }); }
function money(value) { return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value); }
function shortDate(value) { return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(new Date(value)); }
</script>
