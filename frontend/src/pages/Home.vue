<template>
  <main class="app-shell home-shell">
    <header class="overview-heading"><h1>总览</h1><time :datetime="todayDate">{{ todayLabel }}</time></header>

    <section class="module-grid" aria-label="今日收支概览">
      <router-link class="module-card balance-card" to="/balance">
        <span>今日结余 <ChevronRight :size="14" /></span><strong>{{ money(todayBalance) }}</strong><small>收入减去支出</small>
      </router-link>
      <router-link class="module-card income-card" to="/income" :aria-label="`查看今日收入 ${money(todayIncome)}`">
        <span><i class="stat-icon income"><ArrowDownLeft :size="15" /></i> 今日收入</span><strong>{{ money(todayIncome) }}</strong><small>查看收入 <ArrowUpRight :size="12" /></small>
      </router-link>
      <router-link class="module-card expense-card" to="/expense" :aria-label="`查看今日支出 ${money(todayExpense)}`">
        <span><i class="stat-icon expense"><ArrowUpRight :size="15" /></i> 今日支出</span><strong>{{ money(todayExpense) }}</strong><small>查看支出 <ArrowUpRight :size="12" /></small>
      </router-link>
    </section>

    <div class="overview-workspace"><div class="overview-main">
    <section class="ai-panel">
      <header class="composer-heading"><div class="composer-title"><span class="composer-icon"><Sparkles :size="19" :stroke-width="1.6" /></span><h2>记一笔</h2></div><router-link class="composer-key" to="/keys">{{ features.text_ai ? '管理 AI' : '连接 AI' }} <ChevronRight :size="13" /></router-link></header>
      <p v-if="!features.text_ai" class="setup-note">先<router-link to="/keys">添加 API Key</router-link>，即可使用 AI 记账。</p>
      <div class="composer-input">
        <textarea v-model.trim="aiText" :disabled="analyzing || saving" aria-label="描述这次收支" rows="4" placeholder="午餐 25 元，打车 18 元…"></textarea>
        <div class="ai-actions">
          <label class="upload-plus" :class="{ unavailable: !features.image_ai || analyzing || saving }" :title="features.image_ai ? '上传账单图片' : '当前 Key 未配置图片模型'">
            <ImagePlus :size="18" :stroke-width="1.6" /><span>上传账单</span><input aria-label="上传账单图片" type="file" accept="image/png,image/jpeg,image/webp" :disabled="analyzing || saving || !features.image_ai" @change="handleImageUpload" />
          </label>
          <button class="primary-btn" :disabled="analyzing || saving || !aiText || !features.text_ai" @click="handleTextAnalysis"><Sparkles :size="15" />{{ analyzing ? '分析中…' : reportVisible ? '重新分析' : 'AI 分析' }}</button>
        </div>
      </div>
      <div v-if="hasLocalDraft" class="composer-draft-state"><span>{{ draftError ? '当前草稿尚未保存' : recoveredDraft ? '已恢复上次未完成的草稿' : '草稿已自动保存在此设备' }}</span><button class="text-button" :disabled="analyzing || saving" @click="discardHomeDraft">清除草稿</button></div>
      <p v-if="draftError" class="error-text" role="alert">{{ draftError }}</p>
      <p v-if="aiError && !reportVisible" class="error-text" role="alert">{{ aiError }}</p>
      <p v-if="savedMessage" class="draft-saved-message" role="status">{{ savedMessage }}</p>
      <AiDraftReview v-model="report.records" :visible="reportVisible" :analyzing="analyzing" :saving="saving"
        :advice="report.advice" :error="aiError" @confirm="saveAiRecords" @discard="closeReport" />
    </section>

    <LedgerQuery v-model="ledgerAnswer" :enabled="features.text_ai" :ledger-version="JSON.stringify(records)" />

    </div>
    <aside class="overview-aside">
      <RecentRecords v-model="records" @changed="ledgerAnswer = null" />
      <section class="manual-entry"><h2>手动记账</h2><div><router-link to="/expense"><Plus :size="16" /> 记支出</router-link><router-link to="/income"><Plus :size="16" /> 记收入</router-link></div><ImportLedger @imported="onImported" /></section>
    </aside></div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { addTransactionsToStore, loadTransactionsFromStore, todayRecords, totalAmount } from "../services/storage";
