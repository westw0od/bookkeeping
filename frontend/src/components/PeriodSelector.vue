<template>
  <div class="period-selector" aria-label="统计时间范围">
    <div class="period-tabs"><button type="button" :class="{ active: mode === 'day' }" :aria-pressed="mode === 'day'" @click="mode = 'day'">按日</button><button type="button" :class="{ active: mode === 'month' }" :aria-pressed="mode === 'month'" @click="mode = 'month'">按月</button><button type="button" :class="{ active: mode === 'all' }" :aria-pressed="mode === 'all'" @click="mode = 'all'">全部日期</button></div>
    <div v-if="mode !== 'all'" class="period-picker"><button class="icon-button" :aria-label="mode === 'day' ? '前一天' : '上个月'" @click="move(-1)"><ChevronLeft :size="17" /></button><input v-if="mode === 'day'" v-model="day" type="date" aria-label="查看日期" required /><input v-else v-model="month" type="month" aria-label="查看月份" required /><button class="icon-button" :aria-label="mode === 'day' ? '后一天' : '下个月'" @click="move(1)"><ChevronRight :size="17" /></button><button class="text-button" @click="reset">{{ mode === 'day' ? '今天' : '本月' }}</button></div>
  </div>
</template>
<script setup>
import { ChevronLeft, ChevronRight } from "@lucide/vue";
import { dateInputValue } from "../services/storage";
const mode = defineModel('mode', { type: String, default: 'month' });
const day = defineModel('day', { type: String, default: () => dateInputValue(new Date()) });
const month = defineModel('month', { type: String, default: () => dateInputValue(new Date()).slice(0, 7) });
function move(delta) {
  const value = mode.value === 'day' ? day.value : month.value + '-01';
  const date = new Date(`${value}T12:00:00`);
  if (!Number.isFinite(date.getTime())) { reset(); return; }
  if (mode.value === 'day') { date.setDate(date.getDate() + delta); day.value = dateInputValue(date); }
  else { date.setMonth(date.getMonth() + delta); month.value = dateInputValue(date).slice(0, 7); }
}
function reset() { const today = dateInputValue(new Date()); day.value = today; month.value = today.slice(0, 7); }
</script>
<style scoped>
.period-selector { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.period-selector .period-tabs { width: auto; }
.period-picker { display: flex; align-items: center; gap: 8px; min-width: 0; }
.period-picker input { width: auto; min-width: 0; margin: 0; padding: 8px 10px; border: 1px solid #e7e7ee; background: #fff; font-size: 13px; }
.period-picker .icon-button { width: 30px; height: 30px; background: transparent; }
.period-picker .text-button { white-space: nowrap; padding: 7px; }
@media (max-width: 480px) { .period-selector { gap: 14px; } .period-picker { width: 100%; justify-content: space-between; } .period-picker input { flex: 1; max-width: 200px; } }
</style>
