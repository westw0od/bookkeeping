<template>
  <main class="app-shell home-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Smart Ledger</p>
        <h1>今天的钱，今天讲清楚</h1>
        <p class="hero-copy">输入一句话或上传账单截图，AI 会帮你拆成结构化记录并生成今日财报。</p>
      </div>
    </header>

    <section class="module-grid">
      <router-link class="module-card expense-card" to="/expense">
        <span>支出模块</span>
        <strong>{{ money(todayExpense) }}</strong>
        <small>饮食、购物、出行等</small>
      </router-link>
      <router-link class="module-card income-card" to="/income">
        <span>收入模块</span>
        <strong>{{ money(todayIncome) }}</strong>
        <small>工资、兼职、奖金等</small>
      </router-link>
      <router-link class="module-card balance-card" to="/balance">
        <span>今日结余</span>
        <strong>{{ money(todayBalance) }}</strong>
        <small>点击查看往天和总结余</small>
      </router-link>
    </section>

    <section class="ai-panel">
      <div class="ai-input-row">
        <textarea
          v-model.trim="aiText"
          rows="3"
          placeholder="输入今天的收入或支出"
        ></textarea>
        <label class="upload-plus" title="上传账单图片">
          +
          <input type="file" accept="image/*" @change="handleImageUpload" />
        </label>
      </div>
      <div class="ai-actions">
        <button class="primary-btn" :disabled="analyzing || !aiText" @click="handleTextAnalysis">
          {{ analyzing ? "分析中..." : "AI 分析" }}
        </button>
        <button v-if="report.records?.length" class="secondary-btn" @click="saveAiRecords">保存 AI 识别记录</button>
      </div>
    </section>

    <section class="query-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Ledger Search</p>
          <h2>问问你的账本</h2>
        </div>
      </div>
      <div class="query-row">
        <input
          v-model.trim="ledgerQuestion"
          placeholder="输入你想查询的账本问题"
          @keyup.enter="askLedger"
        />
        <button class="primary-btn" :disabled="!ledgerQuestion" @click="askLedger">查询</button>
      </div>
      <div v-if="ledgerAnswer" class="ledger-answer">
        <div class="report-metrics query-metrics">
          <div>
            <span>收入</span>
            <strong class="income-text">{{ money(ledgerAnswer.income) }}</strong>
          </div>
          <div>
            <span>支出</span>
            <strong class="expense-text">{{ money(ledgerAnswer.expense) }}</strong>
          </div>
          <div>
            <span>结余</span>
            <strong :class="ledgerAnswer.balance >= 0 ? 'income-text' : 'expense-text'">{{ money(ledgerAnswer.balance) }}</strong>
          </div>
        </div>
        <p class="analysis-text">{{ ledgerAnswer.summary }}</p>
        <ul class="record-list compact-list">
          <li v-for="record in ledgerAnswer.records" :key="record.id">
            <span>{{ record.type === "income" ? "收入" : "支出" }} · {{ record.category }}</span>
            <b :class="record.type === 'income' ? 'income-text' : 'expense-text'">{{ money(record.amount) }}</b>
            <small>{{ formatRecord(record) }}</small>
          </li>
          <li v-if="!ledgerAnswer.records.length" class="empty-item">没有找到匹配记录</li>
        </ul>
      </div>
    </section>

    <section v-if="reportVisible" class="report-card">
      <div class="section-head">
        <div>
          <p class="eyebrow">AI Report</p>
          <h2>今日财报分析</h2>
        </div>
        <div class="report-tools">
          <span class="confidence">置信度 {{ Math.round((report.confidence || 0) * 100) }}%</span>
          <button class="close-btn" type="button" title="关闭分析结果" @click="closeReport">×</button>
        </div>
      </div>

      <div class="report-metrics">
        <div>
          <span>今日总收入</span>
          <strong class="income-text">{{ money(report.incomeTotal) }}</strong>
        </div>
        <div>
          <span>今日总支出</span>
          <strong class="expense-text">{{ money(report.expenseTotal) }}</strong>
        </div>
        <div>
          <span>今日结余</span>
          <strong>{{ money(report.balance) }}</strong>
        </div>
      </div>

      <div class="report-columns">
        <div>
          <h3>消费记录</h3>
          <ul class="record-list compact-list">
            <li v-for="record in report.records" :key="record.id">
              <span>{{ record.type === "income" ? "收入" : "支出" }} · {{ record.category }}</span>
              <b>{{ money(record.amount) }}</b>
              <small>{{ record.note || "AI 识别" }}</small>
            </li>
          </ul>
        </div>
        <div>
          <h3>消费占比</h3>
          <div class="ratio-list">
            <div v-for="[category, ratio] in Object.entries(report.ratios || {})" :key="category">
              <span>{{ category }}</span>
              <i><b :style="{ width: `${Math.max(5, ratio)}%` }"></b></i>
              <strong>{{ ratio }}%</strong>
            </div>
          </div>
          <p class="analysis-text">{{ report.abnormal }}</p>
          <p class="analysis-text">{{ report.advice }}</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { addTransactionsToStore, loadTransactionsFromStore, todayRecords, totalAmount } from "../services/storage";
