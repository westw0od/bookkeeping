<template>
  <div class="import-entry">
    <button type="button" class="import-trigger" @click="open"><Upload :size="14" />导入历史账单</button>
    <p v-if="notice" class="import-notice" role="status">{{ notice }}</p>
    <div v-if="visible" class="modal-mask" @click.self="close" @keydown.esc.prevent="close">
      <section class="modal-card import-dialog" role="dialog" aria-modal="true" aria-labelledby="import-title">
        <header class="import-heading"><div><h2 id="import-title">导入历史账单</h2><p>普通收支与人情往来，使用同一份模板。</p></div><button type="button" class="import-close" aria-label="关闭导入窗口" :disabled="busy" @click="close"><X :size="20" /></button></header>
        <div class="import-template"><FileJson :size="23" /><div><strong>标准 JSON 模板</strong><p>填写日期、金额、分类和往来人等信息。</p></div><button type="button" :disabled="busy" @click="downloadTemplate">下载模板</button></div>
        <details class="import-format" :open="!preview">
          <summary>格式示例 <span>一笔人情支出</span></summary>
          <pre aria-label="账单 JSON 格式示例"><code>{{ formatExample }}</code></pre>
          <div class="import-format-guide">
            <p><strong>必填信息</strong>每笔填写编号、日期、收支类型、金额和分类。日期用 YYYY-MM-DD；expense 表示支出，income 表示收入。</p>
            <p><strong>人情往来</strong>分类填「人情」，counterparty 填往来人，event 填事由；note 是备注。这三项可留空。</p>
            <p><strong>多笔账单</strong>在 records 中依次添加，用逗号分隔。保持 format 不变，source 填来源名称，同一来源内的 external_id 不可重复。</p>
          </div>
        </details>
        <label class="import-picker"><Upload :size="20" /><strong>{{ filename || '选择整理好的 JSON 文件' }}</strong><span>最多 1,000 条，文件不超过 2 MB</span><input aria-label="选择导入文件" type="file" accept=".json,application/json" :disabled="busy" @change="selectFile" /></label>
        <p v-if="busy" class="muted" role="status">{{ committing ? '正在导入…' : '正在校验…' }}</p>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <div v-if="preview" class="import-preview">
          <div class="import-counts"><div><span>待导入</span><strong>{{ preview.new_count }} 笔</strong></div><div><span>新增收入</span><strong class="income-text">{{ money(preview.income) }}</strong></div><div><span>新增支出</span><strong class="expense-text">{{ money(preview.expense) }}</strong></div></div>
          <p v-if="preview.duplicate_count || preview.removed_count" class="import-skipped">{{ preview.duplicate_count }} 笔重复记录、{{ preview.removed_count }} 笔已删除记录将跳过，不会重复入账或自动恢复。</p>
          <ul class="import-rows"><li v-for="row in preview.preview.slice(0, 5)" :key="row.external_id"><div><strong>{{ row.counterparty ? `${row.counterparty} · ${row.event || row.category}` : row.note || row.category }}</strong><small>{{ row.date }} · {{ row.type === 'income' ? '收入' : '支出' }} · {{ row.category }}</small></div><b>{{ money(row.amount) }}</b></li></ul>
          <p v-if="preview.new_count > 5" class="muted">这里只展示前 5 笔，确认后会导入全部 {{ preview.new_count }} 笔。</p>
        </div>
        <footer class="modal-actions"><button class="secondary-btn" type="button" :disabled="busy" @click="close">取消</button><button class="primary-btn" type="button" :disabled="busy || !preview?.new_count" @click="commit">{{ committing ? '导入中…' : preview ? `确认导入 ${preview.new_count} 笔` : '请先选择文件' }}</button></footer>
        <p class="import-footnote">仅在确认后写入你的账本。同一来源和外部编号不会重复导入。</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onUnmounted, ref } from "vue";
