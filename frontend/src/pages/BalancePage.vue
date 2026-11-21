<template>
  <main class="app-shell">
    <header class="page-nav">
      <router-link class="back-link" to="/">返回首页</router-link>
      <div>
        <p class="eyebrow">Balance</p>
        <h1>收支统计</h1>
      </div>
    </header>

    <section class="ledger-summary balance-summary">
      <article class="summary-card">
        <span>总结余</span>
        <strong :class="totalBalance >= 0 ? 'income-text' : 'expense-text'">{{ money(totalBalance) }}</strong>
      </article>
      <article class="summary-card">
        <span>累计收入</span>
        <strong class="income-text">{{ money(totalIncome) }}</strong>
      </article>
      <article class="summary-card">
        <span>累计支出</span>
        <strong class="expense-text">{{ money(totalExpense) }}</strong>
      </article>
    </section>

    <section class="panel transaction-period"><PeriodSelector v-model:mode="periodMode" v-model:day="selectedDate" v-model:month="selectedMonth" /></section>
    <div class="classification-grid"><CategoryBreakdown :records="selectedRecords" type="expense" :period-label="selectedDateLabel.trim()" @select="openCategory" /><CategoryBreakdown :records="selectedRecords" type="income" :period-label="selectedDateLabel.trim()" @select="openCategory" /></div>

    <section class="ledger-layout">
      <div class="panel">
        <div class="section-head">
          <h2>{{ selectedDateLabel }}结余</h2>
        </div>
        <div class="report-metrics day-balance-metrics">
          <div>
            <span>收入</span>
            <strong class="income-text">{{ money(dayIncome) }}</strong>
          </div>
          <div>
            <span>支出</span>
            <strong class="expense-text">{{ money(dayExpense) }}</strong>
          </div>
          <div>
            <span>结余</span>
            <strong :class="dayBalance >= 0 ? 'income-text' : 'expense-text'">{{ money(dayBalance) }}</strong>
          </div>
        </div>
        <p class="analysis-text">{{ balanceAdvice }}</p>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>每日结余</h2>
        </div>
        <div v-if="dailyRows.length" class="daily-list">
          <button
            v-for="row in dailyRows"
            :key="row.date"
            :class="['daily-row', { active: row.date === selectedDate }]"
            type="button"
            @click="selectedDate = row.date; periodMode = 'day'"
          >
            <span>{{ row.date }}</span>
            <small>收 {{ money(row.income) }} / 支 {{ money(row.expense) }}</small>
            <strong :class="row.balance >= 0 ? 'income-text' : 'expense-text'">{{ money(row.balance) }}</strong>
          </button>
        </div>
        <p v-else class="analysis-text">还没有任何账本记录。</p>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import CategoryBreakdown from "../components/CategoryBreakdown.vue";
import PeriodSelector from "../components/PeriodSelector.vue";
import { ledgerRevision } from "../services/editor";
import { dateInputValue, inPeriod, loadTransactionsFromStore, totalAmount } from "../services/storage";

const today = dateInputValue(new Date());
const records = ref([]);
const selectedDate = ref(today);
const selectedMonth = ref(today.slice(0, 7)), periodMode = ref('day'), router = useRouter();

const totalIncome = computed(() => totalAmount(records.value.filter((record) => record.type === "income")));
const totalExpense = computed(() => totalAmount(records.value.filter((record) => record.type === "expense")));
const totalBalance = computed(() => totalIncome.value - totalExpense.value);
const selectedRecords = computed(() => records.value.filter(row => !row.revokedAt && inPeriod(row, periodMode.value, selectedDate.value, selectedMonth.value)));
const dayIncome = computed(() => totalAmount(selectedRecords.value.filter((record) => record.type === "income")));
const dayExpense = computed(() => totalAmount(selectedRecords.value.filter((record) => record.type === "expense")));
const dayBalance = computed(() => dayIncome.value - dayExpense.value);
const selectedDateLabel = computed(() => periodMode.value === 'all' ? '累计' : periodMode.value === 'month' ? selectedMonth.value === today.slice(0, 7) ? '本月' : `${selectedMonth.value} ` : selectedDate.value === today ? '今日' : `${selectedDate.value} `);
const balanceAdvice = computed(() => {
  if (!selectedRecords.value.length) return "这个范围还没有收入或支出记录。";
  if (dayBalance.value > 0) return "这个范围收入高于支出，可结合分类查看收入来源。";
  if (dayBalance.value === 0) return "这个范围收支持平。";
  return "这个范围支出高于收入，可结合分类查看主要开销。";
});
const dailyRows = computed(() => {
  const map = new Map();
  for (const record of records.value) {
    const date = dateInputValue(new Date(record.createdAt));
    const item = map.get(date) || { date, income: 0, expense: 0, balance: 0 };
    if (record.type === "income") item.income += Number(record.amount || 0);
    if (record.type === "expense") item.expense += Number(record.amount || 0);
    item.balance = item.income - item.expense;
    map.set(date, item);
  }
  return [...map.values()]
    .map((item) => ({
      ...item,
      income: round(item.income),
      expense: round(item.expense),
      balance: round(item.balance)
    }))
    .sort((a, b) => b.date.localeCompare(a.date));
});

onMounted(async () => {
  records.value = await loadTransactionsFromStore();
});
watch(ledgerRevision, async () => { records.value = await loadTransactionsFromStore(); });

function openCategory(value) { router.push({ path: '/ledger', query: { period: periodMode.value, day: selectedDate.value, month: selectedMonth.value, type: value.type, category: value.category } }); }

function round(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}

function money(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}
</script>
