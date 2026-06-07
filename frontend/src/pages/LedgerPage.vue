<template>
  <main class="app-shell">
    <header class="page-nav">
      <router-link class="back-link" to="/">返回首页</router-link>
      <div>
        <p class="eyebrow">{{ type === "income" ? "Income" : "Expense" }}</p>
        <h1>{{ pageTitle }}</h1>
      </div>
    </header>

    <section class="date-toolbar">
      <div class="period-tabs">
        <button :class="{ active: periodMode === 'day' }" type="button" @click="periodMode = 'day'">按日</button>
        <button :class="{ active: periodMode === 'month' }" type="button" @click="periodMode = 'month'">按月</button>
        <button :class="{ active: periodMode === 'year' }" type="button" @click="periodMode = 'year'">按年</button>
      </div>
      <button class="secondary-btn" type="button" @click="movePeriod(-1)">{{ previousLabel }}</button>
      <label>
        {{ pickerLabel }}
        <input v-if="periodMode === 'day'" v-model="selectedDate" type="date" />
        <input v-else-if="periodMode === 'month'" v-model="selectedMonth" type="month" />
        <input v-else v-model.number="selectedYear" type="number" min="2000" max="2100" />
      </label>
      <button class="secondary-btn" type="button" @click="movePeriod(1)">{{ nextLabel }}</button>
      <button class="secondary-btn" type="button" @click="resetToCurrentPeriod">{{ currentLabel }}</button>
    </section>

    <section class="ledger-summary">
      <article class="summary-card">
        <span>{{ periodLabel }}{{ type === "income" ? "总收入" : "总支出" }}</span>
        <strong :class="type === 'income' ? 'income-text' : 'expense-text'">{{ money(selectedTotal) }}</strong>
      </article>
      <article class="summary-card">
        <span>{{ periodLabel }}记录数</span>
        <strong>{{ selectedTypedRecords.length }}</strong>
      </article>
    </section>

    <section class="category-grid">
      <button
        v-for="category in categories"
        :key="category"
        :class="['category-card', { active: selectedCategory === category }]"
        :style="categoryCardStyle(category)"
        @click="selectCategory(category)"
      >
        <span class="category-icon" :class="type" :style="categoryIconStyle(category)">
          <component :is="categoryIcon(category)" :size="24" :stroke-width="2.2" />
        </span>
        <span class="category-name">{{ category }}</span>
        <strong>{{ money(categoryTotals[category] || 0) }}</strong>
        <span class="category-action" @click.stop="openModal(category)">记一笔</span>
      </button>
    </section>

    <section v-if="selectedCategory" class="panel category-flow-panel">
      <div class="section-head">
        <h2>{{ selectedCategory }}流水</h2>
        <button class="secondary-btn" type="button" @click="openModal(selectedCategory)">记一笔</button>
      </div>
      <ul class="record-list">
        <li v-for="record in selectedCategoryRecords" :key="record.id">
          <span>{{ recordTitle(record) }}</span>
          <b :class="type === 'income' ? 'income-text' : 'expense-text'">{{ money(record.amount) }}</b>
          <small>{{ formatDateTime(record.createdAt) }}{{ record.note ? ` · ${record.note}` : "" }}</small>
        </li>
        <li v-if="!selectedCategoryRecords.length" class="empty-item">这个范围还没有{{ selectedCategory }}流水</li>
      </ul>
    </section>

    <section class="ledger-layout">
      <div class="panel">
        <div class="section-head">
          <h2>{{ type === "income" ? "收入列表" : "支出列表" }}</h2>
        </div>
        <ul class="record-list">
          <li v-for="record in selectedTypedRecords" :key="record.id">
            <span>{{ record.category }}</span>
            <b :class="type === 'income' ? 'income-text' : 'expense-text'">{{ money(record.amount) }}</b>
            <small>{{ formatDateTime(record.createdAt) }}</small>
          </li>
          <li v-if="!selectedTypedRecords.length" class="empty-item">这个范围还没有记录</li>
        </ul>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>分类占比</h2>
        </div>
        <div v-if="chartRows.length" class="simple-chart">
          <div v-for="[category, amount] in chartRows" :key="category" class="chart-row">
            <span>{{ category }}</span>
            <i><b :style="{ width: chartWidth(amount) }"></b></i>
            <strong>{{ money(amount) }}</strong>
          </div>
        </div>
        <p v-else class="analysis-text">记一笔后，这里会显示各类别占比。</p>
      </div>
    </section>

    <div v-if="activeCategory" class="modal-mask" @click.self="closeModal">
      <form class="modal-card" @submit.prevent="confirmRecord">
        <h2>请输入{{ activeCategory }}{{ type === "income" ? "收入" : "支出" }}金额</h2>
        <label>
          金额
          <input v-model.number="amount" type="number" min="0.01" step="0.01" placeholder="0.00" autofocus />
        </label>
        <label>
          记账时间
          <input v-model="recordTime" type="datetime-local" />
        </label>
        <label>
          备注
          <textarea v-model.trim="note" rows="3" placeholder="可选"></textarea>
        </label>
        <label v-if="activeCategory === '人情'">
          对方姓名
          <input v-model.trim="relationshipPerson" placeholder="对方姓名" />
        </label>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="modal-actions">
          <button class="secondary-btn" type="button" @click="closeModal">取消</button>
          <button class="primary-btn">确认</button>
        </div>
      </form>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import {
  BadgeDollarSign,
  BriefcaseBusiness,
  Car,
  CircleEllipsis,
  Gift,
  GraduationCap,
  HandCoins,
  HeartPulse,
  Map,
  Plane,
  PlugZap,
  Pizza,
  Shirt,
  Sparkles,
  Theater,
  Trophy,
  TrendingUp
} from "@lucide/vue";
import {
  addTransactionsToStore,
  createTransaction,
  dateInputValue,
  datetimeLocalValue,
  expenseCategories,
  formatDateTime,
  groupByCategory,
  incomeCategories,
  loadTransactionsFromStore,
  totalAmount
} from "../services/storage";