import { FileJson, Upload, X } from "@lucide/vue";
import { api } from "../services/api";
const emit = defineEmits(["imported"]);
const formatExample = `{
  "format": "bookkeeping.v1",
  "source": "历史人情账本",
  "records": [{
    "external_id": "gift-001",
    "date": "2026-10-01",
    "type": "expense", "amount": "500.00",
    "category": "人情",
    "counterparty": "张三", "event": "婚礼",
    "note": "随礼"
  }]
}`;
const visible = ref(false), busy = ref(false), committing = ref(false), filename = ref(""), preview = ref(null), error = ref(""), notice = ref("");
let documentValue = null;
function money(value) { return `¥${Number(value || 0).toFixed(2)}`; }
function open() { visible.value = true; filename.value = ""; preview.value = null; documentValue = null; error.value = ""; notice.value = ""; document.body.style.overflow = "hidden"; }
function close() { if (busy.value) return; visible.value = false; document.body.style.overflow = ""; }
onUnmounted(() => { document.body.style.overflow = ""; });
async function downloadTemplate() {
  try {
    const template = await api("/api/ledger/import/template");
    const url = URL.createObjectURL(new Blob([JSON.stringify(template, null, 2)], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "bookkeeping-import-template.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) { error.value = err.message; }
}
async function selectFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  preview.value = null; error.value = ""; documentValue = null; filename.value = file.name;
  if (file.size > 2 * 1024 * 1024) { error.value = "文件不能超过 2 MB"; event.target.value = ""; return; }
  busy.value = true;
  try {
    const raw = (await file.text()).replace(/^\uFEFF/, "");
    try { documentValue = JSON.parse(raw); } catch { throw new Error("文件不是有效 JSON，请参考模板检查格式"); }
    preview.value = await api("/api/ledger/import?dry_run=true", { method: "POST", body: documentValue });
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; event.target.value = ""; }
}
async function commit() {
  if (busy.value || !preview.value?.new_count || !documentValue) return;
  busy.value = true; committing.value = true; error.value = "";
  try {
    const result = await api("/api/ledger/import?dry_run=false", { method: "POST", body: documentValue });
    visible.value = false; document.body.style.overflow = "";
    notice.value = `已导入 ${result.imported_count} 笔账单，跳过 ${result.duplicate_count + result.removed_count} 笔。`;
    emit("imported");
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; committing.value = false; }
}
</script>

<style scoped>
.import-entry { display: block; margin-top: 16px; padding-top: 15px; border-top: 1px solid #f0f0f3; }
.import-trigger { display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; border: 0; background: transparent; color: #8b8b98; font-size: 11px; padding: 2px 0; }
.import-trigger:hover { color: var(--blue); }
.import-notice { font-size: 11px; color: #6b8a73; line-height: 1.8; margin: 13px 0 0; }
.import-dialog { width: min(560px, 100%); }
.import-heading { display: flex; justify-content: space-between; gap: 15px; }
.import-heading h2 { font-size: 21px; font-weight: 600; color: var(--ink); }
.import-heading p { font-size: 12px; color: #a1a1ab; line-height: 1.8; margin: 9px 0 0; }
.import-close { border: 0; background: transparent; color: #a5a5af; align-self: flex-start; padding: 3px; }
.import-template { display: flex; align-items: center; gap: 12px; padding: 16px; border: 1px solid #eaeaf0; border-radius: 12px; background: #fafafd; margin-top: 25px; color: #9b9baa; }
.import-template > div { flex: 1; }
.import-template strong { font-size: 12px; color: #797987; font-weight: 500; }
.import-template p { margin: 6px 0 0; font-size: 11px; line-height: 1.7; }
.import-template button { border: 0; color: var(--blue); background: transparent; padding: 0; font-size: 11px; white-space: nowrap; }
.import-format { margin-top: 18px; border: 1px solid #eaeaf0; border-radius: 12px; overflow: hidden; }
.import-format summary { padding: 13px 15px; color: #53535f; font-size: 12px; cursor: pointer; }
.import-format summary span { margin-left: 8px; color: #92929e; font-size: 11px; }
.import-format pre { margin: 0; padding: 13px 15px; white-space: pre-wrap; overflow-wrap: anywhere; background: #f7f7fa; border-block: 1px solid #eaeaf0; color: #47475a; font: 11px/1.7 ui-monospace, SFMono-Regular, Consolas, monospace; tab-size: 2; }
.import-format-guide { padding: 4px 15px 13px; }
.import-format-guide p { margin: 10px 0 0; color: #83838f; font-size: 11px; line-height: 1.8; overflow-wrap: anywhere; }
.import-format-guide strong { color: #575763; font-weight: 500; margin-right: 6px; }
.import-picker { position: relative; display: flex; align-items: center; flex-direction: column; gap: 12px; padding: 25px 15px; border: 1px dashed #dcdce5; background: #fff; border-radius: 12px; color: #a7a7b2; cursor: pointer; margin-top: 18px; }
.import-picker strong { font-size: 13px; font-weight: 400; color: #8a8a98; word-break: break-all; }
.import-picker span { font-size: 10px; }
.import-picker input { position: absolute; inset: 0; width: 100%; height: 100%; padding: 0; opacity: 0; cursor: pointer; }
.import-picker:focus-within { outline: 3px solid #0071e320; outline-offset: 2px; }
.import-counts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 20px; }
.import-counts > div { border-radius: 10px; padding: 13px; background: #f6f6f9; }
.import-counts span { display: block; color: #a4a4af; font-size: 10px; margin-bottom: 8px; }
.import-counts strong { font-size: 16px; font-weight: 500; color: #686878; }
.import-skipped, .import-footnote { color: #a3a3ae; font-size: 11px; line-height: 1.8; margin: 14px 0 0; }
.import-rows { list-style: none; padding: 0; margin: 17px 0 0; }
.import-rows li { display: flex; align-items: center; gap: 15px; justify-content: space-between; border-top: 1px solid #eeeef3; padding: 12px 0; }
.import-rows strong { font-size: 12px; font-weight: 500; color: #7a7a87; }
.import-rows small { display: block; margin-top: 5px; font-size: 10px; color: #ababba; }
.import-rows b { font-size: 12px; font-weight: 500; color: #868691; white-space: nowrap; }
.import-footnote { font-size: 10px; text-align: center; margin-top: 18px; }
@media (max-width: 480px) { .import-template { flex-wrap: wrap; } .import-counts { gap: 6px; } .import-counts > div { padding: 11px 9px; } .import-counts strong { font-size: 14px; } }
</style>