import { analyzeImageBill, analyzeTextExpense } from "../services/ai";
import { api, currentUser } from "../services/api";
import { deleteDraft, draftError, readDraft, saveDraft } from "../services/drafts";
import { ledgerRevision } from "../services/editor";
import AiDraftReview from "../components/AiDraftReview.vue";
import RecentRecords from "../components/RecentRecords.vue";
import ImportLedger from "../components/ImportLedger.vue";
import LedgerQuery from "../components/LedgerQuery.vue";
import { ArrowDownLeft, ArrowUpRight, ChevronRight, ImagePlus, Plus, Sparkles } from "@lucide/vue";

const records = ref([]);
const todayDate = new Date().toLocaleDateString("en-CA");
const todayLabel = new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date());
const draftOwner = currentUser.value.id;
const cachedDraft = readDraft('home-ai')?.data;
const recoveredDraft = ref(Boolean(cachedDraft));
const aiText = ref(cachedDraft?.text || "");
const ledgerAnswer = ref(null);
const analyzing = ref(false);
const saving = ref(false);
const aiError = ref("");
const features = ref({ text_ai: false, image_ai: false });
const savedMessage = ref("");
const reportVisible = ref(Boolean(cachedDraft?.reportVisible));
const report = ref(cachedDraft?.report || emptyReport());
const hasLocalDraft = computed(() => Boolean(aiText.value || reportVisible.value));

const todayIncome = computed(() => totalAmount(todayRecords(records.value, "income")));
const todayExpense = computed(() => totalAmount(todayRecords(records.value, "expense")));
const todayBalance = computed(() => todayIncome.value - todayExpense.value);

onMounted(async () => {
  records.value = await loadTransactionsFromStore();
  try { features.value = await api("/api/features"); }
  catch (error) { aiError.value = error.message; }
});

watch(aiText, () => {
  if (!analyzing.value && !saving.value) { closeReport(); savedMessage.value = ""; }
}, { flush: "sync" });

watch([aiText, report, reportVisible], () => {
  if (hasLocalDraft.value) saveDraft('home-ai', { text: aiText.value, report: report.value, reportVisible: reportVisible.value }, { kind: 'ai', title: aiText.value.slice(0, 45) || '图片识别待确认账单', path: '/' }, draftOwner);
  else deleteDraft('home-ai', draftOwner);
}, { deep: true, flush: 'sync' });
watch(ledgerRevision, async () => { records.value = await loadTransactionsFromStore(); ledgerAnswer.value = null; });
watch(() => readDraft('home-ai'), value => { if (!value && hasLocalDraft.value) discardHomeDraft(); });
function discardHomeDraft() { aiText.value = ''; closeReport(); recoveredDraft.value = false; deleteDraft('home-ai', draftOwner); }

async function handleTextAnalysis() {
  if (!aiText.value || analyzing.value || saving.value) return;
  closeReport();
  savedMessage.value = "";
  analyzing.value = true;
  aiError.value = "";
  try {
    report.value = await analyzeTextExpense(aiText.value);
    reportVisible.value = true;
  } catch (error) {
    aiError.value = error.message || "AI 分析失败";
  } finally {
    analyzing.value = false;
  }
}

async function handleImageUpload(event) {
  const file = event.target.files?.[0];
  if (!file || analyzing.value || saving.value) return;
  closeReport();
  savedMessage.value = "";
  if (file.size > 8 * 1024 * 1024) { aiError.value = "图片大小不能超过 8 MB"; event.target.value = ""; return; }
  analyzing.value = true;
  aiError.value = "";
  try {
    report.value = await analyzeImageBill(file);
    reportVisible.value = true;
  } catch (error) {
    aiError.value = error.message || "图片识别失败，请手动补充。";
  } finally {
    analyzing.value = false;
    event.target.value = "";
  }
}

async function saveAiRecords() {
  if (saving.value || analyzing.value || !reportVisible.value || !report.value.records.length) return;
  saving.value = true;
  aiError.value = "";
  try {
    const count = report.value.records.length;
    records.value = await addTransactionsToStore(report.value.records);
    aiText.value = "";
    ledgerAnswer.value = null;
    closeReport();
    savedMessage.value = `已确认记账，${count} 笔记录已保存到账本。`;
  } catch (error) { aiError.value = error.message; }
  finally { saving.value = false; }
}

function closeReport() {
  aiError.value = "";
  reportVisible.value = false;
  report.value = emptyReport();
}

async function onImported() {
  records.value = await loadTransactionsFromStore();
  ledgerAnswer.value = null;
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