const props = defineProps({
  type: {
    type: String,
    required: true
  }
});

const today = dateInputValue(new Date());
const thisMonth = today.slice(0, 7);
const thisYear = new Date().getFullYear();
const records = ref([]);
const periodMode = ref("day");
const selectedDate = ref(today);
const selectedMonth = ref(thisMonth);
const selectedYear = ref(thisYear);
const selectedCategory = ref("");
const activeCategory = ref("");
const amount = ref(null);
const note = ref("");
const recordTime = ref(datetimeLocalValue(new Date()));
const relationshipPerson = ref("");
const error = ref("");

const categories = computed(() => (props.type === "income" ? incomeCategories : expenseCategories));
const pageTitle = computed(() => (props.type === "income" ? "收入模块" : "支出模块"));
const periodLabel = computed(() => {
  if (periodMode.value === "day") return selectedDate.value === today ? "今日" : `${selectedDate.value} `;
  if (periodMode.value === "month") return selectedMonth.value === thisMonth ? "本月" : `${selectedMonth.value} `;
  return selectedYear.value === thisYear ? "今年" : `${selectedYear.value}年 `;
});
const pickerLabel = computed(() => {
  if (periodMode.value === "day") return "查看日期";
  if (periodMode.value === "month") return "查看月份";
  return "查看年份";
});
const previousLabel = computed(() => ({ day: "前一天", month: "上个月", year: "上一年" }[periodMode.value]));
const nextLabel = computed(() => ({ day: "后一天", month: "下个月", year: "下一年" }[periodMode.value]));
const currentLabel = computed(() => ({ day: "今天", month: "本月", year: "今年" }[periodMode.value]));
const selectedTypedRecords = computed(() =>
  records.value.filter((record) => record.type === props.type && isRecordInCurrentPeriod(record))
);
const selectedTotal = computed(() => totalAmount(selectedTypedRecords.value));
const categoryTotals = computed(() => groupByCategory(selectedTypedRecords.value));
const chartRows = computed(() => Object.entries(categoryTotals.value).sort((a, b) => b[1] - a[1]));
const chartMax = computed(() => Math.max(1, ...chartRows.value.map((row) => row[1])));
const selectedCategoryRecords = computed(() =>
  selectedTypedRecords.value.filter((record) => record.category === selectedCategory.value)
);
const expenseIcons = {
  饮食: Pizza,
  购物: Shirt,
  娱乐: Theater,
  出行: Car,
  旅游: Plane,
  教育: GraduationCap,
  医疗: HeartPulse,
  人情: Gift,
  水电: PlugZap,
  其他: CircleEllipsis
};
const incomeIcons = {
  工资: BriefcaseBusiness,
  补贴: HandCoins,
  兼职: BadgeDollarSign,
  人情: Gift,
  幸运: Sparkles,
  奖金: Trophy,
  投资: TrendingUp,
  其他: CircleEllipsis
};
const categoryColors = {
  饮食: ["#fff3e6", "#d97706"],
  购物: ["#fdf2f8", "#db2777"],
  娱乐: ["#f5f3ff", "#7c3aed"],
  出行: ["#eef6ff", "#2563eb"],
  旅游: ["#ecfeff", "#0891b2"],
  教育: ["#f0fdf4", "#16a34a"],
  医疗: ["#fff1f2", "#e11d48"],
  人情: ["#fff7ed", "#ea580c"],
  水电: ["#eff6ff", "#1d4ed8"],
  工资: ["#ecfdf5", "#059669"],
  补贴: ["#f0fdf4", "#16a34a"],
  兼职: ["#eef2ff", "#4f46e5"],
  幸运: ["#fefce8", "#ca8a04"],
  奖金: ["#fff7ed", "#ea580c"],
  投资: ["#f0fdfa", "#0f766e"],
  其他: ["#f1f5f9", "#475569"]
};

