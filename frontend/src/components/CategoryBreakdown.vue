<template>
  <section class="panel category-breakdown" :class="type" :aria-label="`${label}分类统计`">
    <header class="section-head"><h2>{{ label }}分类</h2><span>{{ periodLabel }}</span></header>
    <div class="category-overview"><strong>{{ money(totalCents / 100) }}</strong><small>{{ rows.length }} 个分类 · {{ relevant.length }} 笔</small></div>
    <p v-if="rows.length" class="category-main">{{ type === 'expense' ? '主要花在' : '主要来自' }} <b>{{ rows[0].category }}</b><span>{{ percent(rows[0].cents) }}%</span></p>
    <ol v-if="rows.length" class="category-ranking"><li v-for="(row, index) in rows" :key="row.category"><button type="button" :aria-label="`查看${row.category}${label}明细`" :aria-pressed="selected === row.category" @click="$emit('select', { type, category: row.category })"><span class="category-rank">{{ index + 1 }}</span><span class="category-bar-content"><span class="category-bar-label"><strong>{{ row.category }}</strong><small>{{ row.count }} 笔</small><b>{{ money(row.cents / 100) }}</b><em>{{ percent(row.cents) }}%</em></span><span class="category-bar-track"><i :style="{ width: `${row.cents / totalCents * 100}%` }"></i></span></span></button></li></ol>
    <p v-else class="empty-copy">这个范围还没有{{ label }}记录。</p>
    <p v-if="rows.length" class="category-chart-hint">点击分类查看对应账单</p>
  </section>
</template>
<script setup>
import { computed } from "vue";
const props = defineProps({ records: { type: Array, default: () => [] }, type: { type: String, required: true }, periodLabel: String, selected: String });
defineEmits(['select']);
const label = computed(() => props.type === 'expense' ? '支出' : '收入');
const relevant = computed(() => props.records.filter(row => row.type === props.type && !row.revokedAt));
const rows = computed(() => {
  const groups = new Map();
  for (const row of relevant.value) {
    const name = row.category || '其他', group = groups.get(name) || { category: name, cents: 0, count: 0 };
    group.cents += Math.round(Number(row.amount) * 100); group.count++; groups.set(name, group);
  }
  return [...groups.values()].sort((a, b) => b.cents - a.cents || a.category.localeCompare(b.category, 'zh-CN'));
});
const totalCents = computed(() => rows.value.reduce((sum, row) => sum + row.cents, 0));
function percent(cents) { return totalCents.value ? (cents / totalCents.value * 100).toFixed(1).replace(/\.0$/, '') : '0'; }
function money(amount) { return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(amount); }
</script>
<style scoped>
.category-breakdown { padding: 25px; min-width: 0; }
.category-breakdown .section-head h2 { font-size: 16px; }
.category-breakdown .section-head > span { font-size: 11px; color: #777783; }
.category-overview { margin: 23px 0 14px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; }
.category-overview > strong { font-size: 29px; font-weight: 550; letter-spacing: -.8px; font-variant-numeric: tabular-nums; }
.category-overview > small { font-size: 11px; color: #777783; }
.category-main { display: flex; align-items: center; gap: 7px; color: #777783; padding: 12px; border-radius: 9px; background: #f6f6f9; font-size: 12px; margin: 0 0 16px; }
.category-main b { color: #454551; font-weight: 500; overflow-wrap: anywhere; }
.category-main > span { margin-left: auto; color: #6d6d7b; }
.category-ranking { padding: 0; margin: 0; list-style: none; }
.category-ranking button { display: flex; width: 100%; align-items: center; gap: 10px; border: 1px solid transparent; border-radius: 10px; padding: 11px 7px; background: none; text-align: left; }
.category-ranking button:hover, .category-ranking button[aria-pressed='true'] { background: #f7f7fb; border-color: #e8e8f0; }
.category-rank { font-size: 11px; color: #8c8c98; width: 15px; text-align: center; flex-shrink: 0; }
.category-bar-content { flex: 1; min-width: 0; }
.category-bar-label { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; align-items: baseline; gap: 9px; }
.category-bar-label strong { color: #464652; font-size: 13px; font-weight: 500; overflow-wrap: anywhere; }
.category-bar-label small { font-size: 10px; color: #83838f; }
.category-bar-label b { font-size: 13px; font-weight: 500; color: #4e4e5a; white-space: nowrap; font-variant-numeric: tabular-nums; }
.category-bar-label em { font-style: normal; font-size: 11px; color: #777783; min-width: 44px; text-align: right; }
.category-bar-track { display: block; margin-top: 10px; height: 5px; border-radius: 5px; background: #f1f1f5; overflow: hidden; }
.category-bar-track > i { display: block; height: 100%; border-radius: inherit; background: #cf9e8c; }
.income .category-bar-track > i { background: #8cb7a2; }
.category-chart-hint { font-size: 10px; color: #868692; margin: 16px 0 0 32px; }
@media (max-width: 480px) { .category-breakdown { padding: 22px 18px; } .category-overview > strong { font-size: 27px; } .category-bar-label { gap: 6px; } }
</style>