import { analyzeImageBill, analyzeTextExpense } from "../services/ai";

const records = ref([]);
const aiText = ref("");
const ledgerQuestion = ref("");
const ledgerAnswer = ref(null);
const analyzing = ref(false);
const reportVisible = ref(false);
const report = ref(emptyReport());

const todayIncome = computed(() => totalAmount(todayRecords(records.value, "income")));
const todayExpense = computed(() => totalAmount(todayRecords(records.value, "expense")));
const todayBalance = computed(() => todayIncome.value - todayExpense.value);

onMounted(async () => {
  records.value = await loadTransactionsFromStore();
});

async function handleTextAnalysis() {
  if (!aiText.value) return;
  analyzing.value = true;
  try {
    report.value = await analyzeTextExpense(aiText.value);
    reportVisible.value = true;
  } catch (error) {
    alert(error.message || "AI 分析失败");
  } finally {
    analyzing.value = false;
  }
}

async function handleImageUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  analyzing.value = true;
  try {
    report.value = await analyzeImageBill(file);
    reportVisible.value = true;
    if (report.value.records.length && report.value.confidence > 0.2) {
      records.value = await addTransactionsToStore(report.value.records);
    }
  } catch (error) {
    alert(error.message || "图片识别失败，请手动补充。");
  } finally {
    analyzing.value = false;
    event.target.value = "";
  }
}

async function saveAiRecords() {
  records.value = await addTransactionsToStore(report.value.records);
  aiText.value = "";
  closeReport();
  alert("AI 识别记录已保存");
}

function closeReport() {
  reportVisible.value = false;
  report.value = emptyReport();
}

function askLedger() {
  ledgerAnswer.value = analyzeLedgerQuestion(ledgerQuestion.value, records.value);
}

function analyzeLedgerQuestion(question, sourceRecords) {
  const normalized = question.replace(/\s+/g, "");
  const range = resolveDateRange(normalized);
  const category = resolveCategory(normalized);
  const person = resolvePerson(normalized);
  const type = resolveType(normalized);

  const matched = sourceRecords.filter((record) => {
    const createdAt = new Date(record.createdAt);
    if (range && (createdAt < range.start || createdAt > range.end)) return false;
    if (type && record.type !== type) return false;
    if (category && record.category !== category) return false;
    if (person && !recordText(record).includes(person)) return false;
    if (!person && !category && !type && range && !recordText(record).includes(normalized)) return true;
    if (!person && !category && !type && !range) return recordText(record).includes(normalized);
    return true;
  });

  const income = totalAmount(matched.filter((record) => record.type === "income"));
  const expense = totalAmount(matched.filter((record) => record.type === "expense"));
  const rangeText = range?.label || "全部时间";
  const topic = [person ? `${person}相关` : "", category || "", type === "income" ? "收入" : "", type === "expense" ? "支出" : ""]
    .filter(Boolean)
    .join(" · ");
  const summary = matched.length
    ? `${rangeText}${topic ? `，${topic}` : ""}共找到 ${matched.length} 条记录，收入 ${money(income)}，支出 ${money(expense)}，结余 ${money(income - expense)}。`
    : `${rangeText}${topic ? `，${topic}` : ""}没有找到匹配记录。`;

  return {
    records: matched.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)),
    income,
    expense,
    balance: income - expense,
    summary
  };
}

