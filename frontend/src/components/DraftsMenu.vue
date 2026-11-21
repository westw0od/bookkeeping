<template>
  <button class="toolbar-drafts" type="button" :aria-label="`我的草稿，${savedDrafts.length} 份`" @click="visible = true"><FilePenLine :size="17" /><span>草稿</span><b v-if="savedDrafts.length">{{ savedDrafts.length }}</b></button>
  <Teleport to="body"><div v-if="visible" class="modal-mask" @click.self="visible = false" @keydown.esc="visible = false">
    <section class="modal-card drafts-dialog" role="dialog" aria-modal="true" aria-labelledby="drafts-title">
      <header class="section-head"><h2 id="drafts-title">我的草稿</h2><button class="icon-button" aria-label="关闭草稿列表" @click="visible = false"><X :size="20" /></button></header>
      <p class="page-description">仅保存在当前设备，登录对应账号后可继续填写。</p>
      <ul class="drafts-list"><li v-for="item in savedDrafts" :key="item.slot"><button :aria-label="`继续草稿：${item.title}`" @click="resume(item)"><strong>{{ item.title }}</strong><small>{{ formatDateTime(item.updatedAt) }} · {{ item.kind === 'edit' ? '账单编辑' : item.kind === 'ai' ? 'AI 记账' : '手动记账' }}</small></button><button class="text-button" :aria-label="`删除草稿：${item.title}`" @click="deleteDraft(item.slot)">删除</button></li></ul>
      <p v-if="!savedDrafts.length" class="empty-copy">没有待处理的草稿。</p>
    </section>
  </div></Teleport>
</template>
<script setup>
import { onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { FilePenLine, X } from "@lucide/vue";
import { deleteDraft, savedDrafts } from "../services/drafts";
import { openEntryEditor } from "../services/editor";
import { formatDateTime } from "../services/storage";
const visible = ref(false), router = useRouter();
watch(visible, value => { document.body.style.overflow = value ? "hidden" : ""; });
onUnmounted(() => { document.body.style.overflow = ""; });
function resume(item) {
  visible.value = false;
  if (item.kind === "ai") router.push(item.path || "/");
  else openEntryEditor(item.data.original || null);
}
</script>
<style scoped>
.toolbar-drafts { display: inline-flex; align-items: center; gap: 6px; border: 0; padding: 5px 0; background: none; color: #60606c; font-size: 12px; white-space: nowrap; }
.toolbar-drafts b { font-size: 10px; font-weight: 600; border-radius: 10px; padding: 2px 5px; color: #0067cf; background: #e9f1ff; }
.drafts-dialog { width: min(520px, 100%); }
.drafts-list { margin: 18px 0 0; padding: 0; list-style: none; }
.drafts-list li { display: flex; align-items: center; gap: 14px; border-top: 1px solid var(--line); padding: 14px 0; }
.drafts-list li > button:first-child { flex: 1; min-width: 0; text-align: left; border: 0; background: none; padding: 3px 0; }
.drafts-list strong { display: block; color: var(--ink); font-size: 14px; overflow-wrap: anywhere; }
.drafts-list small { display: block; color: #71717d; margin-top: 7px; font-size: 11px; }
@media (max-width: 480px) { .toolbar-drafts span { display: none; } }
</style>