onMounted(load);
watch(() => props.type, load);

async function load() {
  records.value = await loadTransactionsFromStore();
}

function openModal(category) {
  selectedCategory.value = category;
  activeCategory.value = category;
  amount.value = null;
  note.value = "";
  relationshipPerson.value = "";
  recordTime.value = `${defaultRecordDate()}T${currentTimeText()}`;
  error.value = "";
}

function selectCategory(category) {
  selectedCategory.value = selectedCategory.value === category ? "" : category;
}

function closeModal() {
  activeCategory.value = "";
}

async function confirmRecord() {
  if (!amount.value) {
    error.value = "金额不能为空";
    return;
  }
  if (Number(amount.value) <= 0) {
    error.value = "金额必须大于 0";
    return;
  }
  if (!recordTime.value) {
    error.value = "请选择记账时间";
    return;
  }
  const finalNote = activeCategory.value === "人情" && relationshipPerson.value
    ? `${relationshipPerson.value}${note.value ? `：${note.value}` : ""}`
    : note.value;
  const record = createTransaction({
    type: props.type,
    category: activeCategory.value,
    amount: amount.value,
    note: finalNote,
    createdAt: new Date(recordTime.value).toISOString()
  });
  records.value = await addTransactionsToStore([record]);
  selectedDate.value = dateInputValue(new Date(record.createdAt));
  selectedMonth.value = selectedDate.value.slice(0, 7);
  selectedYear.value = new Date(record.createdAt).getFullYear();
  closeModal();
}

function movePeriod(amount) {
  if (periodMode.value === "day") {
    const date = new Date(`${selectedDate.value}T12:00:00`);
    date.setDate(date.getDate() + amount);
    selectedDate.value = dateInputValue(date);
    return;
  }
  if (periodMode.value === "month") {
    const date = new Date(`${selectedMonth.value}-01T12:00:00`);
    date.setMonth(date.getMonth() + amount);
    selectedMonth.value = dateInputValue(date).slice(0, 7);
    return;
  }
  selectedYear.value += amount;
}

function resetToCurrentPeriod() {
  selectedDate.value = today;
  selectedMonth.value = thisMonth;
  selectedYear.value = thisYear;
}

function currentTimeText() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function defaultRecordDate() {
  if (periodMode.value === "day") return selectedDate.value;
  if (periodMode.value === "month") {
    return selectedMonth.value === thisMonth ? today : `${selectedMonth.value}-01`;
  }
  return selectedYear.value === thisYear ? today : `${selectedYear.value}-01-01`;
}

function isRecordInCurrentPeriod(record) {
  const date = new Date(record.createdAt);
  if (periodMode.value === "day") {
    return dateInputValue(date) === selectedDate.value;
  }
  if (periodMode.value === "month") {
    return dateInputValue(date).slice(0, 7) === selectedMonth.value;
  }
  return date.getFullYear() === Number(selectedYear.value);
}

function chartWidth(value) {
  return `${Math.max(8, (value / chartMax.value) * 100)}%`;
}

function categoryIcon(category) {
  const icons = props.type === "income" ? incomeIcons : expenseIcons;
  return icons[category] || Map;
}

function categoryIconStyle(category) {
  const [background, color] = categoryColors[category] || categoryColors.其他;
  return { background, color };
}

function categoryCardStyle(category) {
  const [background, color] = categoryColors[category] || categoryColors.其他;
  return {
    background: `linear-gradient(135deg, #ffffff 0%, ${background} 100%)`,
    borderColor: `${color}26`
  };
}

function recordTitle(record) {
  if (record.category !== "人情") return record.note || record.category;
  const noteText = record.note || "未填写对象";
  return noteText.split(/[：:，,。]/)[0] || "未填写对象";
}

function money(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}
</script>