function resolveDateRange(text) {
  const now = new Date();
  if (text.includes("今天") || text.includes("今日")) {
    return dayRange(now, "今天");
  }
  if (text.includes("昨天")) {
    const date = new Date(now);
    date.setDate(date.getDate() - 1);
    return dayRange(date, "昨天");
  }
  if (text.includes("这个月") || text.includes("本月")) {
    return monthRange(now.getFullYear(), now.getMonth(), "本月");
  }
  if (text.includes("上个月")) {
    return monthRange(now.getFullYear(), now.getMonth() - 1, "上个月");
  }
  return null;
}

function resolveCategory(text) {
  const groups = [
    ["饮食", ["吃饭", "饮食", "咖啡", "午餐", "晚餐", "早餐", "外卖"]],
    ["购物", ["购物", "买衣服", "衣服", "鞋", "包"]],
    ["娱乐", ["娱乐", "电影", "游戏", "唱歌"]],
    ["出行", ["出行", "打车", "地铁", "公交", "车费"]],
    ["旅游", ["旅游", "酒店", "机票"]],
    ["教育", ["教育", "学习", "课程", "培训"]],
    ["医疗", ["医疗", "看病", "药", "医院"]],
    ["人情", ["人情", "红包", "礼金", "随礼", "份子钱", "结婚"]],
    ["水电", ["水电", "水费", "电费", "燃气", "物业", "宽带"]],
    ["工资", ["工资", "薪资"]],
    ["兼职", ["兼职"]],
    ["补贴", ["补贴"]],
    ["奖金", ["奖金"]],
    ["投资", ["投资", "收益", "分红"]]
  ];
  return groups.find(([, words]) => words.some((word) => text.includes(word)))?.[0] || "";
}

function resolvePerson(text) {
  const patterns = [/和(.+?)的?人情/, /我和(.+?)的/, /(.+?)的人情往来/, /(.+?)女儿/, /(.+?)儿子/];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) return match[1].replace(/我|这个月|本月|今天|昨天|花了多少钱|多少钱/g, "");
  }
  return "";
}

function resolveType(text) {
  if (text.includes("收入") || text.includes("赚") || text.includes("到账")) return "income";
  if (text.includes("支出") || text.includes("花了") || text.includes("消费") || text.includes("花多少钱")) return "expense";
  return "";
}

function recordText(record) {
  return `${record.category}${record.note || ""}${record.type === "income" ? "收入" : "支出"}`;
}

function dayRange(date, label) {
  const start = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
  const end = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
  return { start, end, label };
}

function monthRange(year, month, label) {
  const start = new Date(year, month, 1, 0, 0, 0, 0);
  const end = new Date(year, month + 1, 0, 23, 59, 59, 999);
  return { start, end, label };
}

function formatRecord(record) {
  const time = new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(record.createdAt));
  return `${time}${record.note ? ` · ${record.note}` : ""}`;
}

function emptyReport() {
  return {
    records: [],
    incomeTotal: 0,
    expenseTotal: 0,
    balance: 0,
    incomeByCategory: {},
    expenseByCategory: {},
    ratios: {},
    abnormal: "",
    advice: "",
    confidence: 0
  };
}

function money(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}
</script>
