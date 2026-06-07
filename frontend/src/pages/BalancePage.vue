<template>
  <main class="app-shell">
    <header class="page-nav">
      <router-link class="back-link" to="/">返回首页</router-link>
      <div>
        <p class="eyebrow">Balance</p>
        <h1>结余总览</h1>
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

    <section class="date-toolbar">
      <button class="secondary-btn" type="button" @click="moveDate(-1)">前一天</button>
      <label>
        查看日期
        <input v-model="selectedDate" type="date" />
      </label>
      <button class="secondary-btn" type="button" @click="moveDate(1)">后一天</button>
      <button class="secondary-btn" type="button" @click="selectedDate = today">今天</button>
    </section>

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
            @click="selectedDate = row.date"
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
import { computed, onMounted, ref } from "vue";
import { dateInputValue, loadTransactionsFromStore, recordsByDate, totalAmount } from "../services/storage";

const today = dateInputValue(new Date());
const records = ref([]);
const selectedDate = ref(today);

const totalIncome = computed(() => totalAmount(records.value.filter((record) => record.type === "income")));
const totalExpense = computed(() => totalAmount(records.value.filter((record) => record.type === "expense")));
const totalBalance = computed(() => totalIncome.value - totalExpense.value);
const selectedRecords = computed(() => recordsByDate(records.value, selectedDate.value));
const dayIncome = computed(() => totalAmount(selectedRecords.value.filter((record) => record.type === "income")));
const dayExpense = computed(() => totalAmount(selectedRecords.value.filter((record) => record.type === "expense")));
const dayBalance = computed(() => dayIncome.value - dayExpense.value);
const selectedDateLabel = computed(() => (selectedDate.value === today ? "今日" : `${selectedDate.value} `));
const balanceAdvice = computed(() => {
  if (!selectedRecords.value.length) return "这一天还没有收入或支出记录。";
  if (dayBalance.value > 0) return "这一天收入高于支出，现金流状态不错。";
  if (dayBalance.value === 0) return "这一天收支刚好持平。";
  return "这一天支出高于收入，可以回看支出明细，确认是否有非必要消费。";
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

function moveDate(days) {
  const date = new Date(`${selectedDate.value}T12:00:00`);
  date.setDate(date.getDate() + days);
  selectedDate.value = dateInputValue(date);
}

function round(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}

function money(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}
</script>
